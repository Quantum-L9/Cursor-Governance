#!/usr/bin/env python3
"""Autonomous PR-body compile for make pr.

Fills the single template (.github/pull_request_template.md) from measured
facts: commit subjects, name-status, additive_only paths, ALLOW-ROOT-DELETION
markers, and gate/L4 receipts. Judgment leftovers are not required.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_body_completion.v1"
UNMEASURED = "not measured by open_pr_after_gate.sh — do not treat as verified"
PROTECTED_STAMP = "<!-- L9_PROTECTED_ROOT_PR -->"
NA = "n/a — not this change"
FIX_PLACEHOLDER = (
    "<!-- What you changed to make the problem above go away. "
    "Note alternatives you rejected and why. -->"
)
REVIEWER_PLACEHOLDER = (
    "<!-- Where to look hardest. Trade-offs accepted. Deferred follow-ups, with issue links. -->"
)
DELETION_RE = re.compile(r"ALLOW-ROOT-DELETION:\s*(?P<path>\S+?)\s*(?:—|-)\s+(?P<reason>\S.*)")
TYPE_LABELS = (
    "Bug fix",
    "Feature / enhancement",
    "Refactor (no behavior change)",
    "Documentation",
    "CI / governance change",
    "Breaking change",
)
RISK_LABELS = (
    "Low — additive, reversible, no data or contract change",
    "Medium — touches shared code, config, or a public interface",
    "High — breaking change, migration, IAM/network, or irreversible",
)

GOV_PREFIXES = (
    "commands/",
    "rules/",
    "skills/",
    "ops/",
    ".github/",
    "environment/",
)
DOCS_PREFIXES = ("docs/", "docs/plans/", "WIP/")


@dataclass
class MechanicalFacts:
    commits: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    issue_closes: list[int] = field(default_factory=list)
    gate_receipt: dict[str, Any] | None = None
    l4_receipt: dict[str, Any] | None = None
    campaign_body: str = ""
    template_path: str = ""
    additive_only_paths: list[str] = field(default_factory=list)
    deletion_markers: dict[str, str] = field(default_factory=dict)


@dataclass
class ComposeResult:
    body: str
    needs_completion: list[str]
    mechanical_filled: list[str]


def _run_git(workspace: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(workspace), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _l4_receipt_path(workspace: Path) -> Path:
    """Ask l4_local where the receipt is; never re-derive the location here.

    L4 state is not always at <workspace>/.l9/autonomy: L9_AUTONOMY_STATE_DIR
    relocates it, and a relocated directory is namespaced per workspace. A
    second component resolving the same state by its own rule is how a
    consumer silently reads nothing — the PR body would simply lose its L4
    section, with no error to notice. One owner, one resolver.
    """
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autonomy"))
        from l4_local import receipt_path

        return receipt_path(workspace)
    except Exception:  # noqa: BLE001 — fall back rather than break PR composition
        return workspace / ".l9" / "autonomy" / "l4-release-receipt.json"


def _issue_numbers(text: str) -> list[int]:
    found: list[int] = []
    patterns = (
        r"(?:Fixes|Closes)\s+#(\d+)",
        r"Issue-Remediation-Cycle:\s*\S+#(\d+)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            number = int(match.group(1))
            if number not in found:
                found.append(number)
    return found


def _deletion_markers(text: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    for match in DELETION_RE.finditer(text):
        markers[match.group("path").strip()] = match.group("reason").strip()
    return markers


def collect_mechanical(
    workspace: Path,
    *,
    pr_base: str,
    template_path: str = "",
    campaign_body: str = "",
    additive_only_paths: list[str] | None = None,
) -> MechanicalFacts:
    log = _run_git(workspace, "log", f"{pr_base}..HEAD", "--format=%s%n%b---END---")
    commits: list[str] = []
    issue_closes: list[int] = []
    markers: dict[str, str] = {}
    for block in log.split("---END---"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        commits.append(lines[0])
        issue_closes.extend(_issue_numbers(block))
        markers.update(_deletion_markers(block))
    names = _run_git(workspace, "diff", "--name-status", f"{pr_base}...HEAD")
    changed = [line.strip() for line in names.splitlines() if line.strip()]
    unique_issues: list[int] = []
    for number in issue_closes:
        if number not in unique_issues:
            unique_issues.append(number)
    return MechanicalFacts(
        commits=commits,
        changed_files=changed,
        issue_closes=unique_issues,
        gate_receipt=_load_json(workspace / ".l9" / "pr" / "gate-receipt.json"),
        l4_receipt=_load_json(_l4_receipt_path(workspace)),
        campaign_body=campaign_body.strip(),
        template_path=template_path,
        additive_only_paths=[p for p in (additive_only_paths or []) if p.strip()],
        deletion_markers=markers,
    )


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "_none measured_"
    return "\n".join(f"- {item}" for item in items)


def _changed_paths(facts: MechanicalFacts) -> list[str]:
    paths: list[str] = []
    for line in facts.changed_files:
        parts = line.split("\t", 1)
        rel = parts[-1].strip() if parts else ""
        if rel:
            paths.append(rel)
    return paths


def _first_subject(facts: MechanicalFacts) -> str:
    return facts.commits[0] if facts.commits else "measured change (no commit subject)"


def infer_type_of_change(facts: MechanicalFacts) -> str:
    paths = _changed_paths(facts)
    if facts.deletion_markers:
        return "Breaking change"
    if paths and all(path.startswith(DOCS_PREFIXES) or path.startswith("docs/") for path in paths):
        return "Documentation"
    if paths and all(path.startswith(GOV_PREFIXES) or path.startswith("docs/") for path in paths):
        return "CI / governance change"
    return "Feature / enhancement"


def infer_risk(facts: MechanicalFacts) -> str:
    if facts.deletion_markers:
        return RISK_LABELS[2]
    paths = _changed_paths(facts)
    if paths and all(path.startswith("docs/") or path.startswith("WIP/") for path in paths):
        return RISK_LABELS[0]
    return RISK_LABELS[1]


def _security_passed(facts: MechanicalFacts) -> bool:
    receipt = facts.gate_receipt or {}
    if not receipt:
        return False
    if receipt.get("security") in {"pass", "passed", "ok", True}:
        return True
    waves = receipt.get("waves")
    if isinstance(waves, dict):
        sec = waves.get("security")
        if sec in {"pass", "passed", True}:
            return True
        if isinstance(sec, dict) and sec.get("status") in {"pass", "passed"}:
            return True
    return receipt.get("schema") == "l9.pr_gate_receipt.v2"


def _needs_completion(template: str | None) -> list[str]:
    # Autonomous compile fills every heading the one template still carries.
    del template
    return []


def _annotate_unchecked_boxes(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if (
            re.match(r"^- \[ \] ", line)
            and UNMEASURED not in line
            and " — n/a" not in line
            and " — n/a —" not in line
        ):
            lines.append(f"{line} — {UNMEASURED}")
        else:
            lines.append(line)
    return "\n".join(lines)


def _evidence_lines(facts: MechanicalFacts) -> list[str]:
    evidence: list[str] = []
    if facts.gate_receipt:
        evidence.append(
            f"gate-receipt.json present: schema={facts.gate_receipt.get('schema')} "
            f"head={facts.gate_receipt.get('head')} "
            f"passed_at={facts.gate_receipt.get('passed_at')}"
        )
    else:
        evidence.append("gate-receipt.json absent — local gate result not measured here")
    if facts.l4_receipt:
        evidence.append(
            f"L4 receipt present: phase={facts.l4_receipt.get('phase')} "
            f"head={facts.l4_receipt.get('head_sha')}"
        )
    else:
        evidence.append("L4 receipt absent — release authorization not measured here")
    return evidence


def _check_box(text: str, label: str) -> str:
    pattern = re.compile(rf"^- \[ \] ([^\n]*{re.escape(label)}[^\n]*)$", re.M)
    return pattern.sub(r"- [x] \1", text, count=1)


def _na_unchecked_in_section(text: str, heading: str, until: str | None) -> str:
    start = text.find(heading)
    if start < 0:
        return text
    end = len(text)
    if until:
        nxt = text.find(until, start + len(heading))
        if nxt >= 0:
            end = nxt
    chunk = text[start:end]
    new_lines: list[str] = []
    for line in chunk.splitlines():
        if re.match(r"^- \[ \] ", line) and " — n/a" not in line:
            new_lines.append(f"{line} — {NA}")
        else:
            new_lines.append(line)
    return text[:start] + "\n".join(new_lines) + text[end:]


def _fill_protected_root(text: str, facts: MechanicalFacts) -> str:
    paths = facts.additive_only_paths
    if PROTECTED_STAMP not in text and paths:
        text = PROTECTED_STAMP + "\n" + text
    if not paths:
        text = text.replace(
            "- ` `",
            "- N/A — no additive_only root files",
            1,
        )
        why = "N/A — no additive_only root files in this diff."
        text = text.replace(
            "<!-- What cannot be done in a non-root path. Composer fills. -->",
            why,
            1,
        )
        text = text.replace(
            "<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->",
            "N/A — append-only — none.",
            1,
        )
        text = _na_unchecked_in_section(text, "### Edit mode", "## Problem")
        return text
    path_lines = "\n".join(f"- `{path}`" for path in paths)
    text = text.replace("- ` `", path_lines, 1)
    rewrite = any(path in facts.deletion_markers for path in paths)
    if rewrite:
        text = text.replace(
            "- [ ] **Justified rewrite**",
            "- [x] **Justified rewrite**",
            1,
        )
        reasons = "; ".join(
            f"{path}: {facts.deletion_markers[path]}"
            for path in paths
            if path in facts.deletion_markers
        )
        proof = reasons or "ALLOW-ROOT-DELETION present in range."
    else:
        text = text.replace(
            "- [ ] **Append-only**",
            "- [x] **Append-only**",
            1,
        )
        proof = "append-only — none."
    text = _na_unchecked_in_section(text, "### Edit mode", "## Problem")
    text = text.replace(
        "<!-- What cannot be done in a non-root path. Composer fills. -->",
        _first_subject(facts),
        1,
    )
    text = text.replace(
        "<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->",
        proof,
        1,
    )
    return text


def _fill_type_of_change(text: str, facts: MechanicalFacts) -> str:
    chosen = infer_type_of_change(facts)
    for label in TYPE_LABELS:
        if label == chosen:
            text = _check_box(text, label)
        else:
            text = re.sub(
                rf"^- \[ \] ([^\n]*{re.escape(label)}[^\n]*)$",
                rf"- [ ] \1 — {NA}",
                text,
                count=1,
                flags=re.M,
            )
    return text


def _fill_risk(text: str, facts: MechanicalFacts) -> str:
    chosen = infer_risk(facts)
    for label in RISK_LABELS:
        if label == chosen:
            text = _check_box(text, label)
        else:
            text = re.sub(
                rf"^- \[ \] ({re.escape(label)})$",
                rf"- [ ] \1 — {NA}",
                text,
                count=1,
                flags=re.M,
            )
    return text


def _fill_changes_by_intent(text: str, facts: MechanicalFacts) -> str:
    why = _first_subject(facts)
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for line in facts.changed_files:
        parts = line.split("\t")
        status = parts[0] if parts else "M"
        path = parts[-1] if parts else line
        bullet = f"- `{path}` — {why}"
        if status.startswith("A"):
            added.append(bullet)
        elif status.startswith("D"):
            deleted.append(bullet)
        else:
            modified.append(bullet)
    block = []
    block.append("**Added**")
    block.extend(added or ["- n/a"])
    block.append("")
    block.append("**Modified**")
    block.extend(modified or ["- n/a"])
    block.append("")
    block.append("**Deleted**")
    block.extend(deleted or ["- n/a"])
    replacement = "\n".join(block)
    pattern = re.compile(
        r"\*\*Added\*\*.*?\*\*Deleted\*\*\n- `path/to/dead.py`[^\n]*",
        re.S,
    )
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text


def _fill_gates(text: str, facts: MechanicalFacts) -> str:
    if _security_passed(facts):
        text = text.replace(
            "- [ ] No secrets, tokens, or customer data in code, tests, fixtures, or logs",
            "- [x] No secrets, tokens, or customer data in code, tests, fixtures, or logs",
            1,
        )
    return _na_unchecked_in_section(text, "## Gates", "## Reviewer focus")


def _fill_template(template: str, facts: MechanicalFacts) -> str:
    text = template
    commit_block = _bullet_list(facts.commits)
    files_block = _bullet_list(facts.changed_files)
    closes = ", ".join(f"#{n}" for n in facts.issue_closes) if facts.issue_closes else "#"
    subject = _first_subject(facts)
    text = _fill_protected_root(text, facts)
    error_fence = (
        "```\npaste the error / failing output here, or delete this block and describe the gap\n```"
    )
    text = text.replace(error_fence, subject, 1)
    if "## Summary" in text:
        text = text.replace(
            "<!-- One-sentence description of what this PR does. -->",
            subject,
            1,
        )
    text = re.sub(r"Closes #<!-- issue number -->", f"Closes {closes}", text, count=1)
    text = re.sub(r"Closes #(?!\d)", f"Closes {closes}", text, count=1)
    text = _fill_type_of_change(text, facts)
    if "## Fix" in text:
        text = text.replace(FIX_PLACEHOLDER, subject, 1)
        text = text.replace("<!-- What you changed -->", subject, 1)
    text = _fill_risk(text, facts)
    text = re.sub(r"(?m)^Rollback:\s*$", "Rollback: revert this PR", text, count=1)
    text = re.sub(
        r"(?m)^Blast radius:\s*$",
        "Blast radius: measured paths in Changes by intent",
        text,
        count=1,
    )
    evidence = _evidence_lines(facts)
    text = re.sub(
        r"```\n\$ pytest -q\n\$ ruff check \. && pyright\n```",
        "```\n" + "\n".join(evidence) + "\n```",
        text,
        count=1,
    )
    text = re.sub(
        r"_pending — the bot fills this in on push_",
        files_block,
        text,
        count=1,
    )
    text = _fill_gates(text, facts)
    if "## Reviewer focus" in text:
        text = text.replace(
            REVIEWER_PLACEHOLDER,
            "See Changes by intent and Protected-root (if any additive_only path).",
            1,
        )
    text = _fill_changes_by_intent(text, facts)
    if facts.l4_receipt and facts.l4_receipt.get("phase") == "release_authorized":
        text = text.replace("- [ ] **L4 local autonomy**", "- [x] **L4 local autonomy**", 1)
        text = text.replace("- [ ] **Post-exec kernels**", "- [x] **Post-exec kernels**", 1)
    del commit_block
    return _annotate_unchecked_boxes(text)


def compose_pr_body(facts: MechanicalFacts, template: str | None) -> ComposeResult:
    parts: list[str] = []
    filled = [
        "commits",
        "changed_files",
        "problem",
        "type of change",
        "risk",
        "rollback",
        "changes by intent",
    ]
    if facts.campaign_body:
        parts.append(facts.campaign_body.rstrip())
        parts.append("")
    parts.append("<!-- autonomous compile from open_pr_after_gate.sh -->")
    if template and template.strip():
        parts.append(_fill_template(template, facts))
        if facts.additive_only_paths:
            filled.append("protected-root")
    else:
        closes = ", ".join(f"#{n}" for n in facts.issue_closes)
        parts.extend(
            [
                "## Problem",
                "",
                _first_subject(facts),
                "",
                f"Closes {closes or '#'}",
                "",
                "## Files touched",
                "",
                _bullet_list(facts.changed_files),
            ]
        )
    parts.extend(["", "## Commits", "", _bullet_list(facts.commits), "", "## Test plan", ""])
    if facts.gate_receipt:
        parts.append("- [x] `make pr` local gate receipt present")
        filled.append("make pr gate receipt")
    else:
        parts.append(f"- [ ] `make pr` local gate receipt — {UNMEASURED}")
    if facts.l4_receipt and facts.l4_receipt.get("phase") == "release_authorized":
        parts.append("- [x] L4 release receipt present (`release_authorized`)")
        filled.append("L4 receipt")
    else:
        parts.append(f"- [ ] L4 release receipt — {UNMEASURED}")
    parts.append(f"- [ ] CI green — {UNMEASURED}")
    parts.extend(["", "## Changed files", "", _bullet_list(facts.changed_files)])
    if template and "## Evidence" not in template:
        parts.extend(["", "## Mechanical evidence", "", *_evidence_lines(facts)])
        filled.append("mechanical evidence")
    if facts.gate_receipt:
        filled.append("gate receipt in Evidence")
    if facts.l4_receipt:
        filled.append("L4 receipt in Evidence")
    return ComposeResult(
        body="\n".join(parts).rstrip() + "\n",
        needs_completion=_needs_completion(template),
        mechanical_filled=filled,
    )


def write_handoff(
    path: Path,
    *,
    result: ComposeResult,
    facts: MechanicalFacts,
    pr_number: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": SCHEMA,
        "pr_number": pr_number,
        "template": facts.template_path,
        "needs_completion": result.needs_completion,
        "mechanical_filled": result.mechanical_filled,
        "commit_count": len(facts.commits),
        "changed_file_count": len(facts.changed_files),
        "additive_only_paths": facts.additive_only_paths,
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _load_additive_only(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--pr-base", default="origin/main")
    parser.add_argument("--template", type=Path, default=None)
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument("--campaign-body-file", type=Path, default=None)
    parser.add_argument("--additive-only-file", type=Path, default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    args = parser.parse_args(argv)

    campaign = ""
    if args.campaign_body_file and args.campaign_body_file.is_file():
        campaign = args.campaign_body_file.read_text(encoding="utf-8")
    template_text = ""
    template_path = ""
    if args.template and args.template.is_file():
        template_text = args.template.read_text(encoding="utf-8")
        template_path = str(args.template)
    facts = collect_mechanical(
        args.workspace.resolve(),
        pr_base=args.pr_base,
        template_path=template_path,
        campaign_body=campaign,
        additive_only_paths=_load_additive_only(args.additive_only_file),
    )
    result = compose_pr_body(facts, template_text or None)
    if args.handoff:
        write_handoff(args.handoff, result=result, facts=facts, pr_number=args.pr_number)
    print(result.body, end="")
    if result.needs_completion:
        print(
            "PR body requires completion: " + "; ".join(result.needs_completion),
            file=__import__("sys").stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
