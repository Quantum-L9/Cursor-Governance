#!/usr/bin/env python3
"""Mechanical PR-body prefill for make pr.

Fills only facts the publish path already measured: commit subjects, changed
files, gate-receipt / L4-receipt presence. Judgment sections stay empty and
are listed as needing completion. Unverified governance boxes stay unchecked.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_body_completion.v1"
UNMEASURED = "not measured by open_pr_after_gate.sh — do not treat as verified"
JUDGMENT_HEADINGS = (
    ("## Problem", "Problem (human/agent summary)"),
    ("## Summary", "Summary (human/agent sentence)"),
    ("## Fix", "Fix (alternatives rejected)"),
    ("## Type of Change", "Type of Change"),
    ("## Risk", "Risk"),
    ("## Breaking Change", "Breaking Change / rollback"),
    ("## Rollback Plan", "Rollback Plan"),
    ("## Reviewer focus", "Reviewer focus"),
    ("## Changes by intent", "Changes by intent"),
)


@dataclass
class MechanicalFacts:
    commits: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    issue_closes: list[int] = field(default_factory=list)
    gate_receipt: dict[str, Any] | None = None
    l4_receipt: dict[str, Any] | None = None
    campaign_body: str = ""
    template_path: str = ""


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


def collect_mechanical(
    workspace: Path,
    *,
    pr_base: str,
    template_path: str = "",
    campaign_body: str = "",
) -> MechanicalFacts:
    log = _run_git(workspace, "log", f"{pr_base}..HEAD", "--format=%s%n%b---END---")
    commits: list[str] = []
    issue_closes: list[int] = []
    for block in log.split("---END---"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        commits.append(lines[0])
        issue_closes.extend(_issue_numbers(block))
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
        l4_receipt=_load_json(workspace / ".l9" / "autonomy" / "l4-release-receipt.json"),
        campaign_body=campaign_body.strip(),
        template_path=template_path,
    )


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "_none measured_"
    return "\n".join(f"- {item}" for item in items)


def _needs_completion(template: str | None) -> list[str]:
    text = template or ""
    if not text.strip():
        return [label for _, label in JUDGMENT_HEADINGS[:5]]
    return [label for heading, label in JUDGMENT_HEADINGS if heading in text]


def _annotate_unchecked_boxes(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^- \[ \] ", line) and UNMEASURED not in line:
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


def _check_measured_l4_boxes(text: str, facts: MechanicalFacts) -> str:
    if not (facts.l4_receipt and facts.l4_receipt.get("phase") == "release_authorized"):
        return text
    text = text.replace("- [ ] **L4 local autonomy**", "- [x] **L4 local autonomy**", 1)
    return text.replace("- [ ] **Post-exec kernels**", "- [x] **Post-exec kernels**", 1)


def _fill_template(template: str, facts: MechanicalFacts) -> str:
    text = template
    commit_block = _bullet_list(facts.commits)
    files_block = _bullet_list(facts.changed_files)
    closes = ", ".join(f"#{n}" for n in facts.issue_closes) if facts.issue_closes else "#"
    if "## Summary" in text and "Mechanical commit subjects" not in text:
        text = text.replace(
            "<!-- One-sentence description of what this PR does. -->",
            "<!-- One-sentence description of what this PR does. -->\n\n"
            "Mechanical commit subjects (judgment sentence still required):\n\n"
            f"{commit_block}",
            1,
        )
    error_fence = (
        "```\npaste the error / failing output here, or delete this block and describe the gap\n```"
    )
    text = text.replace(
        error_fence,
        "Mechanical (commit subjects — judgment still required above):\n\n" + commit_block,
        1,
    )
    text = re.sub(r"Closes #<!-- issue number -->", f"Closes {closes}", text, count=1)
    text = re.sub(r"Closes #(?!\d)", f"Closes {closes}", text, count=1)
    if "## Fix" in text and "Mechanical commit subjects" not in text.split("## Fix", 1)[1][:400]:
        text = text.replace(
            "## Fix\n",
            "## Fix\n\n"
            "Mechanical commit subjects (not a substitute for alternatives rejected):\n\n"
            f"{commit_block}\n\n",
            1,
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
    text = _check_measured_l4_boxes(text, facts)
    return _annotate_unchecked_boxes(text)


def compose_pr_body(facts: MechanicalFacts, template: str | None) -> ComposeResult:
    parts: list[str] = []
    filled = ["commits", "changed_files"]
    if facts.campaign_body:
        parts.append(facts.campaign_body.rstrip())
        parts.append("")
    parts.append(
        "<!-- mechanical prefill from open_pr_after_gate.sh; "
        "judgment sections still require completion -->"
    )
    if template and template.strip():
        parts.append(_fill_template(template, facts))
    else:
        closes = ", ".join(f"#{n}" for n in facts.issue_closes)
        parts.extend(
            [
                "## Problem",
                "",
                "Mechanical commit subjects (judgment still required):",
                "",
                _bullet_list(facts.commits),
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
        parts.append("- [x] `make pr-check` local gate receipt present")
        filled.append("make pr-check receipt")
    else:
        parts.append(f"- [ ] `make pr-check` local gate receipt — {UNMEASURED}")
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
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--pr-base", default="origin/main")
    parser.add_argument("--template", type=Path, default=None)
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument("--campaign-body-file", type=Path, default=None)
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
