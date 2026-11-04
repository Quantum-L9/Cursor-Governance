#!/usr/bin/env python3
"""Drive a triggered release to completion: wait, observe, plan the remainder.

A merged version PR or a pushed tag is the start of a release, not the end. This
script follows the repository's release run for the release commit, then reads
the three side effects a release consists of on the host -- the exact tag, the
GitHub Release, and the maintained major tag -- and reports either that all
three are done or the ordered commands that finish what the run left undone.

It never mutates anything. Every command in `plan` is run by the agent as its own
shell command, so the publication plane and git guardrails evaluate each one.
Rerun this script after each step until it exits 0.

Plan routes, preferred first:
  repository_job  dispatch the release workflow, or rerun its run for this commit
                  once: the repository's own job, with its own credentials.
  agent           create the missing exact tag and Release; the tag push is
                  receipt-gated (references/publication-plane.md).
  operator        move an existing major tag. A lease push onto a shared tag ref
                  needs human authorization (L9_GIT_DESTRUCTIVE_AUTHORIZED); an
                  agent never sets it for itself.

Print one JSON object on stdout.

Exit 0: RELEASE_COMPLETE (tag, Release and major tag all at the release commit)
Exit 1: MISMATCH (a tag at another commit, a major tag ahead of the release, bad input)
Exit 3: TRANSPORT_BLOCKED
Exit 4: WAITING_APPROVAL (the run waits on an environment reviewer)
Exit 5: COMPLETION_REQUIRED (see plan)
Exit 6: RUN_PENDING (the run did not finish before --wait-seconds)
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_github_release as releases  # noqa: E402  (sibling module, same pack)
import verify_release_tag as tags  # noqa: E402

_FAILED = {"failure", "cancelled", "timed_out", "startup_failure", "action_required"}
_WORKFLOW = re.compile(r"\A[A-Za-z0-9_.-]+\.ya?ml\Z")
_BRANCH = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")

# Injectable for tests.
_sleep = time.sleep
_clock = time.monotonic


def _get(path: str) -> tuple[str, Any]:
    """GET a host path: (present|absent|blocked, parsed JSON or detail)."""
    code, out, err = tags.gh_api(path)
    if code != 0:
        if tags._is_404(out, err):
            return "absent", {}
        return "blocked", {"detail": (err or out).strip() or f"request failed: {path}"}
    try:
        return "present", json.loads(out)
    except json.JSONDecodeError:
        return "blocked", {"detail": f"response was not JSON: {path}"}


def find_run(remote: str, workflow: str, commit: str) -> tuple[str, dict[str, Any]]:
    state, body = _get(f"repos/{remote}/actions/workflows/{workflow}/runs?head_sha={commit}")
    if state != "present":
        return state, body
    runs = body.get("workflow_runs") if isinstance(body, dict) else None
    runs = [r for r in runs or [] if isinstance(r, dict) and r.get("head_sha") == commit]
    if not runs:
        return "absent", {}
    return "present", max(
        runs, key=lambda r: int(r.get("run_attempt") or 0) + int(r.get("id") or 0)
    )


def _summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "url": run.get("html_url"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "attempt": run.get("run_attempt"),
    }


def pending_approval(remote: str, run_id: Any) -> list[dict[str, Any]]:
    state, body = _get(f"repos/{remote}/actions/runs/{run_id}/pending_deployments")
    if state != "present" or not isinstance(body, list):
        return []
    waiting = []
    for item in body:
        if not isinstance(item, dict):
            continue
        env = item.get("environment") if isinstance(item.get("environment"), dict) else {}
        reviewers = [
            str((r.get("reviewer") or {}).get("login") or (r.get("reviewer") or {}).get("name"))
            for r in item.get("reviewers") or []
            if isinstance(r, dict)
        ]
        waiting.append({"environment": env.get("name"), "reviewers": reviewers})
    return waiting


def failed_jobs(remote: str, run_id: Any) -> list[dict[str, Any]]:
    state, body = _get(f"repos/{remote}/actions/runs/{run_id}/jobs")
    if state != "present" or not isinstance(body, dict):
        return []
    return [
        {"name": j.get("name"), "conclusion": j.get("conclusion"), "url": j.get("html_url")}
        for j in body.get("jobs") or []
        if isinstance(j, dict) and j.get("conclusion") in _FAILED
    ]


def major_relation(remote: str, current: str, commit: str) -> str:
    """identical | behind (major can advance) | ahead | diverged | blocked."""
    if current == commit:
        return "identical"
    state, body = _get(f"repos/{remote}/compare/{current}...{commit}")
    if state != "present" or not isinstance(body, dict):
        return "blocked"
    status = body.get("status")
    if status == "ahead":
        return "behind"
    if status == "behind":
        return "ahead"
    return str(status or "diverged")


def observe(remote: str, tag: str, commit: str, major: str | None) -> dict[str, Any]:
    seen: dict[str, Any] = {"problems": [], "missing": [], "blocked": []}
    state, ident = tags.remote_identity(remote, tag)
    seen["tag"] = {"state": state, **ident}
    if state == "blocked":
        seen["blocked"].append(f"tag: {ident.get('detail')}")
    elif state == "absent":
        seen["missing"].append("tag")
    elif ident.get("remote_peeled") != commit:
        seen["problems"].append(
            f"{tag} already names {ident.get('remote_peeled') or 'a non-commit'}"
        )

    state, record = releases.release_record(remote, tag)
    if state == "blocked":
        seen["blocked"].append(f"release: {record.get('detail')}")
    elif state == "absent":
        seen["missing"].append("release")
    else:
        seen["release"] = {"url": record.get("html_url"), "draft": bool(record.get("draft"))}
        if record.get("draft"):
            seen["missing"].append("release_published")
        if record.get("tag_name") != tag:
            seen["problems"].append(f"release tag_name is {record.get('tag_name')!r}")

    if major:
        state, ident = tags.remote_identity(remote, major)
        seen["major"] = {"state": state, **ident}
        if state == "blocked":
            seen["blocked"].append(f"major: {ident.get('detail')}")
        elif state == "absent":
            seen["missing"].append("major_create")
        else:
            current = ident.get("remote_peeled") or ""
            relation = major_relation(remote, current, commit) if current else "diverged"
            seen["major"]["relation"] = relation
            if relation == "behind":
                seen["missing"].append("major_advance")
            elif relation == "blocked":
                seen["blocked"].append("major: compare request failed")
            elif relation != "identical":
                seen["problems"].append(
                    f"{major} is {relation} of the release commit; never move it backwards"
                )
    return seen


def _q(value: str) -> str:
    return shlex.quote(value)


def _step(route: str, step: str, command: str) -> dict[str, str]:
    actor = "operator" if route == "operator" else "agent"
    return {"route": route, "actor": actor, "step": step, "command": command}


def repository_steps(args: argparse.Namespace, run: dict[str, Any] | None) -> list[dict[str, str]]:
    """The repository's own job finishing the release: one dispatch or one rerun, never more."""
    if not args.workflow:
        return []
    api = f"gh api -X POST repos/{args.remote}/actions"
    if run is None:
        if not args.dispatchable:
            return []
        return [
            _step(
                "repository_job",
                "dispatch the release workflow on the branch whose tip is the release commit",
                f"{api}/workflows/{args.workflow}/dispatches -f ref={_q(args.branch)}",
            )
        ]
    if int(run.get("run_attempt") or 1) >= 2:
        return []
    if run.get("conclusion") in _FAILED:
        return [
            _step(
                "repository_job",
                "read the failed job log; for a transient or host cause rerun the failed jobs once",
                f"{api}/runs/{run.get('id')}/rerun-failed-jobs",
            )
        ]
    return [
        _step(
            "repository_job",
            "rerun the release run once, only when its job decides each side effect from "
            "host state; otherwise take the fallback",
            f"{api}/runs/{run.get('id')}/rerun",
        )
    ]


