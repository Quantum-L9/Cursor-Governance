#!/usr/bin/env python3
"""Temporary operator helpers for replaying a finished implementation as a stack.

These are not the live campaign path. `make campaign` still owns activate through
close. Use this module when a campaign must reproduce work that already exists
on a git ref, one task at a time, so each task produces the diff its contract
declares.

Subcommands:

- ``materialize`` — copy a task's declared writable paths from a git ref into
  its worktree. Optional ``--hold-back`` keeps later-task functions out of a
  shared file. Checksum manifests are regenerated against the worktree.
- ``drive`` — loop the first incomplete task: materialize, then ``make campaign
  --until execute``, until every required task is COMPLETED or one is stuck.
- ``reset`` — retire the live pec runtime, rewind the target to a base SHA,
  and re-arm.

Nothing here is campaign-specific. Campaign id, isolate, target, intent, and
reference ref are all arguments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PE_ROOT = Path(__file__).resolve().parents[1]
GOV_ROOT = PE_ROOT.parents[1]
RUN_CAMPAIGN = PE_ROOT / "scripts/run_campaign.py"
PEC = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
GIT_TIMEOUT_S = 45
MAKE_TIMEOUT_S = 900


class ReplayError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def run_cmd(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = GIT_TIMEOUT_S,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env or os.environ.copy(),
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayError(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReplayError(f"{path} is not a JSON object")
    return payload


def load_hold_back(path: Path | None) -> dict[str, dict[str, tuple[str, ...]]]:
    """Optional map: task_id → relative path → function names to hold back."""
    if path is None:
        return {}
    raw = load_json(path)
    parsed: dict[str, dict[str, tuple[str, ...]]] = {}
    for task_id, files in raw.items():
        if not isinstance(files, dict):
            raise ReplayError(f"hold-back {task_id!r} must map paths to function names")
        parsed[str(task_id)] = {
            str(rel): tuple(str(name) for name in names)
            for rel, names in files.items()
            if isinstance(names, list)
        }
    return parsed


def function_span(text: str, name: str) -> tuple[int, int] | None:
    match = re.search(rf"^def {re.escape(name)}\(", text, re.MULTILINE)
    if match is None:
        return None
    following = re.search(r"^(?:def |@)", text[match.end() :], re.MULTILINE)
    end = len(text) if following is None else match.end() + following.start()
    return match.start(), end


def hold_back_functions(ported: str, base_text: str, names: tuple[str, ...]) -> str:
    """Replace named functions in *ported* with the versions from *base_text*."""
    for name in names:
        target_span = function_span(ported, name)
        base_span = function_span(base_text, name)
        if target_span is None or base_span is None:
            continue
        ported = (
            ported[: target_span[0]]
            + base_text[base_span[0] : base_span[1]]
            + ported[target_span[1] :]
        )
    return ported


def git_show(repo: Path, spec: str) -> str | None:
    blob = run_cmd(["git", "-C", str(repo), "show", spec])
    if blob.returncode != 0:
        return None
    return blob.stdout


def regenerate_manifest(path: Path) -> None:
    """Rewrite a checksum manifest so it hashes the tree it ships with."""
    if not path.is_file():
        return
    if path.name == "MANIFEST.json":
        document = json.loads(path.read_text(encoding="utf-8"))
        root = path.parent
        for entry in document.get("files") or []:
            if not isinstance(entry, dict) or not entry.get("path"):
                continue
            target = root / str(entry["path"])
            if target.is_file():
                entry["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        path.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    if path.name == "MANIFEST.yaml":
        if yaml is None:
            raise ReplayError("PyYAML is required to regenerate MANIFEST.yaml")
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            return
        root = path.parent
        carries_bytes = any(
            "bytes" in entry for entry in (document.get("files") or []) if isinstance(entry, dict)
        )
        files: list[dict[str, Any]] = []
        for item in sorted(root.rglob("*")):
            if (
                not item.is_file()
                or item.name == "MANIFEST.yaml"
                or "__pycache__" in item.parts
                or item.suffix == ".pyc"
            ):
                continue
            entry: dict[str, Any] = {
                "path": item.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
            }
            if carries_bytes:
                entry["bytes"] = item.stat().st_size
            files.append(entry)
        document["files"] = files
        summary = document.get("summary")
        if isinstance(summary, dict):
            if "file_count" in summary:
                summary["file_count"] = len(files)
            if "total_bytes" in summary:
                summary["total_bytes"] = sum(int(entry.get("bytes") or 0) for entry in files)
        path.write_text(yaml.safe_dump(document, sort_keys=False, width=120), encoding="utf-8")


def materialize_task(
    *,
    workspace: Path,
    task_id: str,
    target: Path,
    ref: str,
    hold_back: dict[str, dict[str, tuple[str, ...]]] | None = None,
) -> dict[str, Any]:
    """Copy the task's declared writable paths from *ref* into its worktree."""
    worktree = workspace / "worktrees" / task_id
    contract_path = workspace / "contracts" / "rendered" / f"{task_id}.json"
    if not worktree.is_dir():
        raise ReplayError(f"no worktree for {task_id}: {worktree}")
    if not contract_path.is_file():
        raise ReplayError(f"no rendered contract for {task_id}: {contract_path}")
    contract = load_json(contract_path)
    holds = (hold_back or {}).get(task_id) or {}
    ported: list[str] = []
    missing: list[str] = []
    held: list[str] = []
    regenerated: list[str] = []
    for rel in contract.get("writable_paths") or []:
        content = git_show(target, f"{ref}:{rel}")
        if content is None:
            missing.append(str(rel))
            continue
        names = holds.get(str(rel))
        if names:
            base = git_show(worktree, f"HEAD:{rel}")
            if base is not None:
                content = hold_back_functions(content, base, names)
                held.extend(names)
        destination = worktree / str(rel)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        if destination.name in {"MANIFEST.json", "MANIFEST.yaml"}:
            regenerate_manifest(destination)
            regenerated.append(str(rel))
        ported.append(str(rel))
    return {
        "task_id": task_id,
        "ported": ported,
        "missing": missing,
        "held_back": held,
        "regenerated": regenerated,
    }


