"""ADR numbers are one decision each, and the generated index matches the files."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops/scripts/validate_adr_identity.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_adr_identity", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _adr(number: int, slug: str, title: str) -> str:
    return f"# ADR-{number:04d}: {title}\n\n## Status\n\nAccepted\n\n## Date\n\n2026-10-04\n"


def test_same_slug_pointer_and_body_are_one_decision(tmp_path: Path) -> None:
    module = _load()
    body = tmp_path / "environment/contracts/execution/adr/ADR-0017-peer.md"
    pointer = tmp_path / "docs/decisions/ADR-0017-peer.md"
    _write(body, _adr(17, "peer", "Peer core"))
    _write(
        pointer,
        "# ADR-0017: Peer core\n\n**Org catalog pointer only.** Canonical body:\n\n"
        "`environment/contracts/execution/adr/ADR-0017-peer.md`\n",
    )
    module.write_readme(tmp_path)
    assert module.check(tmp_path) == []


def test_different_slugs_with_one_number_fail(tmp_path: Path) -> None:
    module = _load()
    _write(
        tmp_path / "docs/decisions/ADR-0007-alpha.md",
        _adr(7, "alpha", "Alpha"),
    )
    _write(
        tmp_path / "docs/decisions/ADR-0007-beta.md",
        _adr(7, "beta", "Beta"),
    )
    findings = module.identity_findings(module.collect(tmp_path))
    assert any("ADR-0007 names more than one decision" in item for item in findings)


def test_bold_status_line_is_indexed(tmp_path: Path) -> None:
    module = _load()
    _write(
        tmp_path / "docs/decisions/ADR-0040-contracts.md",
        "# ADR-0040: Contracts own rule semantics\n\n"
        "**Status:** Accepted  \n**Date:** 2026-08-14\n",
    )
    records = module.collect(tmp_path)
    assert records[0].status == "Accepted"


def test_heading_number_must_match_filename(tmp_path: Path) -> None:
    module = _load()
    _write(
        tmp_path / "docs/decisions/ADR-0009-named.md",
        "# ADR-0008: Wrong heading\n\n## Status\n\nAccepted\n",
    )
    findings = module.identity_findings(module.collect(tmp_path))
    assert any("does not match filename" in item for item in findings)


def test_repository_adr_index_is_unique_and_current() -> None:
    module = _load()
    assert module.check(ROOT) == []