def _tag_pushes(args: argparse.Namespace, missing: list[str], repo: str) -> list[dict[str, str]]:
    tag, commit, major = args.tag, args.commit, args.major_tag
    pushes: list[dict[str, str]] = []
    if "tag" in missing:
        ref = f"{commit}:refs/tags/{tag}"
        if args.tag_kind == "annotated":
            pushes.append(
                _step(
                    "agent",
                    "create the annotated tag locally at the release commit",
                    f"git -C {_q(repo)} tag -a {_q(tag)} {commit} -m {_q(tag)}",
                )
            )
            ref = f"refs/tags/{tag}"
        pushes.append(
            _step(
                "agent",
                "push exactly the release tag ref",
                f"git -C {_q(repo)} push origin {_q(ref)}",
            )
        )
    if "major_create" in missing:
        pushes.append(
            _step(
                "agent",
                "create the maintained major tag at the release commit",
                f"git -C {_q(repo)} push origin {commit}:refs/tags/{_q(major or '')}",
            )
        )
    if not pushes:
        return []
    reason = f"publish release refs of {tag} at {commit} in {args.remote}; no force, no recreate"
    receipt_tool = '"$GOV_PY" "$GOV/ops/autonomy/breakglass_receipt.py"'
    return [
        _step(
            "agent",
            "write the publish-path receipt in its own command",
            f"{receipt_tool} --write --issuer ops --hours 1 --reason {_q(reason)}",
        ),
        *pushes,
        _step(
            "agent",
            "remove the receipt as soon as the pushes return, success or failure",
            f"rm -f ~/.l9/autonomy/publish-path-override.json && {receipt_tool} --status",
        ),
    ]