def pec_status_tasks(workspace: Path) -> list[dict[str, Any]]:
    env = {**os.environ, "L9_ALLOW_PEC_DIRECT": "1"}
    completed = run_cmd(
        [sys.executable, str(PEC), "status", "--workspace", str(workspace)],
        env=env,
    )
    if completed.returncode != 0:
        raise ReplayError(f"pec status failed: {(completed.stderr or completed.stdout).strip()}")
    payload = json.loads(completed.stdout)
    return list(payload.get("tasks") or [])


def first_incomplete_task(workspace: Path) -> str | None:
    for task in pec_status_tasks(workspace):
        if str(task.get("runtime_state") or "") != "COMPLETED":
            return str(task.get("id") or "") or None
    return None


def run_campaign_until(
    intent: Path, until: str, *, isolate: Path
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "L9_CAMPAIGN_UNTIL_DEBUG": "1"}
    return run_cmd(
        [sys.executable, str(RUN_CAMPAIGN), "--intent", str(intent), "--until", until],
        cwd=isolate,
        timeout=MAKE_TIMEOUT_S,
        env=env,
    )


def drive_campaign(
    *,
    intent: Path,
    isolate: Path,
    workspace: Path,
    target: Path,
    ref: str | None,
    hold_back: dict[str, dict[str, tuple[str, ...]]] | None = None,
    max_steps: int = 20,
) -> dict[str, Any]:
    """Materialize each incomplete task from *ref*, then re-run execute."""
    completed: list[str] = []
    for _ in range(max_steps):
        task_id = first_incomplete_task(workspace)
        if not task_id:
            return {"status": "COMPLETED", "completed": completed}
        if ref and (workspace / "worktrees" / task_id).is_dir():
            result = materialize_task(
                workspace=workspace,
                task_id=task_id,
                target=target,
                ref=ref,
                hold_back=hold_back,
            )
            print(f"ported {len(result['ported'])} file(s) into {task_id}")
            for rel in result["ported"]:
                print(f"  + {rel}")
            if result["missing"]:
                print(f"absent from {ref} — author by hand:")
                for rel in result["missing"]:
                    print(f"  ? {rel}")
        output = run_campaign_until(intent, "execute", isolate=isolate)
        after = first_incomplete_task(workspace)
        print(f"[{task_id}] -> {after or 'all complete'}")
        if after != task_id:
            completed.append(task_id)
            continue
        tail = ((output.stdout or "") + (output.stderr or "")).strip()
        if "refuse stub" in tail:
            print(next((line for line in tail.splitlines() if "refuse stub" in line), tail[:200]))
            continue
        raise ReplayError(f"{task_id} did not advance:\n{tail[-2000:]}")
    raise ReplayError(
        f"drive exceeded {max_steps} steps; last incomplete: {first_incomplete_task(workspace)}"
    )


