#!/usr/bin/env python3
"""FAIL receipt for the local PR gate — refuse a second full run on the same tree.

Stdlib only. Called from run_pr_gate.sh (early refuse / write on exit) and from
the afterShellExecution hook. A matching FAIL receipt must print STOP LOOPING
and exit 2 so agents cannot wait through another make pr.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_gate_failure.v2"
STOP = "STOP LOOPING"
FAILED_NODE_RE = re.compile(r"^FAILED\s+(\S+)", re.M)
HOOK_ID_RE = re.compile(r"^- hook id:\s+(\S+)", re.M)
HOOK_EXIT_RE = re.compile(r"^- exit code:\s+(\d+)", re.M)
MAKE_PR_RE = re.compile(
    r"\bmake(?:\s+-C\s+\S+)?\s+pr(?:-check)?(?:\s|$|[;&])",
    re.I,
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_digest(raw: str) -> tuple[str, str, str]:
    """(paths digest, content digest, PR base) — the gate's content identity."""
    paths, content, pr_base = raw.split(" ", 2)
    return paths, content, pr_base


def digest_matches(doc: dict[str, Any], current: str, head_sha: str = "") -> bool:
    """Does this FAIL receipt still describe the current state?

    The content digest alone is not sufficient. A pre-commit hook that rewrites
    a tracked file does so *before* the receipt is written, so the receipt
    already records the rewritten bytes. Committing that rewrite — which is
    exactly what the gate instructs — moves HEAD but leaves the working tree
    byte-identical, so a digest-only comparison would keep matching and the
    loop-breaker would refuse the very re-run it asked for.

    A receipt written without a head sha keeps the old digest-only behavior, so
    this is never weaker than before.
    """

    want = f"{doc.get('paths_digest', '')} {doc.get('content_digest', '')} {doc.get('pr_base', '')}"
    if want != current:
        return False
    recorded_head = str(doc.get("head_sha", "") or "")
    if not recorded_head or not head_sha:
        return True
    return recorded_head == head_sha


