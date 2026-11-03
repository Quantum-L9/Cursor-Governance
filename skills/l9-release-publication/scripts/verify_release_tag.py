#!/usr/bin/env python3
"""Verify a release tag's identity locally and on the GitHub host.

The tag ref, the object it names, and the commit it peels to are the release
identity. A tag that exists but names another object or commit is a different
release, so every comparison is exact.

Kinds:
  annotated    the ref names a tag object (`--tag-object` required) that peels
               to `--peeled-commit`. Operator-admitted and agent-created tags.
  lightweight  the ref names `--peeled-commit` directly. Tags a release job
               creates with plain `git tag <name> <sha>`.
  any          either, as long as the peeled commit matches.

Checks:
  --repo-dir   the local tag (omit for a tag that exists only on the host,
               such as one a release job created).
  --remote     the host ref through `gh api` (owner/name).
  --bind-origin       require the checkout's origin to be --remote (before a push).
  --require-remote    an absent host ref is a mismatch (after a push or release run).

Print one JSON object on stdout.

Exit 0: MATCH
Exit 1: MISMATCH (or invalid input)
Exit 2: REMOTE_ABSENT (remote requested, ref missing, --require-remote not set)
Exit 3: TRANSPORT_BLOCKED
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any

_TAG = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
_REMOTE = re.compile(r"\A[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_ORIGIN = re.compile(
    r"\A(?:https://github\.com/|git@github\.com:)"
    r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?\Z"
)
KINDS = ("annotated", "lightweight", "any")


def _absolute(name: str) -> str:
    """Resolve an executable from absolute PATH entries only (a relative entry can hijack it)."""
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory or not os.path.isabs(directory):
            continue
        found = shutil.which(name, path=directory)
        if found:
            return found
    return name


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_absolute(cmd[0]), *cmd[1:]], cwd=cwd, capture_output=True, text=True, check=False
    )


def _accepted(pattern: re.Pattern[str], value: str | None) -> str:
    match = pattern.fullmatch((value or "").lower() if pattern is _SHA else (value or ""))
    return "" if match is None else match.group(0)


def _emit(payload: dict[str, Any], code: int) -> int:
    print(json.dumps(payload, sort_keys=True))
    return code


def _kind_ok(kind: str, wanted: str) -> bool:
    return wanted == "any" or kind == {"annotated": "tag", "lightweight": "commit"}[wanted]


def local_identity(repo: str, tag: str) -> tuple[str, str, str]:
    """Return (object type, ref target, peeled commit) of a local tag; empty when missing."""
    ref = f"refs/tags/{tag}"
    kind = _run(["git", "cat-file", "-t", "--", ref], cwd=repo)
    obj = _run(["git", "rev-parse", "--verify", "--end-of-options", ref], cwd=repo)
    peeled = _run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"], cwd=repo
    )
    return (
        kind.stdout.strip() if kind.returncode == 0 else "",
        obj.stdout.strip() if obj.returncode == 0 else "",
        peeled.stdout.strip() if peeled.returncode == 0 else "",
    )


def gh_api(path: str) -> tuple[int, str, str]:
    result = _run(["gh", "api", path])
    return result.returncode, result.stdout, result.stderr


def _json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _is_404(out: str, err: str) -> bool:
    return "404" in f"{out}\n{err}" or "Not Found" in f"{out}\n{err}"


def remote_identity(remote: str, tag: str) -> tuple[str, dict[str, str]]:
    """Return (state, fields): state is absent, blocked, or present."""
    owner, _, name = remote.partition("/")
    code, out, err = gh_api(f"repos/{owner}/{name}/git/ref/tags/{tag}")
    if code != 0:
        if _is_404(out, err):
            return "absent", {}
        return "blocked", {"detail": (err or out).strip() or "tag ref request failed"}
    ref = _json_object(out)
    obj = ref.get("object") if ref else None
    if not isinstance(obj, dict):
        return "blocked", {"detail": "remote ref response has no object"}
    kind = str(obj.get("type") or "")
    sha = str(obj.get("sha") or "")
    if kind == "commit":
        return "present", {"remote_kind": "commit", "remote_ref_target": sha, "remote_peeled": sha}
    if kind != "tag":
        return "present", {"remote_kind": kind, "remote_ref_target": sha, "remote_peeled": ""}
    code, out, err = gh_api(f"repos/{owner}/{name}/git/tags/{sha}")
    if code != 0:
        return "blocked", {"detail": (err or out).strip() or "tag object request failed"}
    tag_obj = _json_object(out)
    target = tag_obj.get("object") if tag_obj else None
    if not isinstance(target, dict):
        return "blocked", {"detail": "remote tag object response has no target"}
    peeled = str(target.get("sha") or "") if target.get("type") == "commit" else ""
    return "present", {"remote_kind": "tag", "remote_ref_target": sha, "remote_peeled": peeled}


def origin_repository(repo: str) -> str:
    result = _run(["git", "remote", "get-url", "origin"], cwd=repo)
    if result.returncode != 0:
        return ""
    match = _ORIGIN.fullmatch(result.stdout.strip())
    return "" if match is None else f"{match.group(1)}/{match.group(2)}"


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a release tag locally and on the host.")
    parser.add_argument("--repo-dir", help="local checkout holding the tag")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--kind", choices=KINDS, default="annotated")
    parser.add_argument("--tag-object", help="annotated tag object sha (required for annotated)")
    parser.add_argument("--peeled-commit", required=True, help="commit the tag must resolve to")
    parser.add_argument("--remote", help="owner/name on GitHub")
    parser.add_argument("--bind-origin", action="store_true")
    parser.add_argument("--require-remote", action="store_true")
    return parser.parse_args()


def _input_error(args: argparse.Namespace) -> str:
    if not args.repo_dir and not args.remote:
        return "give --repo-dir, --remote, or both"
    if (args.require_remote or args.bind_origin) and not args.remote:
        return "--require-remote and --bind-origin need --remote"
    if args.bind_origin and not args.repo_dir:
        return "--bind-origin needs --repo-dir"
    if args.kind == "annotated" and not args.tag_object:
        return "--kind annotated needs --tag-object"
    if not _accepted(_TAG, args.tag) or not _accepted(_SHA, args.peeled_commit):
        return "tag or peeled commit is not an allowlisted token"
    if args.tag_object and not _accepted(_SHA, args.tag_object):
        return "tag object is not a 40-hex sha"
    if args.remote and not _accepted(_REMOTE, args.remote):
        return "remote is not owner/name"
    return ""


def main() -> int:
    args = _parse()
    problem = _input_error(args)
    if problem:
        return _emit({"status": "MISMATCH", "detail": problem}, 1)
    expected_object = (args.tag_object or "").lower()
    expected_peeled = args.peeled_commit.lower()
    payload: dict[str, Any] = {
        "tag": args.tag,
        "kind": args.kind,
        "expected_peeled": expected_peeled,
        "expected_tag_object": expected_object,
    }

    if args.repo_dir:
        kind, obj, peeled = local_identity(args.repo_dir, args.tag)
        payload.update({"local_kind": kind, "local_ref_target": obj, "local_peeled": peeled})
        object_ok = not expected_object or obj == expected_object
        if not (_kind_ok(kind, args.kind) and object_ok and peeled == expected_peeled):
            payload["status"] = "MISMATCH"
            payload["detail"] = "local tag kind, object, or peeled commit differs"
            return _emit(payload, 1)

    if not args.remote:
        payload["status"] = "MATCH"
        return _emit(payload, 0)

    if args.bind_origin:
        bound = origin_repository(args.repo_dir)
        payload["origin"] = bound
        if bound.lower() != args.remote.lower():
            payload["status"] = "MISMATCH"
            payload["detail"] = "origin is not the verified owner/name"
            return _emit(payload, 1)

    state, remote = remote_identity(args.remote, args.tag)
    payload.update(remote)
    if state == "blocked":
        payload["status"] = "TRANSPORT_BLOCKED"
        return _emit(payload, 3)
    if state == "absent":
        if args.require_remote:
            payload["status"] = "MISMATCH"
            payload["detail"] = "remote tag ref is absent"
            return _emit(payload, 1)
        payload["status"] = "REMOTE_ABSENT"
        return _emit(payload, 2)
    remote_kind = "tag" if remote.get("remote_kind") == "tag" else remote.get("remote_kind", "")
    object_ok = not expected_object or remote.get("remote_ref_target") == expected_object
    ok = (
        _kind_ok(remote_kind, args.kind)
        and object_ok
        and remote.get("remote_peeled") == expected_peeled
    )
    payload["status"] = "MATCH" if ok else "MISMATCH"
    if not ok:
        payload["detail"] = "remote tag kind, object, or peeled commit differs"
    return _emit(payload, 0 if ok else 1)


if __name__ == "__main__":
    sys.exit(main())
