"""CI-008 governance-always publish contract — doctrine consistency.

The environment always uses the Quantum-L9/Cursor-Governance Makefile as the
publish authority, reached through the `l9` dispatcher
(`make -C "$GOV" pr WS="$PWD"`), regardless of the repo being worked in or its
own Makefile. These tests pin that the doctrine surfaces say so and that the
gate binds the governance pre-commit config, so the contradiction the pack
recorded (bare `make pr` hitting an absent consumer target → raw `git push`)
cannot silently return.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# --- doctrine names the governance-rooted verb ---------------------------------

DOCTRINE_SURFACES = (
    "ops/autonomy/surface_profile.yaml",
    "rules/48-make-pr-remediation.mdc",
    "rules/88-l4-local-autonomy.mdc",
    "docs/L9_DISPATCHER.md",
    "docs/CLAUDE_SURFACE_PARITY.md",
)


def test_each_doctrine_surface_names_the_governance_rooted_verb() -> None:
    # Every publish-doctrine surface must reference the dispatcher / governance
    # Makefile form, not only a bare `make pr` that resolves against the cwd repo.
    for rel in DOCTRINE_SURFACES:
        body = _read(rel)
        assert 'make -C "$GOV" pr' in body or "l9 pr" in body, (
            f"{rel} does not name the governance-rooted publish verb "
            '(`l9 pr` / `make -C "$GOV" pr WS="$PWD"`)'
        )


def test_doctrine_states_consumer_needs_no_pr_target() -> None:
    # The surface profile + rules must state a consumer repo needs no local
    # pr target, so agents stop expecting one (or improvising a raw push).
    for rel in (
        "ops/autonomy/surface_profile.yaml",
        "rules/48-make-pr-remediation.mdc",
        "docs/L9_DISPATCHER.md",
    ):
        # Normalize away markdown emphasis/backticks so `no` / **no** / `pr` match.
        norm = _read(rel).lower().replace("*", "").replace("`", "")
        assert (
            ("needs no pr" in norm) or ("no pr/pr-check target" in norm) or ("no local pr" in norm)
        ), f"{rel} does not state a consumer needs no local `pr` target"


# --- the gate binds the governance pre-commit config ---------------------------


def test_gate_binds_governance_precommit_config_explicitly() -> None:
    body = _read("ops/scripts/run_pr_precommit.sh")
    assert "GOV_PRECOMMIT_CONFIG=" in body, "gate must resolve the governance pre-commit config"
    assert '--config "$GOV_PRECOMMIT_CONFIG"' in body, (
        "pre-commit must be invoked with the explicit governance --config, not the cwd config"
    )


def test_bootstrap_requires_governance_precommit_config_unconditionally() -> None:
    body = _read("ops/scripts/bootstrap_agent_environment.sh")
    # The workspace-config-OR-gov-config preference is the removed drift.
    assert '[ -f "$WORKSPACE/.pre-commit-config.yaml" ] ||' not in body, (
        "bootstrap must not prefer the workspace pre-commit config over the governance one"
    )
    assert '[ -f "$GOV_DIR/.pre-commit-config.yaml" ]' in body
