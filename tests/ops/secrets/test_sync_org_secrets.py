"""sync_actions_secrets org targets (#892) and drift check (#870).

Frozen interface (lane L2 -> lane L3 secret-drift workflow):

    sync_actions_secrets.py --org ORG --app {actions,dependabot}
        [--check] [--report-json PATH] [NAME ...]

``--check`` compares names and timestamps only; values are never read,
printed or compared. Exit 0 in sync, 1 drift/missing, 2 plan/transport error.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import sync_actions_secrets as sas  # noqa: E402

ORG = "Quantum-L9"
CANARIES = {
    "SONAR_TOKEN": "canary-sonar-org-31aa-not-real",
    "GITHUB_TOKEN": "canary-pat-org-8c02-not-real",
}


def _assert_no_leak(text: str) -> None:
    for value in CANARIES.values():
        assert value not in text


class FakeGh:
    """Fake ``gh``: org secret metadata, read probes and ``gh secret set``.

    ``org`` maps ``(app, NAME)`` to an ``updated_at`` string, or to an int HTTP
    status that the metadata read fails with.
    """

    def __init__(
        self,
        org: dict[tuple[str, str], str | int] | None = None,
        *,
        probe_ok: bool = True,
        set_rc: int = 0,
    ) -> None:
        self.org = org or {}
        self.probe_ok = probe_ok
        self.set_rc = set_rc
        self.calls: list[dict[str, Any]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": list(argv), **kwargs})
        if argv[:2] == ["gh", "api"] and argv[2].startswith(f"orgs/{ORG}/"):
            _, _, app, _, name = argv[2].split("/")
            state = self.org.get((app, name), 404)
            if isinstance(state, int):
                reason = "Not Found" if state == 404 else "Forbidden"
                return subprocess.CompletedProcess(
                    argv, 1, '{"message":"x"}', f"gh: {reason} (HTTP {state})\n"
                )
            body = {
                "name": name,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": state,
                "visibility": "private",
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(body), "")
        if argv[:2] == ["gh", "api"]:
            rc = 0 if self.probe_ok else 1
            return subprocess.CompletedProcess(argv, rc, "3\n" if rc == 0 else "", "")
        if argv[:3] == ["gh", "secret", "set"]:
            return subprocess.CompletedProcess(argv, self.set_rc, "", "")
        raise AssertionError(f"unexpected command {argv[:3]}")

    def secret_sets(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["argv"][:3] == ["gh", "secret", "set"]]

    def probes(self) -> list[str]:
        return [
            c["argv"][2]
            for c in self.calls
            if c["argv"][:2] == ["gh", "api"] and c["argv"][2].startswith("repos/")
        ]


@pytest.fixture
def fake_bind(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    values = dict(CANARIES)

    def bind(name: str, **_kwargs: Any) -> str | None:
        value = values.get(name)
        sas.cb._SOURCES[name] = "infisical" if value else "unbound"
        return value

    monkeypatch.setattr(sas.cb, "bind", bind)
    monkeypatch.setattr(sas.cb, "reset_cache", lambda: None)
    return values


@pytest.fixture
def vault(monkeypatch: pytest.MonkeyPatch) -> dict[str, str | int]:
    """Infisical metadata: vault name -> ``updatedAt`` or an HTTP status."""
    state: dict[str, str | int] = {
        "GITHUB_TOKEN": "2026-11-01T10:00:00.000Z",
        "SONAR_TOKEN": "2026-10-01T10:00:00.000Z",
    }

    def fetch(name: str) -> sas.VaultMeta:
        value = state.get(name, 404)
        if isinstance(value, int):
            return sas.VaultMeta(status=value, updated_at=None)
        return sas.VaultMeta(status=200, updated_at=value)

    def never_bind(*_a: Any, **_k: Any) -> None:
        raise AssertionError("--check must never bind a secret value")

    monkeypatch.setattr(sas, "vault_metadata", fetch)
    monkeypatch.setattr(sas.cb, "bind", never_bind)
    return state


def _install(monkeypatch: pytest.MonkeyPatch, gh: FakeGh) -> FakeGh:
    monkeypatch.setattr(sas.subprocess, "run", gh)
    return gh


# --- plan ------------------------------------------------------------------


def test_committed_plan_declares_org_targets() -> None:
    plan = sas.load_plan()
    by_name = {t.target_name: t for t in plan.org_secrets}
    assert set(by_name) == {"SDK_TOKEN", "SONAR_TOKEN"}
    sdk = by_name["SDK_TOKEN"]
    assert sdk.org == ORG
    assert sdk.apps == ("actions", "dependabot")
    assert sdk.vault_name == "GITHUB_TOKEN"
    assert set(sdk.must_read) == {
        "Quantum-L9/Cognitive.Engine.Graphs",
        "Quantum-L9/Gate_SDK",
    }
    assert by_name["SONAR_TOKEN"].apps == ("actions",)
    assert by_name["SONAR_TOKEN"].vault_name == "SONAR_TOKEN"
    assert {t.vault_name for t in plan.org_secrets} <= sas.root_env_keys()
    assert [t.target_name for t in sas.org_targets(plan, ORG, "dependabot")] == ["SDK_TOKEN"]
    assert {t.target_name for t in sas.org_targets(plan, ORG, "actions")} == {
        "SDK_TOKEN",
        "SONAR_TOKEN",
    }


def _org_plan(tmp_path: Path, **override: Any) -> Path:
    target = {
        "org": "o",
        "secret": "X_TOKEN",
        "vault_name": "SONAR_TOKEN",
        "apps": ["actions"],
        "visibility": "private",
    }
    target.update(override)
    plan = {"schema": sas.SCHEMA, "secrets": [], "org_secrets": [target]}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"apps": ["codespaces"]}, "apps"),
        ({"apps": []}, "apps"),
        ({"apps": ["actions", "actions"]}, "apps"),
        ({"visibility": "public"}, "visibility"),
        ({"visibility": "selected"}, "repositories"),
        ({"visibility": "selected", "repositories": ["other/r"]}, "repositories"),
        ({"repositories": ["r"]}, "repositories"),
        ({"vault_name": "NOT_A_VAULT_KEY"}, "NOT_A_VAULT_KEY"),
        ({"must_read": "o/r"}, "must_read"),
        ({"org": "bad org"}, "org"),
        ({"org": "trailing-"}, "org"),
        ({"secret": "SONAR_TOKEN\n"}, "secret"),
    ],
)
def test_org_target_schema_rejects(tmp_path: Path, override: dict[str, Any], match: str) -> None:
    plan = _org_plan(tmp_path, **override)
    with pytest.raises(sas.PlanError, match=match):
        sas.load_plan(plan)


def test_org_target_schema_accepts_selected(tmp_path: Path) -> None:
    plan = sas.load_plan(_org_plan(tmp_path, visibility="selected", repositories=["o/a", "o/b"]))
    (target,) = plan.org_secrets
    assert target.repositories == ("o/a", "o/b")


# --- check: verdicts and exit codes ------------------------------------------


def _check(tmp_path: Path, *extra: str, app: str = "actions") -> tuple[int, dict[str, Any]]:
    report = tmp_path / "drift.json"
    rc = sas.main(["--org", ORG, "--app", app, "--check", "--report-json", str(report), *extra])
    data = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    return rc, data


def test_check_in_sync_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    gh = _install(
        monkeypatch,
        FakeGh(
            {
                ("actions", "SDK_TOKEN"): "2026-11-02T00:00:00Z",
                ("actions", "SONAR_TOKEN"): "2026-10-01T10:00:00Z",
            }
        ),
    )
    rc, data = _check(tmp_path)
    assert rc == 0
    assert data["schema"] == "l9.secret-drift.v1"
    assert (data["org"], data["app"]) == (ORG, "actions")
    rows = {r["name"]: r for r in data["rows"]}
    assert set(rows) == {"SDK_TOKEN", "SONAR_TOKEN"}
    assert {r["verdict"] for r in rows.values()} == {"in_sync"}
    assert set(rows["SDK_TOKEN"]) == {"name", "org_updated_at", "vault_updated_at", "verdict"}
    assert rows["SDK_TOKEN"]["vault_updated_at"] == "2026-11-01T10:00:00.000Z"
    assert gh.secret_sets() == []


def test_check_org_older_than_vault_is_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    _install(
        monkeypatch,
        FakeGh(
            {
                ("actions", "SDK_TOKEN"): "2026-10-31T23:59:59Z",
                ("actions", "SONAR_TOKEN"): "2026-10-02T00:00:00Z",
            }
        ),
    )
    rc, data = _check(tmp_path)
    assert rc == 1
    verdicts = {r["name"]: r["verdict"] for r in data["rows"]}
    assert verdicts == {"SDK_TOKEN": "drift", "SONAR_TOKEN": "in_sync"}


def test_check_missing_in_org_and_missing_in_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    del vault["SONAR_TOKEN"]
    _install(monkeypatch, FakeGh({("actions", "SONAR_TOKEN"): "2026-10-02T00:00:00Z"}))
    rc, data = _check(tmp_path)
    assert rc == 1
    rows = {r["name"]: r for r in data["rows"]}
    assert rows["SDK_TOKEN"]["verdict"] == "missing_in_org"
    assert rows["SDK_TOKEN"]["org_updated_at"] is None
    assert rows["SONAR_TOKEN"]["verdict"] == "missing_in_vault"
    assert rows["SONAR_TOKEN"]["vault_updated_at"] is None


def test_check_org_read_403_exits_two_and_writes_no_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    report = tmp_path / "drift.json"
    report.write_text("stale", encoding="utf-8")
    _install(
        monkeypatch,
        FakeGh({("actions", "SDK_TOKEN"): 403, ("actions", "SONAR_TOKEN"): "2026-10-02T00:00:00Z"}),
    )
    rc = sas.main(["--org", ORG, "--app", "actions", "--check", "--report-json", str(report)])
    assert rc == 2
    assert not report.exists()


def test_check_vault_transport_error_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    vault["SONAR_TOKEN"] = 0
    _install(
        monkeypatch,
        FakeGh(
            {
                ("actions", "SDK_TOKEN"): "2026-11-02T00:00:00Z",
                ("actions", "SONAR_TOKEN"): "2026-10-02T00:00:00Z",
            }
        ),
    )
    rc, _ = _check(tmp_path)
    assert rc == 2


def test_check_names_filter_and_unknown_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    gh = _install(monkeypatch, FakeGh({("dependabot", "SDK_TOKEN"): "2026-11-02T00:00:00Z"}))
    rc, data = _check(tmp_path, "SDK_TOKEN", app="dependabot")
    assert rc == 0
    assert [r["name"] for r in data["rows"]] == ["SDK_TOKEN"]
    assert all("/dependabot/" in c["argv"][2] for c in gh.calls)
    assert sas.main(["--org", ORG, "--app", "dependabot", "--check", "SONAR_TOKEN"]) == 2
    assert sas.main(["--org", ORG, "--app", "actions", "--check", "NOPE"]) == 2


def test_check_unplanned_org_is_plan_error(
    monkeypatch: pytest.MonkeyPatch, vault: dict[str, str | int]
) -> None:
    _install(monkeypatch, FakeGh())
    assert sas.main(["--org", "Someone-Else", "--app", "actions", "--check"]) == 2


def test_app_requires_org_and_org_requires_app() -> None:
    with pytest.raises(SystemExit):
        sas.main(["--app", "actions"])
    with pytest.raises(SystemExit):
        sas.main(["--org", ORG])
    with pytest.raises(SystemExit):
        sas.main(["--check"])


def test_check_output_names_and_dates_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    vault: dict[str, str | int],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install(monkeypatch, FakeGh({("actions", "SDK_TOKEN"): "2026-10-01T00:00:00Z"}))
    _check(tmp_path)
    out = capsys.readouterr()
    assert "SDK_TOKEN" in out.out
    _assert_no_leak(out.out + out.err + (tmp_path / "drift.json").read_text(encoding="utf-8"))


def test_vault_metadata_requests_no_value(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(
        sas.cb,
        "_machine_profile",
        lambda: {
            "host": "https://app.infisical.com",
            "project_id": "p",
            "environment": "prod",
            "client_id": "i",
            "client_secret": "s",
        },
    )
    monkeypatch.setattr(sas.cb, "_ua_token", lambda _p: "tok")

    def req(host: str, method: str, path: str, token: str | None = None, **_k: Any):
        seen.update(host=host, method=method, path=path)
        return 200, {
            "secret": {
                "secretKey": "SONAR_TOKEN",
                "updatedAt": "2026-10-01T00:00:00Z",
                "secretValue": CANARIES["SONAR_TOKEN"],
            }
        }

    monkeypatch.setattr(sas, "infisical_req", req)
    meta = sas.vault_metadata("SONAR_TOKEN")
    assert meta == sas.VaultMeta(status=200, updated_at="2026-10-01T00:00:00Z")
    assert seen["method"] == "GET"
    assert seen["path"].startswith("/api/v4/secrets/SONAR_TOKEN?")
    assert "viewSecretValue=false" in seen["path"]
    _assert_no_leak(repr(meta))


def test_vault_metadata_without_identity_is_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sas.cb, "_machine_profile", lambda: None)
    assert sas.vault_metadata("SONAR_TOKEN").status == 0


# --- set ---------------------------------------------------------------------


def test_set_dependabot_passes_app_and_stdin_only(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = _install(monkeypatch, FakeGh())
    rc = sas.main(["--org", ORG, "--app", "dependabot"])
    assert rc == 0
    (call,) = gh.secret_sets()
    assert call["argv"] == [
        "gh",
        "secret",
        "set",
        "SDK_TOKEN",
        "--org",
        ORG,
        "--app",
        "dependabot",
        "--visibility",
        "private",
    ]
    assert call["input"] == CANARIES["GITHUB_TOKEN"]
    assert set(gh.probes()) == {
        "repos/Quantum-L9/Cognitive.Engine.Graphs/contents",
        "repos/Quantum-L9/Gate_SDK/contents",
    }
    for c in gh.calls:
        _assert_no_leak(" ".join(c["argv"]))
    out = capsys.readouterr()
    _assert_no_leak(out.out + out.err)


def test_set_actions_sets_both_planned_names(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    gh = _install(monkeypatch, FakeGh())
    assert sas.main(["--org", ORG, "--app", "actions"]) == 0
    by_name = {c["argv"][3]: c for c in gh.secret_sets()}
    assert set(by_name) == {"SDK_TOKEN", "SONAR_TOKEN"}
    assert by_name["SONAR_TOKEN"]["input"] == CANARIES["SONAR_TOKEN"]
    assert by_name["SONAR_TOKEN"]["argv"][-2:] == ["--visibility", "all"]


def test_set_selected_visibility_passes_repo_names(
    tmp_path: Path, fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    gh = _install(monkeypatch, FakeGh())
    plan = _org_plan(tmp_path, visibility="selected", repositories=["o/a", "o/b"])
    monkeypatch.setattr(sas, "DEFAULT_PLAN", plan)
    assert sas.main(["--org", "o", "--app", "actions"]) == 0
    (call,) = gh.secret_sets()
    assert call["argv"][-4:] == ["--visibility", "selected", "--repos", "a,b"]


def test_set_skipped_when_must_read_probe_fails(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = _install(monkeypatch, FakeGh(probe_ok=False))
    rc = sas.main(["--org", ORG, "--app", "dependabot"])
    assert rc == 1
    assert gh.secret_sets() == []
    assert "SKIP SDK_TOKEN" in capsys.readouterr().out


def test_set_dry_run_writes_nothing(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    gh = _install(monkeypatch, FakeGh())
    assert sas.main(["--org", ORG, "--app", "actions", "--dry-run"]) == 0
    assert gh.secret_sets() == []


def test_org_mode_leaves_repo_targets_alone(
    fake_bind: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    gh = _install(monkeypatch, FakeGh())
    sas.main(["--org", ORG, "--app", "actions"])
    assert all("--repo" not in c["argv"] for c in gh.secret_sets())


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-15T10:00:00Z", "2026-11-15T10:00:00+00:00"),
        (None, "-"),
        ("not-a-timestamp ghp_examplevalue", "<unparseable>"),
    ],
)
def test_drift_log_prints_only_re_rendered_timestamps(value: str | None, expected: str) -> None:
    assert sas._stamp(value) == expected


@pytest.mark.parametrize(
    "argv",
    [
        ["--org", "-oops", "--app", "actions", "--check"],
        ["--org", "Quantum-L9/../x", "--app", "actions", "--check"],
        ["--org", "Quantum-L9", "--app", "actions", "--check", "--repo=evil"],
        ["--org", "Quantum-L9", "--app", "actions", "--check", "GITHUB_TOKEN"],
        ["--org", "Quantum-L9", "--app", "actions", "--check", "BAD NAME"],
        ["--plan", "/etc/passwd"],
    ],
)
def test_cli_rejects_values_that_could_reach_gh_or_the_filesystem(argv: list[str]) -> None:
    """S8705/S8707: org, names and plan paths never flow from the CLI unchecked."""
    with pytest.raises(SystemExit) as exc:
        sas.main(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda: sas.org_secret_updated_at("-oops", "actions", "SONAR_TOKEN"), "organization"),
        (lambda: sas.org_secret_updated_at("o/../x", "actions", "SONAR_TOKEN"), "organization"),
        (lambda: sas.org_secret_updated_at(ORG, "../actions", "SONAR_TOKEN"), "app"),
        (lambda: sas.org_secret_updated_at(ORG, "actions", "../SONAR_TOKEN"), "secret name"),
        (lambda: sas.org_secret_updated_at(ORG, "actions", "GITHUB_TOKEN"), "secret name"),
        (lambda: sas.org_secret_updated_at(ORG, "actions", "X\n"), "secret name"),
    ],
)
def test_metadata_sink_revalidates_every_gh_argument(
    monkeypatch: pytest.MonkeyPatch, call: Any, match: str
) -> None:
    """S8705: the ``gh api`` sink re-validates; parse-time checks are not the only guard."""
    gh = _install(monkeypatch, FakeGh())
    with pytest.raises(ValueError, match=match):
        call()
    assert gh.calls == []


def _target(**override: Any) -> sas.OrgSecret:
    fields: dict[str, Any] = {
        "org": ORG,
        "target_name": "SONAR_TOKEN",
        "vault_name": "SONAR_TOKEN",
        "apps": ("actions",),
        "visibility": "all",
    }
    fields.update(override)
    return sas.OrgSecret(**fields)


@pytest.mark.parametrize(
    ("target", "app", "match"),
    [
        (_target(org="--repo"), "actions", "organization"),
        (_target(target_name="--body"), "actions", "secret name"),
        (_target(), "--env", "app"),
        (_target(visibility="public"), "actions", "visibility"),
        (
            _target(visibility="selected", repositories=("o/--x", "o/a/b")),
            "actions",
            "repository",
        ),
    ],
)
def test_set_sink_revalidates_every_gh_argument(
    monkeypatch: pytest.MonkeyPatch, target: sas.OrgSecret, app: str, match: str
) -> None:
    """S8705: ``gh secret set`` argv holds only constants or sink-validated values."""
    gh = _install(monkeypatch, FakeGh())
    with pytest.raises(ValueError, match=match):
        sas.set_org_secret(target, app, CANARIES["SONAR_TOKEN"])
    assert gh.calls == []


def test_set_sink_passes_module_constant_for_app(monkeypatch: pytest.MonkeyPatch) -> None:
    gh = _install(monkeypatch, FakeGh())
    app = "".join(["depend", "abot"])  # equal to, but not, the module constant
    assert sas.set_org_secret(_target(apps=("dependabot",)), app, "v")
    (call,) = gh.secret_sets()
    passed = call["argv"][call["argv"].index("--app") + 1]
    assert passed == "dependabot"
    assert passed is sas.ORG_APPS[1]