def agent_steps(args: argparse.Namespace, seen: dict[str, Any]) -> list[dict[str, str]]:
    """What the agent (and, for a major move, the operator) runs when no job route is left."""
    tag, remote, major = args.tag, args.remote, args.major_tag
    repo = args.repo_dir or "<checkout>"
    missing = seen["missing"]
    steps = _tag_pushes(args, missing, repo)
    if "release" in missing:
        steps.append(
            _step(
                "agent",
                "create the GitHub Release for the existing tag",
                f"gh release create {_q(tag)} --repo {remote} --verify-tag --title {_q(tag)} "
                "--generate-notes",
            )
        )
    if "release_published" in missing:
        steps.append(
            _step(
                "agent",
                "publish the draft Release",
                f"gh release edit {_q(tag)} --repo {remote} --draft=false",
            )
        )
    if "major_advance" in missing:
        prev = seen["major"].get("remote_peeled", "")
        steps.append(
            _step(
                "operator",
                f"advance {major} from {prev} with a lease; ask the operator to run it",
                f"L9_GIT_DESTRUCTIVE_AUTHORIZED={_q(f'advance {major} to {tag}')} "
                f"git -C {_q(repo)} push --force-with-lease=refs/tags/{major}:{prev} "
                f"origin {args.commit}:refs/tags/{major}",
            )
        )
    return steps


def consumer_refresh(tag: str, major: str | None) -> str:
    refs = [f"refs/tags/{tag}:refs/tags/{tag}"]
    if major:
        refs.append(f"refs/tags/{major}:refs/tags/{major}")
    return "git fetch origin --force " + " ".join(refs)


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drive a triggered release to completion.")
    parser.add_argument("--remote", required=True, help="owner/name on GitHub")
    parser.add_argument("--tag", required=True, help="exact release tag, e.g. v4.3.0")
    parser.add_argument("--commit", required=True, help="release commit (40 hex)")
    parser.add_argument("--major-tag", help="maintained major tag, e.g. v4")
    parser.add_argument("--workflow", help="release workflow file, from detect_release_model.py")
    parser.add_argument(
        "--dispatchable", action="store_true", help="the workflow has workflow_dispatch"
    )
    parser.add_argument("--branch", default="main", help="default branch for a dispatch")
    parser.add_argument("--tag-kind", choices=("lightweight", "annotated"), default="lightweight")
    parser.add_argument("--repo-dir", help="checkout used for agent tag pushes")
    parser.add_argument("--wait-seconds", type=int, default=1800)
    parser.add_argument("--trigger-grace-seconds", type=int, default=180)
    parser.add_argument("--poll-seconds", type=int, default=30)
    return parser.parse_args()