def load_doc(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(doc, dict):
        return None
    return doc


def parse_failed_nodes(log_text: str) -> list[str]:
    seen: list[str] = []
    for match in FAILED_NODE_RE.finditer(log_text):
        node = match.group(1)
        if node not in seen:
            seen.append(node)
    return seen


def parse_failed_hooks(log_text: str) -> list[str]:
    hooks: list[str] = []
    current = ""
    for line in log_text.splitlines():
        hid = HOOK_ID_RE.match(line)
        if hid:
            current = hid.group(1)
            continue
        if current and HOOK_EXIT_RE.match(line) and current not in hooks:
            hooks.append(current)
            current = ""
    return hooks


def recheck_command(nodes: list[str], pytest_bin: str) -> str:
    if not nodes:
        return ""
    return " ".join([pytest_bin, *nodes])


def build_failure_doc(
    *,
    current: str,
    nodes: list[str],
    hooks: list[str],
    pytest_bin: str,
    log_hint: str,
    head_sha: str = "",
) -> dict[str, Any]:
    paths, content, pr_base = parse_digest(current)
    command = recheck_command(nodes, pytest_bin)
    if nodes:
        message = (
            f"{STOP}: do not re-run the full gate. "
            "Next tool call is Read those test files and run the recheck_command. "
            "Do not AwaitShell another make pr."
        )
    elif log_hint:
        message = f"{STOP}: do not re-run the full gate. Read {log_hint}."
    else:
        message = f"{STOP}: do not re-run the full gate."
    return {
        "schema": SCHEMA,
        "paths_digest": paths,
        "content_digest": content,
        "pr_base": pr_base,
        "head_sha": head_sha,
        "failed_at": utc_now(),
        "failed_nodes": nodes,
        "failed_hooks": hooks,
        "recheck_command": command,
        "message": message,
    }


def format_refuse(doc: dict[str, Any]) -> str:
    lines = [
        STOP,
        "FAIL receipt matches unchanged state — do not re-run the full gate.",
        "Fix first:",
    ]
    nodes = [str(n) for n in doc.get("failed_nodes") or []]
    hooks = [str(h) for h in doc.get("failed_hooks") or []]
    if nodes:
        lines.extend(f"  {node}" for node in nodes)
    if hooks:
        lines.extend(f"  hook:{hook}" for hook in hooks)
    if not nodes and not hooks:
        lines.append("  (no named pytest nodes — read .l9/pr/last-gate.log)")
    command = str(doc.get("recheck_command") or "").strip()
    lines.append("Re-check:")
    if command:
        lines.append(f"  {command}")
    else:
        lines.append("  read .l9/pr/last-gate.log")
    extra = str(doc.get("message") or "").strip()
    if extra and extra != STOP:
        lines.append(extra)
    return "\n".join(lines) + "\n"


def format_hook_text(doc: dict[str, Any]) -> str:
    return (
        format_refuse(doc).rstrip()
        + "\nNext tool call is Read those test files and run that pytest command; "
        "do not AwaitShell another make pr.\n"
    )


def is_make_pr_command(command: str) -> bool:
    return bool(MAKE_PR_RE.search(command))


def _exit_code(payload: dict[str, Any]) -> int:
    for key in ("exitCode", "exit_code", "status"):
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return 0


def _command(payload: dict[str, Any]) -> str:
    for key in ("command", "cmd"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _workspace(payload: dict[str, Any]) -> Path:
    for key in ("cwd", "workspace", "working_directory"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value).expanduser()
    env_ws = os.environ.get("WS")
    if env_ws:
        return Path(env_ws).expanduser()
    return Path.cwd()


def cmd_refuse(path: Path, current: str, head_sha: str = "") -> int:
    doc = load_doc(path)
    if doc is None or not digest_matches(doc, current, head_sha):
        return 0
    sys.stdout.write(format_refuse(doc))
    return 2


def cmd_write(
    path: Path,
    current: str,
    *,
    log_path: Path | None,
    precommit_path: Path | None,
    pytest_bin: str,
    head_sha: str = "",
) -> int:
    chunks: list[str] = []
    for candidate in (log_path, precommit_path):
        if candidate is not None and candidate.is_file():
            chunks.append(candidate.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(chunks)
    nodes = parse_failed_nodes(text)
    hooks = parse_failed_hooks(text)
    hint = str(log_path) if log_path is not None else ""
    doc = build_failure_doc(
        current=current,
        nodes=nodes,
        hooks=hooks,
        pytest_bin=pytest_bin,
        log_hint=hint,
        head_sha=head_sha,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"gate failure receipt written: {path}", file=sys.stderr)
    return 0


def cmd_after_shell() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print("{}")
        return 0
    if not isinstance(payload, dict):
        print("{}")
        return 0
    command = _command(payload)
    if not is_make_pr_command(command) or _exit_code(payload) == 0:
        print("{}")
        return 0
    workspace = _workspace(payload)
    doc = load_doc(workspace / ".l9" / "pr" / "gate-failure.json")
    if doc is None:
        print("{}")
        return 0
    text = format_hook_text(doc)
    print(
        json.dumps(
            {
                "additional_context": text,
                "agent_message": text,
            }
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR gate FAIL receipt")
    sub = parser.add_subparsers(dest="cmd", required=True)

    refuse = sub.add_parser("refuse")
    refuse.add_argument("path", type=Path)
    refuse.add_argument("digest")
    refuse.add_argument("--head-sha", default="")

    write = sub.add_parser("write")
    write.add_argument("path", type=Path)
    write.add_argument("digest")
    write.add_argument("--log", type=Path, default=None)
    write.add_argument("--precommit", type=Path, default=None)
    write.add_argument("--pytest", default="pytest")
    write.add_argument("--head-sha", default="")

    sub.add_parser("after-shell")

    args = parser.parse_args(argv)
    if args.cmd == "refuse":
        return cmd_refuse(args.path, args.digest, args.head_sha)
    if args.cmd == "write":
        return cmd_write(
            args.path,
            args.digest,
            log_path=args.log,
            precommit_path=args.precommit,
            pytest_bin=args.pytest,
            head_sha=args.head_sha,
        )
    return cmd_after_shell()


if __name__ == "__main__":
    raise SystemExit(main())
