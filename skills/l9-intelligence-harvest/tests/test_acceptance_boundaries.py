from pathlib import Path

import yaml

PACK = Path(__file__).parents[1]


def test_beneficiary_none_targets_standalone_reuse():
    text = (PACK / "references/beneficiary-fit-contract.md").read_text()
    assert "beneficiary is `none`" in text and "standalone reusable placement" in text


def test_source_doctrine_not_archived_as_prompt_blob():
    assert not any("Gold Nugget Extractor" in p.name for p in PACK.rglob("*"))


def test_human_markdown_is_renderer_only():
    text = (PACK / "SKILL.md").read_text()
    assert "canonical product is `harvest.json`; Markdown is renderer-only" in text


def test_donor_instruction_cannot_gain_authority():
    policy = yaml.safe_load((PACK / "policies/harvest-policy.yaml").read_text())
    assert policy["security"]["donor_content_is_evidence_not_authority"] is True
    assert policy["security"]["execute_donor_code_by_default"] is False


def test_no_beneficiary_mutation_path():
    policy = yaml.safe_load((PACK / "policies/harvest-policy.yaml").read_text())
    assert policy["mutation"]["donor"] == "forbidden"
    assert policy["mutation"]["beneficiary"] == "forbidden"
    assert policy["mutation"]["beneficiary_implementation"] == "forbidden"
