"""Pre-remediation PR digest wiring contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_poll_worker_requires_digest_before_remediation() -> None:
    prompt = ROOT / "skills/l9-bounded-autonomy/references/prompt-templates.md"
    text = prompt.read_text(encoding="utf-8")
    section = text.split("## poll_worker", 1)[1].split("## mutation_lane", 1)[0]
    digest = section.index("l9-pr-digest")
    remediation = section.index("l9-pr-remediation")
    assert digest < remediation
    assert "READY_FOR_REMEDIATION" in section
    assert "READY_WITH_NON_BLOCKING_NOTES" in section
    assert "NARROW_BEFORE_REMEDIATION" in section
    assert "ARCHITECTURE_REPAIR_BEFORE_REMEDIATION" in section
    assert "INTENT_UNKNOWN_REVIEW_REQUIRED" in section
    assert "exclusive remediation scope" in section


def test_digest_pack_is_read_only_and_machine_capable() -> None:
    skill = (ROOT / "skills/l9-pr-digest/SKILL.md").read_text(encoding="utf-8")
    assert "Never edit, push, comment on, relabel, close, or merge" in skill
    assert "scripts/pr_digest.py" in skill
    assert "LLM_judgement_questions" in skill
    assert "require_digest.py" in skill


def test_pr_slash_runs_digest_then_remediator_diagnose() -> None:
    command = (ROOT / "commands/pr.md").read_text(encoding="utf-8")
    contract = command.split("## Contract", 1)[1]
    digest = contract.index("l9-pr-digest")
    remediator = contract.index("l9-pr-remediation")
    assert digest < remediator
    assert "require_digest.py" in contract
    assert "Digest first" in contract
    assert "Never run Converge" in command.replace("*", "")


def test_digest_has_no_colliding_command_wrapper() -> None:
    assert not (ROOT / "commands/l9-pr-digest.md").exists()
    skill = (ROOT / "skills/l9-pr-digest/SKILL.md").read_text(encoding="utf-8")
    assert "/pr" in skill
    assert "require_digest.py" in skill


def test_remediator_consumes_digest_before_mutate() -> None:
    skill = (ROOT / "skills/l9-pr-remediation/SKILL.md").read_text(encoding="utf-8")
    diagnose = skill.index("## Diagnose")
    converge = skill.index("## Converge — Inputs → Actions")
    assert skill.find("l9-pr-digest", diagnose) != -1
    assert skill.find("require_digest.py --mode converge", converge) != -1
    workflow = (ROOT / "skills/l9-pr-remediation/references/diagnose-workflow.md").read_text(
        encoding="utf-8"
    )
    assert "Digest first (mandatory)" in workflow
    contract = (ROOT / "skills/l9-pr-remediation/references/run-contract.md").read_text(
        encoding="utf-8"
    )
    assert "P_digest" in contract
