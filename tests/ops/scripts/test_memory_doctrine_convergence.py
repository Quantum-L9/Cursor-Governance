"""Anti-regression ratchet for the memory doctrine convergence (PR #509 closure).

Locks ADR-0030 items 7-9 / CANONICAL_LAW 8.3 into
``ops/scripts/validate_legacy_doctrine_residue.py``:

* converged surfaces (rules 03/87/97/98 + projections, the memory skills, the
  active memory docs) FAIL when they teach the retired client as live, provider
  URL / bearer possession, Graphiti ``inject`` / PICKUP as the current resume
  SSOT, or generic ingest / the operator CLI ``write`` as the model's alternative
  to ``memory.write_governed`` -- and FAIL when they stop carrying the governed
  write contract;
* ADRs and the append-only root files may keep historical text only under a
  dated supersession / amendment heading naming ADR-0030;
* not-yet-converged surfaces are reported as WARN and tightened to FAIL by
  ``--strict-memory-doctrine`` (the ratchet only tightens).

Provider variable names in fixtures are assembled from parts so the fixture
text is never itself an egress-scanner literal.
"""

from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "ops" / "scripts" / "validate_legacy_doctrine_residue.py"

_URL_VAR = "GRAPHITI_MCP_" + "URL"
_TOKEN_VAR = "GRAPHITI_MCP_" + "TOKEN"


def _load():
    spec = importlib.util.spec_from_file_location("validate_legacy_doctrine_residue", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def residue():
    return _load()


def _run(residue, root: Path, *flags: str) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out):
        rc = residue.main(["--root", str(root), *flags])
    return rc, out.getvalue()


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


#: A minimal converged tree that satisfies every positive-presence check.
def _converged_tree(root: Path) -> None:
    for rel, tokens in _load().MEMORY_DOCTRINE_REQUIRED_TOKENS.items():
        body = "# converged\n\n" + "\n".join(f"- carries `{t}`" for t in tokens) + "\n"
        _write(root, rel, body)


# --------------------------------------------------------------------------- #
# Positive: the real repository passes and carries the contract
# --------------------------------------------------------------------------- #


def test_the_real_repository_passes_the_ratchet(residue) -> None:
    rc, out = _run(residue, ROOT)
    assert rc == 0, out
    assert "PASS" in out


@pytest.mark.parametrize("rel", sorted(_load().MEMORY_DOCTRINE_REQUIRED_TOKENS))
def test_converged_surface_carries_the_governed_write_contract(residue, rel: str) -> None:
    text = (ROOT / rel).read_text(encoding="utf-8")
    for token in residue.MEMORY_DOCTRINE_REQUIRED_TOKENS[rel]:
        assert token in text, f"{rel} lost `{token}`"
    assert not residue.memory_doctrine_hits(text), residue.memory_doctrine_hits(text)


def test_gmp_phase0_no_longer_cites_episode_names(residue) -> None:
    for rel in residue.MEMORY_DOCTRINE_FORBIDDEN_TOKENS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "<episode names>" not in text, rel
        assert "snapshot_digest" in text, rel


@pytest.mark.parametrize(
    "rel",
    [
        "docs/decisions/ADR-0002-memory-enforcement-contract.md",
        "docs/decisions/ADR-0003-memory-two-entry-points-one-contract.md",
        "docs/decisions/ADR-0004-hook-memory-client-contract-pin.md",
        "docs/decisions/ADR-0005-one-agent-memory-domain-out-of-band.md",
        "docs/decisions/ADR-0006-single-memory-front-door-graphiti.md",
        "docs/decisions/ADR-0007-cloud-graphiti-https-reachability.md",
        "docs/decisions/ADR-0028-session-hydrate-close-visibility.md",
        "docs/decisions/ADR-0029-surface-hook-divergence.md",
        "docs/decisions/ADR-0030-memory-control-plane-single-front-door.md",
        "CANONICAL_LAW.md",
        "AGENTS.md",
    ],
)
def test_amended_authorities_carry_a_dated_marker(residue, rel: str) -> None:
    assert residue.has_supersession_marker((ROOT / rel).read_text(encoding="utf-8")), rel