def reset_campaign(
    *,
    campaign_id: str,
    isolate: Path,
    target: Path,
    base: str,
    intent: Path,
    l9_root: Path,
) -> dict[str, Any]:
    """Retire the live runtime, rewind the target, and re-arm."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    programs = l9_root / "programs"
    live = programs / campaign_id
    retired = None
    if live.is_dir():
        stale = programs / "stale"
        stale.mkdir(parents=True, exist_ok=True)
        retired = stale / f"{campaign_id}-retired-{stamp}"
        shutil.move(str(live), str(retired))
    prune = run_cmd(["git", "-C", str(target), "worktree", "prune"])
    if prune.returncode != 0:
        raise ReplayError(f"git worktree prune failed: {(prune.stderr or '').strip()}")
    listed = run_cmd(["git", "-C", str(target), "branch", "--format=%(refname:short)"])
    renamed: list[str] = []
    for branch in listed.stdout.splitlines():
        if not branch.startswith("pec/"):
            continue
        retired_name = f"retired/{branch.replace('/', '-')}-{stamp}"
        moved = run_cmd(["git", "-C", str(target), "branch", "-m", branch, retired_name])
        if moved.returncode != 0:
            raise ReplayError(f"cannot retire {branch}: {(moved.stderr or '').strip()}")
        renamed.append(retired_name)
    checkout = run_cmd(
        ["git", "-C", str(target), "checkout", "-B", f"campaign-base/{campaign_id}", base]
    )
    if checkout.returncode != 0:
        raise ReplayError(f"cannot rewind target to {base}: {(checkout.stderr or '').strip()}")
    force = run_cmd(["git", "-C", str(target), "branch", "-f", f"campaign/{campaign_id}", base])
    if force.returncode != 0:
        raise ReplayError(f"cannot reset campaign/{campaign_id}: {(force.stderr or '').strip()}")
    armed = run_campaign_until(intent, "arm", isolate=isolate)
    if armed.returncode != 0:
        raise ReplayError(
            f"re-arm failed:\n{((armed.stdout or '') + (armed.stderr or ''))[-2000:]}"
        )
    return {
        "campaign_id": campaign_id,
        "base": base,
        "retired": str(retired) if retired else None,
        "renamed_branches": renamed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    materialize = sub.add_parser("materialize", help="copy declared paths from a git ref")
    materialize.add_argument("--workspace", type=Path, required=True)
    materialize.add_argument("--task", required=True)
    materialize.add_argument("--target", type=Path, required=True)
    materialize.add_argument("--ref", required=True)
    materialize.add_argument("--hold-back", type=Path, default=None)

    drive = sub.add_parser("drive", help="materialize each incomplete task and re-run execute")
    drive.add_argument("--intent", type=Path, required=True)
    drive.add_argument("--isolate", type=Path, default=GOV_ROOT)
    drive.add_argument("--workspace", type=Path, required=True)
    drive.add_argument("--target", type=Path, required=True)
    drive.add_argument("--ref", default=None)
    drive.add_argument("--hold-back", type=Path, default=None)
    drive.add_argument("--max-steps", type=int, default=20)

    reset = sub.add_parser("reset", help="retire runtime, rewind target, re-arm")
    reset.add_argument("--campaign-id", required=True)
    reset.add_argument("--isolate", type=Path, default=GOV_ROOT)
    reset.add_argument("--target", type=Path, required=True)
    reset.add_argument("--base", required=True)
    reset.add_argument("--intent", type=Path, required=True)
    reset.add_argument("--l9-root", type=Path, default=Path.home() / ".l9")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "materialize":
            result = materialize_task(
                workspace=args.workspace,
                task_id=args.task,
                target=args.target,
                ref=args.ref,
                hold_back=load_hold_back(args.hold_back),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "drive":
            result = drive_campaign(
                intent=args.intent,
                isolate=args.isolate,
                workspace=args.workspace,
                target=args.target,
                ref=args.ref,
                hold_back=load_hold_back(args.hold_back),
                max_steps=args.max_steps,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        result = reset_campaign(
            campaign_id=args.campaign_id,
            isolate=args.isolate,
            target=args.target,
            base=args.base,
            intent=args.intent,
            l9_root=args.l9_root,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except ReplayError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
