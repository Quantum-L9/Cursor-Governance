"""The bypass scan must match a declared token, not a word that starts with one.

`validate_commit_verification_contract.py` hand-maintained three literals in a
regex with no trailing boundary. That was wrong in both directions at once:

* it matched `--no-verify` inside `--no-verify-ancestry` — an argparse flag for
  skipping an origin/main reachability probe, not a bypass — so the gate failed
  on unmodified `main`, which teaches people to ignore it;
* it knew three literals while the declaration named more, so
  `--no-pre-commit-hook` (declared on six git subcommands) was never scanned.

The enforcer (`verification_bypass_gate`) never had either bug: it compares
whole tokens parsed from the command. Only the validator's line scan was wrong,
and only because it restated the declaration instead of reading it.

These tests assert the pattern's behavior, so a rewrite that keeps the names and
loses the boundary still fails.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "validate_commit_verification_contract.py"


def _module():
    sys.path.insert(0, str(ROOT / "ops" / "autonomy"))
    spec = importlib.util.spec_from_file_location("_ccv_validator", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def validator():
    return _module()


@pytest.fixture(scope="module")
def pattern(validator):
    return validator.bypass_pattern(validator.load_contract())


def test_longer_flag_sharing_a_prefix_is_not_a_bypass(pattern) -> None:
    """The reported failure: an ancestry-probe flag is not commit verification."""
    assert not pattern.search('        "--no-verify-ancestry",')
    assert not pattern.search("parser.add_argument('--no-verify-ancestry')")


def test_canonical_bypass_is_still_caught(pattern) -> None:
    """The boundary must not become an escape hatch."""
    assert pattern.search('git commit --no-verify -m "x"')
    assert pattern.search("git push --no-verify")
    assert pattern.search("git -c core.hooksPath=/dev/null commit")
    assert pattern.search("pre-commit uninstall")


def test_declared_flag_the_old_literal_list_missed_is_caught(pattern) -> None:
    """`--no-pre-commit-hook` is declared on six subcommands and was unscanned."""
    assert pattern.search("git commit --no-pre-commit-hook -m x")


def test_every_scannable_declared_token_is_matched(validator, pattern) -> None:
    """A form added to the declaration is scanned without a second edit here.

    `env_prefix` and `hook_path_write` are excluded by construction: they need
    the command's subcommand context, which a line scan does not have.
    """
    contract = validator.load_contract()
    scannable = {"git_flag", "git_global_config", "git_subcommand_args", "argv"}
    seen = 0
    for form in contract["forms"]:
        if form.get("detector") not in scannable:
            continue
        for token in (
            *(form.get("flags") or ()),
            *(form.get("keys") or ()),
            *(form.get("match_args") or ()),
        ):
            seen += 1
            assert pattern.search(f"run {token} now"), f"{form['id']}: {token} unscanned"
    assert seen, "no scannable tokens found — the derivation is not reading the contract"


def test_env_forms_are_left_to_the_enforcer(pattern) -> None:
    """Scanning bare `SKIP=` would flag the gate's own surface-aware skip list."""
    assert not pattern.search('_CORPUS_SKIP="sync-generated-artifacts,ruff"')
    assert not pattern.search('SKIP="$skip" pre-commit run --config "$CFG"')


def test_a_line_that_forbids_the_bypass_is_not_an_emission(validator, pattern) -> None:
    """Teaching against a bypass is the point, not a violation."""
    line = "# never use git commit --no-verify"
    assert pattern.search(line)
    assert validator._PROHIBITION.search(pattern.sub(" ", line))


def test_validator_passes_on_the_tracked_tree() -> None:
    """End to end: the gate is honest about this repository as it stands."""
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