# --------------------------------------------------------------------------- #
# Negative: each retired teaching fails on a converged surface
# --------------------------------------------------------------------------- #


STALE_TEACHINGS = {
    "retired-client-live": (
        "Run `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py inject "
        '"task"` at resume.\n'
    ),
    "provider-possession": (
        f"Every surface sets:\n\n```bash\n{_URL_VAR}=https://example.invalid/graphiti/mcp\n"
        f"{_TOKEN_VAR}=<bearer>\n```\n"
    ),
    "graphiti-inject-pickup-resume-ssot": (
        "**Updated: 2026-08-06** — Resume SSOT is **Graphiti** (`inject` / PICKUP episodes).\n"
    ),
    "generic-write-as-model-write": (
        '3. **Write to memory:** `memcli write "LESSON: ..." --kind lesson`\n'
    ),
}


@pytest.mark.parametrize("finding", sorted(STALE_TEACHINGS))
def test_stale_teaching_fails_on_a_converged_surface(residue, tmp_path: Path, finding: str) -> None:
    _converged_tree(tmp_path)
    rel = "rules/03-graphiti-memory.mdc"
    original = (tmp_path / rel).read_text(encoding="utf-8")
    _write(tmp_path, rel, original + "\n" + STALE_TEACHINGS[finding])
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert f"[{finding}]" in out, out
    assert rel in out


def test_generic_ingest_as_model_write_fails_on_a_converged_surface(
    residue, tmp_path: Path
) -> None:
    _converged_tree(tmp_path)
    rel = "skills/l9-chat-extraction/references/extract-chat.md"
    original = (tmp_path / rel).read_text(encoding="utf-8")
    _write(tmp_path, rel, original + "\nCall memory.ingest with the lesson as content.\n")
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "[generic-write-as-model-write]" in out


def test_pickup_string_through_generic_write_fails_on_a_converged_surface(
    residue, tmp_path: Path
) -> None:
    _converged_tree(tmp_path)
    rel = "skills/l9-end-session/references/end-session-protocol.md"
    original = (tmp_path / rel).read_text(encoding="utf-8")
    _write(
        tmp_path,
        rel,
        original + '\nmemcli write "PICKUP|date=today|task=x" --kind pickup_context\n',
    )
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "[generic-write-as-model-write]" in out


