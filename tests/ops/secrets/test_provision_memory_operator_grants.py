"""Operator grants derived from the org registry: dry run by default, ordered, no values out."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import provision_memory_operator_grants as prov  # noqa: E402

SUBJECT = "google-oauth2|subject-000000-SENTINEL"
SECRET_SENTINEL = "actor-binding-SECRET-sentinel"
COVERED = frozenset({"cursor-governance", "dot-github", "quantum-l9-github", "seo-bot"})
TYPED = ["cursor-governance", "quantum-l9-github"]


class FakeInfisical:
    def __init__(self, grants: dict[str, Any], actors: dict[str, Any] | None = None) -> None:
        self.store = {
            prov.GRANTS_NAME: json.dumps(grants),
            prov.ACTORS_NAME: json.dumps(
                actors if actors is not None else {SUBJECT: {"k": SECRET_SENTINEL}}
            ),
        }
        self.writes: list[dict[str, Any]] = []

    def __call__(self, method: str, path: str, body: dict[str, Any] | None) -> tuple[int, Any]:
        if method == "GET":
            name = path.split("/api/v3/secrets/raw/", 1)[1].split("?", 1)[0]
            return 200, {"secret": {"secretValue": self.store[name]}}
        assert method == "PATCH" and path == f"/api/v4/secrets/{prov.GRANTS_NAME}"
        assert body is not None
        assert body["projectId"] == "mem" and body["environment"] == "prod"
        self.writes.append(body)
        self.store[prov.GRANTS_NAME] = body["secretValue"]
        return 200, {"secret": {}}


def make(
    infisical: FakeInfisical,
    *,
    apply: bool = False,
    live: str | None = "3.0.0",
    refs: list[str] | None = None,
    **flags: bool,
) -> tuple[prov.Provisioner, list[str]]:
    lines: list[str] = []
    provisioner = prov.Provisioner(
        project="mem",
        infisical=infisical,
        covered=COVERED,
        live_version=lambda: live,
        profile_refs=lambda: refs if refs is not None else ["refs/tags/v3.1.0"],
        apply=apply,
        log=lines.append,
        **flags,
    )
    return provisioner, lines


def grant(read: list[str], write: list[str]) -> dict[str, Any]:
    return {
        SUBJECT: {
            "read_namespaces": read,
            "write_namespaces": write,
            "promote_namespaces": ["cursor-governance"],
            "roles": [],
        }
    }


def test_dry_run_reports_the_derivation_and_writes_nothing() -> None:
    fake = FakeInfisical(grant(TYPED, TYPED))
    provisioner, lines = make(fake)
    assert provisioner.run() == prov.EXIT_OK
    assert fake.writes == []
    assert any("would change" in line for line in lines)
    out = "\n".join(lines)
    assert SUBJECT not in out and SECRET_SENTINEL not in out
    assert "…NTINEL" in out


def test_apply_refuses_while_the_live_service_predates_the_token() -> None:
    fake = FakeInfisical(grant(TYPED, TYPED))
    provisioner, _ = make(fake, apply=True, live="3.0.0")
    with pytest.raises(prov.Stop, match="predates 3.1.0"):
        provisioner.run()
    assert fake.writes == []


def test_apply_refuses_when_the_live_version_is_unknown() -> None:
    fake = FakeInfisical(grant(TYPED, TYPED))
    provisioner, _ = make(fake, apply=True, live=None)
    with pytest.raises(prov.Stop, match="UNKNOWN"):
        provisioner.run()
    assert fake.writes == []


def test_apply_on_a_capable_service_writes_only_the_token_and_keeps_promote() -> None:
    fake = FakeInfisical(grant(TYPED, TYPED))
    provisioner, _ = make(fake, apply=True, live="3.1.0")
    assert provisioner.run() == prov.EXIT_OK
    written = json.loads(fake.store[prov.GRANTS_NAME])[SUBJECT]
    assert written["read_namespaces"] == [prov.TOKEN]
    assert written["write_namespaces"] == [prov.TOKEN]
    assert written["promote_namespaces"] == ["cursor-governance"]


def test_ahead_of_release_needs_a_profile_admitting_only_new_tags() -> None:
    fake = FakeInfisical(grant(TYPED, TYPED))
    old, _ = make(
        fake, apply=True, ahead_of_release=True, refs=["refs/tags/v3.1.0", "refs/tags/v3.0.1"]
    )
    with pytest.raises(prov.Stop, match="every admitted ref"):
        old.run()
    assert fake.writes == []
    ok, _ = make(fake, apply=True, ahead_of_release=True, refs=["refs/tags/v3.1.0"])
    assert ok.run() == prov.EXIT_OK
    assert len(fake.writes) == 1


def test_extras_stop_apply_until_a_decision_is_named() -> None:
    fake = FakeInfisical(grant(["custom-ns", *TYPED], TYPED))
    provisioner, lines = make(fake, apply=True, live="3.1.0")
    with pytest.raises(prov.Stop, match="extras present"):
        provisioner.run()
    assert any(
        "extra (not an org registry namespace)" in line and "custom-ns" in line for line in lines
    )
    keep, _ = make(fake, apply=True, live="3.1.0", keep_extra=True)
    assert keep.run() == prov.EXIT_OK
    written = json.loads(fake.store[prov.GRANTS_NAME])[SUBJECT]
    assert written["read_namespaces"] == [prov.TOKEN, "custom-ns"]


def test_already_derived_grant_is_a_no_op() -> None:
    fake = FakeInfisical(grant([prov.TOKEN], [prov.TOKEN]))
    provisioner, lines = make(fake, apply=True, live="3.0.0")
    assert provisioner.run() == prov.EXIT_OK
    assert fake.writes == []
    assert any("nothing to change" in line for line in lines)


def test_no_operator_subject_stops() -> None:
    fake = FakeInfisical(grant(TYPED, TYPED), actors={})
    provisioner, _ = make(fake)
    with pytest.raises(prov.Stop, match="binds no operator subject"):
        provisioner.run()


def test_registry_namespaces_reads_ids_and_only_their_legacy_names(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    (authority / "semantics").mkdir(parents=True)
    (authority / "semantics" / "repository_registry.yaml").write_text(
        "repositories:\n  - id: dot-github\n  - id: seo-bot\n", encoding="utf-8"
    )
    groups = tmp_path / "group_registry.yaml"
    groups.write_text(
        "repos:\n"
        "  dot-github: {legacy_namespaces: [quantum-l9-github]}\n"
        "  outside-org: {legacy_namespaces: [should-not-appear]}\n",
        encoding="utf-8",
    )
    covered = prov.registry_namespaces(authority, groups)
    assert covered == {"dot-github", "seo-bot", "quantum-l9-github"}


def test_empty_registry_refuses_to_derive(tmp_path: Path) -> None:
    (tmp_path / "semantics").mkdir()
    (tmp_path / "semantics" / "repository_registry.yaml").write_text(
        "repositories: []\n", encoding="utf-8"
    )
    with pytest.raises(prov.Stop, match="names no repository"):
        prov.registry_namespaces(tmp_path, tmp_path / "missing.yaml")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("3.1.0", (3, 1, 0)), ("v3.0.1", (3, 0, 1)), ("3.1", None), (None, None)],
)
def test_parse_version(text: str | None, expected: tuple[int, int, int] | None) -> None:
    assert prov.parse_version(text) == expected


def test_healthz_url_comes_from_the_resource_origin() -> None:
    assert (
        prov.healthz_url("https://memory.example.test/mcp") == "https://memory.example.test/healthz"
    )
    with pytest.raises(prov.Stop, match="not an https URL"):
        prov.healthz_url("http://memory.example.test/mcp")
