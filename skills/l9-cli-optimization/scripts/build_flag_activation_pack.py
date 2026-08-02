#!/usr/bin/env python3
"""Build a deterministic, review-required PR pack from a full-throttle activation
report (the output of `full_throttle.py --mode apply`).

STANDALONE by design: this builder does NOT import or modify `build_commit_pack.py`.
The core scan → PR-pack pipeline keeps its `dormant_by_design` refusal intact;
this is a separate, bounded exception for the full-throttle activation mode (see
`references/full-throttle-activation.md`). The pack it emits is labeled
**REVIEW REQUIRED — do not auto-merge**; the PR is the human gate.

Pack layout:
  MANIFEST.json                     strategy, activated flags, test delta, checksums
  README.md                         how to apply and what was proven
  change/files/<path>               flipped source files (full content)
  change/commit.patch               unified diff (from the proven worktree)
  pr/PR_BODY.md                     review-required PR description
  evidence/FULL_THROTTLE_REPORT.md  inventory, classifications, exclusions + why, test delta
  SHA256SUMS                        checksum of every emitted file

Determinism: file order is sorted; timestamps come from SOURCE_DATE_EPOCH (or the
report). Stdlib-only. Honesty: the test delta is the real captured flags-off →
flags-on result; nothing is fabricated. A report where `applied` is false emits a
BLOCKED pack (no flips) and exits 2.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flag_inventory import flip_flag  # noqa: E402

STRATEGY = "full_throttle_flag_activation"


class PackError(RuntimeError):
    pass


def _created_utc(report: dict) -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if report.get("created_utc"):
        return str(report["created_utc"])
    if epoch:
        try:
            return datetime.fromtimestamp(int(epoch), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise PackError("SOURCE_DATE_EPOCH must be an integer") from exc
    return "1970-01-01T00:00:00Z"


def _safe_rel(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise PackError(f"unsafe path in report: {value}")
    return p


def _flipped_content(repo: Path, rel: str, rows: list[dict]) -> tuple[str, str]:
    """Return (original_text, flipped_text) for one file given its flag rows."""
    src = repo / rel
    original = src.read_text(encoding="utf-8", errors="ignore")
    flipped = original
    for f in sorted(rows, key=lambda x: -x["line"]):
        flipped = flip_flag(flipped, f)
    return original, flipped


def _unified(rel: str, original: str, flipped: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            flipped.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
    )


def under_root(root: Path, path: Path, *, label: str = "path") -> Path:
    base = os.path.realpath(root)
    target = os.path.realpath(path)
    try:
        if os.path.commonpath([base, target]) != base:
            raise RuntimeError(f"{label} escapes root {root}: {path}")
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes root {root}: {path}") from exc
    return Path(target)


def _write(root: Path, path: Path, content: str) -> None:
    target = under_root(root, path, label="write")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content)


def _render_report_md(report: dict) -> str:
    summary = report.get("summary", {})
    activated = report.get("activated_flags", [])
    backed_out = report.get("backed_out_flags", [])
    delta = report.get("test_delta", {})
    lines = [
        "# Full-Throttle Activation Report",
        "",
        f"Repository: `{report.get('repo', 'UNKNOWN')}`",
        f"Test command: `{' '.join(report.get('test_command', []))}`",
        "",
        "## Test delta (real captured result — no fabrication)",
        "",
        f"- Baseline (flags off): **{'PASS' if report.get('baseline_test', {}).get('passed') else 'FAIL'}**",
        f"- Activated (flags on): **{'PASS' if report.get('activated_test', {}).get('passed') else 'FAIL'}**",
        f"- Flags activated: {delta.get('flags_on', len(activated))}",
        f"- Back-out passes: {report.get('back_out_passes', 0)}",
        "",
        "## Activated flags (non-danger, non-staged, and test-proven)",
        "",
    ]
    if activated:
        for row in report.get("activated_flag_rows", []):
            lines.append(
                f"- `{row['flag']}` — {row['file']}:{row['line']} ({row.get('kind', 'flag')})"
            )
    else:
        lines.append("- (none — every candidate was danger-excluded or regressed tests)")
    lines += ["", "## Excluded — danger block-list (never flipped, polarity-aware)", ""]
    danger_rows = [f for f in report.get("inventory", []) if f["classification"] == "danger"]
    if danger_rows:
        for row in danger_rows:
            lines.append(f"- `{row['flag']}` — {row['file']}:{row['line']} — {row['reason']}")
    else:
        lines.append("- (none)")
    lines += ["", "## Excluded — staged rollout / dormant_by_design (Identity-Lock #1)", ""]
    staged_rows = [f for f in report.get("inventory", []) if f["classification"] == "staged"]
    if staged_rows:
        for row in staged_rows:
            lines.append(f"- `{row['flag']}` — {row['file']}:{row['line']} — {row['reason']}")
    else:
        lines.append("- (none)")
    lines += ["", "## Backed out — empirically unsafe (flip regressed the repo's tests)", ""]
    if backed_out:
        for b in backed_out:
            lines.append(f"- `{b['flag']}` — {b['file']}:{b['line']} — {b['reason']}")
    else:
        lines.append("- (none)")
    lines += ["", f"Inventory totals: {json.dumps(summary.get('by_classification', {}))}", ""]
    return "\n".join(lines) + "\n"


def _render_pr_body(report: dict) -> str:
    activated = report.get("activated_flags", [])
    return (
        "\n".join(
            [
                "# Full-throttle flag activation — REVIEW REQUIRED, do not auto-merge",
                "",
                "This PR flips off-by-default feature flags **on** and commits the new defaults.",
                "Each flip is non-danger (polarity-aware classifier), non-staged, and was proven",
                "against the repository's own test suite in an isolated git worktree.",
                "",
                f"**Flags activated ({len(activated)}):** "
                + (", ".join(f"`{f}`" for f in activated) or "none"),
                "",
                "**Safety:** danger-class flags (delete/deploy/charge/auth-disable/…) were never",
                "flipped; flags that regressed tests were backed out and reported. See",
                "`evidence/FULL_THROTTLE_REPORT.md` for the full inventory, exclusions, and the",
                "real flags-off → flags-on test delta.",
                "",
                "> This mode deliberately activates capability the repo defaults off. A human must",
                "> review and merge; the skill never auto-merges a full-throttle pack.",
                "",
            ]
        )
        + "\n"
    )


def _render_readme(report: dict, pack_name: str) -> str:
    return (
        "\n".join(
            [
                f"# {pack_name}",
                "",
                f"Strategy: `{STRATEGY}` (review-required).",
                "",
                "Apply the activation:",
                "",
                "```bash",
                "git apply --index change/commit.patch",
                "```",
                "",
                "Or copy the full files under `change/files/` over their repository paths.",
                "Then run the repository's own test command and open the PR from `pr/PR_BODY.md`.",
                "Verify `evidence/FULL_THROTTLE_REPORT.md` before merging. Never auto-merge.",
                "",
            ]
        )
        + "\n"
    )


def build(report_path: Path, repo_root: Path, output_parent: Path) -> tuple[Path, int]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    repo = repo_root.resolve()
    pack_name = report.get("pack_name") or (
        "full-throttle-" + Path(report.get("repo", "repo")).name
    )
    pack_root = output_parent / pack_name
    if pack_root.exists():
        import shutil

        shutil.rmtree(pack_root)
    pack_root.mkdir(parents=True)

    activated_rows = report.get("activated_flag_rows", [])
    applied = bool(report.get("applied")) and bool(activated_rows)

    # group activated flags by file
    by_file: dict[str, list[dict]] = {}
    for f in activated_rows:
        _safe_rel(f["file"])
        by_file.setdefault(f["file"], []).append(f)

    patch_parts: list[str] = []
    for rel in sorted(by_file):
        original, flipped = _flipped_content(repo, rel, by_file[rel])
        _write(pack_root, pack_root / "change" / "files" / rel, flipped)
        patch_parts.append(_unified(rel, original, flipped))
    patch_text = report.get("diff") or "".join(patch_parts)
    _write(pack_root, pack_root / "change" / "commit.patch", patch_text)

    _write(pack_root, pack_root / "README.md", _render_readme(report, pack_name))
    _write(pack_root, pack_root / "pr" / "PR_BODY.md", _render_pr_body(report))
    _write(pack_root, pack_root / "evidence" / "FULL_THROTTLE_REPORT.md", _render_report_md(report))

    manifest = {
        "pack_name": pack_name,
        "strategy": STRATEGY,
        "status": "PR_READY" if applied else "BLOCKED",
        "review_required": True,
        "auto_merge": False,
        "repository": report.get("repo"),
        "created_utc": _created_utc(report),
        "activated_flags": report.get("activated_flags", []),
        "danger_excluded": report.get("summary", {}).get("held_danger", []),
        "staged_excluded": report.get("summary", {}).get("held_staged", []),
        "empirically_unsafe": [b["flag"] for b in report.get("backed_out_flags", [])],
        "test_delta": report.get("test_delta", {}),
        "test_command": report.get("test_command", []),
        "changed_files": sorted(by_file),
        "identity_lock_note": "full-throttle activation is a bounded, test-proven exception to "
        "Identity-Lock #1; danger flags and staged/dormant_by_design flags are "
        "never flipped, and the PR is never auto-merged.",
    }
    _write(
        pack_root,
        pack_root / "MANIFEST.json",
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )

    _write_checksums(pack_root)
    return pack_root, (0 if applied else 2)


def _write_checksums(pack_root: Path) -> None:
    entries = []
    for path in sorted(pack_root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append(f"{digest}  {path.relative_to(pack_root).as_posix()}")
    (pack_root / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report", type=Path, required=True, help="full_throttle.py --mode apply output"
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.repo_root.is_dir():
        print(f"FAIL: not a directory: {args.repo_root}", file=sys.stderr)
        return 2
    try:
        pack_root, code = build(args.report, args.repo_root, args.output)
    except (PackError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    status = "PR_READY" if code == 0 else "BLOCKED (no proven flips)"
    print(f"{status}: {pack_root}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
