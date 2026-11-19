"""The organization-policy bind names the .github pin and the local projection separately."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ops.autonomy.org_policy_binding import AUTHORITY_CLAIMS, ROLES, bind, govern, main

ROOT = Path(__file__).resolve().parents[3]


def test_bound_projection_is_not_the_upstream_bytes() -> None:
    item = bind("session", ROOT)
    assert item["status"] == "BOUND"
    assert item["repository"] == "Quantum-L9/.github"
    assert item["path"] == "policies/ORG_INVARIANTS.yaml"
    assert item["admission"] is False
    assert item["signature_status"] == "UNKNOWN"
    assert item["release_status"] == "BLOCKED"
    assert item["projection_canonical"] is False
    assert item["payload_sha256"] != item["projection_sha256"]
    local = ROOT / "ORG_INVARIANTS.yaml"
    assert hashlib.sha256(local.read_bytes()).hexdigest() == item["projection_sha256"]


def test_each_role_has_its_own_constraint() -> None:
    seen = set()
    for role in ROLES:
        item = bind(role, ROOT)
        assert item["status"] == "BOUND"
        assert item["must_not"]
        seen.add(tuple(item["must_not"]))
    assert len(seen) == len(ROLES)


def test_stale_when_the_projection_digest_changes(tmp_path: Path) -> None:
    source = ROOT / "governance" / "authority-bindings" / "org-invariants.yaml"
    binding = tmp_path / "governance" / "authority-bindings"
    binding.mkdir(parents=True)
    text = source.read_text(encoding="utf-8").replace(
        "b432ab6366e7090d862ee108f1a15c8fbdd3e6e9dfdf4fe87d682fcc288abb9a",
        "a" * 64,
    )
    (binding / "org-invariants.yaml").write_text(text, encoding="utf-8")
    projection = tmp_path / "ORG_INVARIANTS.yaml"
    projection.write_bytes((ROOT / "ORG_INVARIANTS.yaml").read_bytes())
    item = bind("cto", tmp_path)
    assert item["status"] == "STALE"
    assert "author organization policy" in item["must_not"]


def test_local_admission_text_does_not_authorize_a_claim(tmp_path: Path) -> None:
    source = ROOT / "governance" / "authority-bindings" / "org-invariants.yaml"
    binding = tmp_path / "governance" / "authority-bindings"
    binding.mkdir(parents=True)
    text = source.read_text(encoding="utf-8")
    text = text.replace("admission: false", "admission: true", 1)
    text = text.replace("signature_status: UNKNOWN", "signature_status: verified", 1)
    text = text.replace("release_status: BLOCKED", "release_status: verified", 1)
    (binding / "org-invariants.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "ORG_INVARIANTS.yaml").write_bytes((ROOT / "ORG_INVARIANTS.yaml").read_bytes())
    for action in AUTHORITY_CLAIMS:
        decision = govern(action, "session", tmp_path)
        assert decision["allowed"] is False
    assert govern("make_pr", "session", tmp_path)["allowed"] is True
    assert main(["--action", "claim_admission", "--root", str(tmp_path)]) == 1
    assert main(["--format", "markdown", "--root", str(ROOT)]) == 0


def test_mode_status_denies_every_authority_claim() -> None:
    from ops.autonomy.projection_mode import _policy_denials

    denials = _policy_denials("cto")
    assert [item["action"] for item in denials] == list(AUTHORITY_CLAIMS)
    assert all(item["allowed"] is False for item in denials)