def _input_error(args: argparse.Namespace) -> str:
    if not tags._accepted(tags._REMOTE, args.remote):
        return "remote is not owner/name"
    if not tags._accepted(tags._TAG, args.tag) or not tags._accepted(tags._SHA, args.commit):
        return "tag or commit is not an allowlisted token"
    if args.major_tag and (
        not tags._accepted(tags._TAG, args.major_tag)
        or not args.tag.startswith(args.major_tag + ".")
    ):
        return "major tag must be the exact tag's major prefix (v4 for v4.3.0)"
    if args.workflow and not tags._accepted(_WORKFLOW, args.workflow):
        return "workflow is not a workflow file name"
    if not tags._accepted(_BRANCH, args.branch):
        return "branch is not an allowlisted token"
    return ""


def wait_for_run(
    args: argparse.Namespace, payload: dict[str, Any]
) -> tuple[int | None, dict[str, Any] | None]:
    """Follow the release run. Returns (exit code to stop with, or None to continue; run)."""
    start = _clock()
    while True:
        state, run = find_run(args.remote, args.workflow, args.commit)
        elapsed = _clock() - start
        if state == "blocked":
            payload.update({"status": "TRANSPORT_BLOCKED", "detail": run.get("detail")})
            return 3, None
        if state == "absent":
            if elapsed >= args.trigger_grace_seconds:
                payload["run"] = {"state": "not_triggered"}
                return None, None
        else:
            payload["run"] = _summary(run)
            if run.get("status") == "completed":
                if run.get("conclusion") in _FAILED:
                    payload["run"]["failed_jobs"] = failed_jobs(args.remote, run.get("id"))
                return None, run
            if run.get("status") == "waiting":
                waiting = pending_approval(args.remote, run.get("id"))
                if waiting:
                    payload.update({"status": "WAITING_APPROVAL", "pending": waiting})
                    return 4, run
            if elapsed >= args.wait_seconds:
                payload["status"] = "RUN_PENDING"
                return 6, run
        _sleep(args.poll_seconds)


def main() -> int:
    args = _parse()
    problem = _input_error(args)
    if problem:
        return tags._emit({"status": "MISMATCH", "detail": problem}, 1)
    args.commit = args.commit.lower()
    payload: dict[str, Any] = {
        "remote": args.remote,
        "tag": args.tag,
        "commit": args.commit,
        "major_tag": args.major_tag,
        "consumer_refresh": consumer_refresh(args.tag, args.major_tag),
    }
    run: dict[str, Any] | None = None
    if args.workflow:
        code, run = wait_for_run(args, payload)
        if code is not None:
            return tags._emit(payload, code)

    seen = observe(args.remote, args.tag, args.commit, args.major_tag)
    payload["observed"] = {
        k: v for k, v in seen.items() if k not in ("missing", "problems", "blocked")
    }
    if seen["blocked"]:
        payload.update({"status": "TRANSPORT_BLOCKED", "detail": "; ".join(seen["blocked"])})
        return tags._emit(payload, 3)
    if seen["problems"]:
        payload.update({"status": "MISMATCH", "detail": "; ".join(seen["problems"])})
        return tags._emit(payload, 1)
    if not seen["missing"]:
        payload["status"] = "RELEASE_COMPLETE"
        return tags._emit(payload, 0)
    job = repository_steps(args, run)
    fallback = agent_steps(args, seen)
    payload.update(
        {
            "status": "COMPLETION_REQUIRED",
            "missing": seen["missing"],
            "plan": job or fallback,
            "fallback": fallback if job else [],
        }
    )
    return tags._emit(payload, 5)


if __name__ == "__main__":
    sys.exit(main())