def test_dropping_the_governed_write_contract_fails(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    rel = "rules/87-cursor-memory-kernel.mdc"
    _write(tmp_path, rel, "# rewritten\n\nUse `memcli write` for everything.\n")
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "no longer carries `memory.write_governed`" in out
    assert "no longer carries `memory.phase_lock`" in out


def test_missing_converged_surface_fails(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    (tmp_path / "ops/memory/README.md").unlink()
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "ops/memory/README.md: converged surface missing" in out


def test_episode_names_semantics_fail_on_the_gmp_skill(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    rel = "skills/l9-gmp-protocol/SKILL.md"
    original = (tmp_path / rel).read_text(encoding="utf-8")
    _write(tmp_path, rel, original + "\nDeclare `MEMORY_PREFETCH: <episode names>`.\n")
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "re-teaches `<episode names>`" in out


# --------------------------------------------------------------------------- #
# Allowances: retirement notices and operator forms are not regressions
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "notice",
    [
        "`ops/graphiti/graphiti_memory_client.py write` is retired; "
        "use `hydration.cli repair-write`.\n",
        f"The scanner flags `{_URL_VAR}` and `{_TOKEN_VAR}`; "
        "no surface holds either (forbidden).\n",
        "A Graphiti `inject` / PICKUP read is not a resume layer: the client is a tombstone.\n",
        'memcli write "durable fact" --kind lesson --agent-id cursor   # operator form\n',
        "Generic `memory.ingest` is not the model's alternative to `memory.write_governed`.\n",
    ],
)
def test_retirement_notices_and_operator_forms_are_allowed(residue, notice: str) -> None:
    assert residue.memory_doctrine_hits(notice) == []


def test_paragraph_context_licenses_a_retirement_notice(residue) -> None:
    text = (
        "> **Retired CLI:** the former client is removed.\n"
        '> Do not run `graphiti_memory_client.py inject "<task>"` at resume;\n'
        "> the canonical hydrate replaces it.\n"
    )
    assert residue.memory_doctrine_hits(text) == []


# --------------------------------------------------------------------------- #
# ADRs and root authority files: historical text needs a dated marker
# --------------------------------------------------------------------------- #


def test_adr_history_without_a_dated_supersession_marker_fails(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    rel = "docs/decisions/ADR-0099-fixture.md"
    _write(
        tmp_path,
        rel,
        "# ADR-0099\n\n## Decision\n\n"
        "1. `/end-session` owns `graphiti_memory_client.py write --kind pickup_context`.\n",
    )
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "no dated supersession/amendment heading naming ADR-0030" in out
    assert rel in out


def test_adr_history_with_a_dated_supersession_marker_passes(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    rel = "docs/decisions/ADR-0099-fixture.md"
    _write(
        tmp_path,
        rel,
        "# ADR-0099\n\n## Decision\n\n"
        "1. `/end-session` owns `graphiti_memory_client.py write --kind pickup_context`.\n\n"
        "## Amendment (2026-09-07) — repair is canonical (ADR-0030)\n\n"
        "The repair is `hydration.cli repair-write` over `ops/memory`.\n",
    )
    rc, out = _run(residue, tmp_path)
    assert rc == 0, out


def test_root_authority_history_needs_the_marker(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    stale = "| MCP interface | run `graphiti_memory_client.py health` | L9-Ops-MCP |\n"
    _write(tmp_path, "AGENTS.md", "# AGENTS\n\n" + stale)
    rc, out = _run(residue, tmp_path)
    assert rc == 1, out
    assert "AGENTS.md" in out
    _write(
        tmp_path,
        "AGENTS.md",
        "# AGENTS\n\n"
        + stale
        + "\n## Memory control plane (2026-09-06) — supersedes §7\n\nCurrent.\n",
    )
    rc, out = _run(residue, tmp_path)
    assert rc == 0, out


# --------------------------------------------------------------------------- #
# The ratchet only tightens: WARN today, FAIL under --strict-memory-doctrine
# --------------------------------------------------------------------------- #


def test_unconverged_surface_warns_then_fails_under_strict(residue, tmp_path: Path) -> None:
    _converged_tree(tmp_path)
    _write(
        tmp_path,
        "commands/fixture-session.md",
        "| Resume SSOT | Graphiti inject / PICKUP |\n"
        "\n"
        "Resume SSOT is Graphiti inject.\n",
    )
    rc, out = _run(residue, tmp_path)
    assert rc == 0, out
    assert "WARN" in out and "commands/fixture-session.md" in out
    rc, out = _run(residue, tmp_path, "--strict-memory-doctrine")
    assert rc == 1, out
    assert "(strict)" in out


def test_surface_classes_are_declared_not_inferred(residue) -> None:
    assert residue._surface_class(ROOT, "rules/03-graphiti-memory.mdc") == "FAIL"
    assert residue._surface_class(ROOT, "CANONICAL_LAW.md") == "AMENDED"
    assert residue._surface_class(ROOT, "docs/decisions/ADR-0030-x.md") == "AMENDED"
    assert residue._surface_class(ROOT, "commands/start-session.md") == "WARN"
    for rel in residue.MEMORY_DOCTRINE_FAIL_SURFACES:
        assert (ROOT / rel).is_file(), rel
