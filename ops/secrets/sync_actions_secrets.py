#!/usr/bin/env python3
"""Mirror Infisical (cursor-governance) secrets into GitHub repo and org secrets.

OPERATOR-ONLY. Hosted agent sessions cannot write Actions secrets (the session
proxy returns 403 on ``repos/*/actions/secrets*``); run this on a machine whose
``gh`` may write repository secrets.

The plan is data: ``actions-secret-sync.json`` beside this file, a list of
``{repo, secret, vault_name}`` plus an optional ``sdk_token`` block. Every
``vault_name`` must be in ``root_env_keys`` of
``infisical-cursor-governance.yaml``; the plan fails to load otherwise.

Value handling:

* Values are bound in-process through ``capability_bind`` (Infisical, as this
  surface's machine identity). They are never exported, printed or written.
* A value reaches ``gh secret set NAME --repo R`` on stdin only, never argv.
* ``gh secret set`` output is never printed; a failure reports its exit code.
* ``--dry-run`` binds and writes nothing.
* ``SDK_TOKEN`` is opt-in (``--with-sdk-token``). It is the Infisical
  ``GITHUB_TOKEN`` (never the shell's ``GH_TOKEN`` / ``GITHUB_TOKEN``) and is set
  only after that PAT proves it can read ``must_read``.

Exit codes: 0 every planned set succeeded (or would, under ``--dry-run``);
1 any skip or failure; 2 the plan did not load.

Org targets (#892) and drift check (#870) — frozen interface consumed by the
Quantum-L9/.github secret-drift workflow::

    sync_actions_secrets.py --org ORG --app {actions,dependabot}
        [--check] [--report-json PATH] [NAME ...]

The plan's ``org_secrets`` list declares which names are org-scoped, from which
vault name, for which apps, with which visibility (``all`` | ``private`` |
``selected`` + ``repositories``) and which repositories a PAT must read first
(``must_read``). Without ``--check`` each planned name for ``ORG``/``APP`` is set
with ``gh secret set NAME --org ORG --app APP --visibility V [--repos ...]``,
value on stdin only, after every ``must_read`` probe passes.

``--check`` writes nothing and reads no value: per planned name it compares the
org secret's ``updated_at`` (GitHub REST metadata) with the Infisical secret's
``updatedAt`` (read with ``viewSecretValue=false``). Verdicts: ``in_sync``,
``drift`` (org older than vault), ``missing_in_org``, ``missing_in_vault``.
Exit 0 all in sync; 1 any drift or missing; 2 plan or transport error (an
org-secrets read other than 404, including 403, or an Infisical read that is
neither 200 nor 404). On exit 2 no report is written and a report already at
``--report-json`` is removed, so a partial evaluation can never be read as
complete. ``--report-json`` schema ``l9.secret-drift.v1``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import capability_bind as cb  # noqa: E402
from infisical_http import infisical_req  # noqa: E402

try:  # pragma: no cover - import guard mirrors capability_bind
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

SCHEMA = "l9.actions-secret-sync.v1"
DEFAULT_PLAN = HERE / "actions-secret-sync.json"
DEFAULT_INVENTORY = HERE / "infisical-cursor-governance.yaml"
SDK_TARGET_NAME = "SDK_TOKEN"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SECRET_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHELL_GH_VARS = ("GITHUB_TOKEN", "GH_TOKEN")
_ORG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
ORG_APPS = ("actions", "dependabot")
ORG_VISIBILITIES = ("all", "private", "selected")
DRIFT_SCHEMA = "l9.secret-drift.v1"
_HTTP_STATUS_RE = re.compile(r"\(HTTP (\d{3})\)")


class PlanError(ValueError):
    """The plan file is malformed or names a vault key outside ``root_env_keys``."""


@dataclass(frozen=True)
class Entry:
    repo: str
    target_name: str  # JSON key "secret": the Actions secret's NAME, never a value
    vault_name: str


@dataclass(frozen=True)
class SdkToken:
    repos: tuple[str, ...]
    vault_name: str
    must_read: str


@dataclass(frozen=True)
class OrgSecret:
    org: str
    target_name: str  # JSON key "secret": the org secret's NAME, never a value
    vault_name: str
    apps: tuple[str, ...]
    visibility: str
    repositories: tuple[str, ...] = ()
    must_read: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    entries: tuple[Entry, ...]
    sdk_token: SdkToken | None = None
    vault_names: frozenset[str] = field(default_factory=frozenset)
    org_secrets: tuple[OrgSecret, ...] = ()


@dataclass(frozen=True)
class VaultMeta:
    """Infisical metadata for one name: HTTP status (0 = unreachable) and ``updatedAt``."""

    status: int
    updated_at: str | None


def root_env_keys(inventory: Path = DEFAULT_INVENTORY) -> frozenset[str]:
    if yaml is None:
        raise PlanError("PyYAML is required to read the Infisical inventory")
    raw = yaml.safe_load(inventory.read_text(encoding="utf-8")) or {}
    keys = raw.get("root_env_keys") if isinstance(raw, dict) else None
    if not isinstance(keys, list) or not keys:
        raise PlanError(f"{inventory}: root_env_keys missing or empty")
    return frozenset(str(k) for k in keys if k)


def _require_str(obj: dict, key: str, where: str, pattern: re.Pattern[str]) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not pattern.match(value):
        raise PlanError(f"{where}: {key!r} missing or malformed")
    return value


def _check_vault(name: str, allowed: frozenset[str], where: str) -> None:
    if name not in allowed:
        raise PlanError(
            f"{where}: vault_name {name!r} is not in root_env_keys of the Infisical inventory"
        )


def load_plan(path: Path = DEFAULT_PLAN, inventory: Path = DEFAULT_INVENTORY) -> Plan:
    allowed = root_env_keys(inventory)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanError(f"{path}: unreadable plan ({type(exc).__name__})") from exc
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise PlanError(f"{path}: schema must be {SCHEMA!r}")
    items = raw.get("secrets")
    if not isinstance(items, list):
        raise PlanError(f"{path}: 'secrets' must be a list")
    entries: list[Entry] = []
    seen: set[tuple[str, str]] = set()
    for i, item in enumerate(items):
        where = f"{path.name}: secrets[{i}]"
        if not isinstance(item, dict):
            raise PlanError(f"{where}: must be an object")
        entry = Entry(
            repo=_require_str(item, "repo", where, _REPO_RE),
            target_name=_require_str(item, "secret", where, _SECRET_RE),
            vault_name=_require_str(item, "vault_name", where, _SECRET_RE),
        )
        _check_vault(entry.vault_name, allowed, where)
        if (entry.repo, entry.target_name) in seen:
            raise PlanError(f"{where}: duplicate {entry.repo} {entry.target_name}")
        seen.add((entry.repo, entry.target_name))
        entries.append(entry)

    sdk: SdkToken | None = None
    block = raw.get("sdk_token")
    if block is not None:
        where = f"{path.name}: sdk_token"
        if not isinstance(block, dict):
            raise PlanError(f"{where}: must be an object")
        repos = block.get("repos")
        if not isinstance(repos, list) or not all(
            isinstance(r, str) and _REPO_RE.match(r) for r in repos
        ):
            raise PlanError(f"{where}: 'repos' must be a list of owner/name")
        vault_name = _require_str(block, "vault_name", where, _SECRET_RE)
        _check_vault(vault_name, allowed, where)
        for repo in repos:
            if (repo, SDK_TARGET_NAME) in seen:
                raise PlanError(f"{where}: {repo} {SDK_TARGET_NAME} also in 'secrets'")
        sdk = SdkToken(
            repos=tuple(repos),
            vault_name=vault_name,
            must_read=_require_str(block, "must_read", where, _REPO_RE),
        )
    org_secrets = _load_org_secrets(raw.get("org_secrets"), path, allowed)
    names = (
        {e.vault_name for e in entries}
        | ({sdk.vault_name} if sdk else set())
        | {t.vault_name for t in org_secrets}
    )
    return Plan(
        entries=tuple(entries),
        sdk_token=sdk,
        vault_names=frozenset(names),
        org_secrets=org_secrets,
    )


def _repo_list(item: dict, key: str, where: str) -> tuple[str, ...]:
    value = item.get(key, [])
    if not isinstance(value, list) or not all(
        isinstance(r, str) and _REPO_RE.match(r) for r in value
    ):
        raise PlanError(f"{where}: {key!r} must be a list of owner/name")
    if len(set(value)) != len(value):
        raise PlanError(f"{where}: {key!r} has duplicates")
    return tuple(value)


def _load_org_secrets(items: object, path: Path, allowed: frozenset[str]) -> tuple[OrgSecret, ...]:
    if items is None:
        return ()
    if not isinstance(items, list):
        raise PlanError(f"{path.name}: 'org_secrets' must be a list")
    targets: list[OrgSecret] = []
    seen: set[tuple[str, str, str]] = set()
    for i, item in enumerate(items):
        where = f"{path.name}: org_secrets[{i}]"
        if not isinstance(item, dict):
            raise PlanError(f"{where}: must be an object")
        org = _require_str(item, "org", where, _ORG_RE)
        target_name = _require_str(item, "secret", where, _SECRET_RE)
        vault_name = _require_str(item, "vault_name", where, _SECRET_RE)
        _check_vault(vault_name, allowed, where)
        apps = item.get("apps")
        if (
            not isinstance(apps, list)
            or not apps
            or not all(a in ORG_APPS for a in apps)
            or len(set(apps)) != len(apps)
        ):
            raise PlanError(f"{where}: 'apps' must be a non-empty unique subset of {ORG_APPS}")
        visibility = item.get("visibility")
        if visibility not in ORG_VISIBILITIES:
            raise PlanError(f"{where}: 'visibility' must be one of {ORG_VISIBILITIES}")
        repositories = _repo_list(item, "repositories", where)
        if visibility == "selected":
            if not repositories:
                raise PlanError(f"{where}: visibility 'selected' needs 'repositories'")
            if any(r.split("/", 1)[0].lower() != org.lower() for r in repositories):
                raise PlanError(f"{where}: 'repositories' must belong to org {org}")
        elif repositories:
            raise PlanError(f"{where}: 'repositories' is only valid with visibility 'selected'")
        must_read = _repo_list(item, "must_read", where)
        for app in apps:
            key = (org.lower(), app, target_name)
            if key in seen:
                raise PlanError(f"{where}: duplicate {org} {app} {target_name}")
            seen.add(key)
        targets.append(
            OrgSecret(
                org=org,
                target_name=target_name,
                vault_name=vault_name,
                apps=tuple(apps),
                visibility=visibility,
                repositories=repositories,
                must_read=must_read,
            )
        )
    return tuple(targets)


def org_targets(plan: Plan, org: str, app: str) -> list[OrgSecret]:
    """Planned org secrets for one org and app, in plan order."""
    return [t for t in plan.org_secrets if t.org.lower() == org.lower() and app in t.apps]


def vault_pat(vault_name: str) -> str | None:
    """Bind the vault PAT, never the shell's ``GH_TOKEN`` / ``GITHUB_TOKEN``."""
    env = {k: v for k, v in os.environ.items() if k not in _SHELL_GH_VARS}
    cb.reset_cache()
    return cb.bind(vault_name, env=env)


def pat_can_read(pat: str, repo: str) -> bool:
    """Probe with the PAT in the child's environment only (never argv)."""
    env = {k: v for k, v in os.environ.items() if k not in _SHELL_GH_VARS}
    env["GH_TOKEN"] = pat
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents", "--jq", "length"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def set_secret(repo: str, target_name: str, value: str) -> bool:
    """``gh secret set`` with the value on stdin only.

    ``gh`` output is never printed: only the exit code is reported, so no
    output can depend on a value.
    """
    result = subprocess.run(
        ["gh", "secret", "set", target_name, "--repo", repo],
        input=value,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"  FAIL {repo} {target_name}: gh secret set exited {result.returncode}")
        return False
    return True


def run(plan: Plan, *, dry_run: bool, with_sdk_token: bool) -> int:
    failures = 0
    for entry in plan.entries:
        value = cb.bind(entry.vault_name)
        if not value:
            source = cb._SOURCES.get(entry.vault_name, "unbound")
            target = f"{entry.repo} {entry.target_name}"
            print(f"  SKIP {target}: vault {entry.vault_name} unbound ({source})")
            failures += 1
            continue
        if dry_run:
            print(f"  would set {entry.repo} {entry.target_name} <- vault {entry.vault_name}")
        elif set_secret(entry.repo, entry.target_name, value):
            print(f"  set  {entry.repo} {entry.target_name} <- vault {entry.vault_name}")
        else:
            failures += 1

    if with_sdk_token:
        sdk = plan.sdk_token
        if sdk is None:
            print(f"  SKIP {SDK_TARGET_NAME}: plan has no sdk_token block")
            return 1
        pat = vault_pat(sdk.vault_name)
        if not pat:
            print(f"  SKIP {SDK_TARGET_NAME}: vault {sdk.vault_name} unbound")
            failures += 1
        elif not pat_can_read(pat, sdk.must_read):
            print(f"  SKIP {SDK_TARGET_NAME}: vault {sdk.vault_name} cannot read {sdk.must_read}")
            failures += 1
        else:
            for repo in sdk.repos:
                if dry_run:
                    print(f"  would set {repo} {SDK_TARGET_NAME} <- vault {sdk.vault_name}")
                elif set_secret(repo, SDK_TARGET_NAME, pat):
                    print(f"  set  {repo} {SDK_TARGET_NAME} <- vault {sdk.vault_name}")
                else:
                    failures += 1
    return 1 if failures else 0


def set_org_secret(target: OrgSecret, app: str, value: str) -> bool:
    """``gh secret set NAME --org ORG --app APP``; value on stdin only, output never printed."""
    argv = [
        "gh", "secret", "set", target.target_name,
        "--org", target.org, "--app", app, "--visibility", target.visibility,
    ]  # fmt: skip
    if target.visibility == "selected":
        argv += ["--repos", ",".join(r.split("/", 1)[1] for r in target.repositories)]
    result = subprocess.run(argv, input=value, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(
            f"  FAIL org {target.org} {app} {target.target_name}: "
            f"gh secret set exited {result.returncode}"
        )
        return False
    return True


def run_org(targets: list[OrgSecret], app: str, *, dry_run: bool) -> int:
    failures = 0
    for target in targets:
        label = f"org {target.org} {app} {target.target_name}"
        # vault_pat never binds the shell's GH_TOKEN / GITHUB_TOKEN.
        value = vault_pat(target.vault_name)
        if not value:
            print(f"  SKIP {target.target_name}: vault {target.vault_name} unbound ({label})")
            failures += 1
            continue
        unreadable = [r for r in target.must_read if not pat_can_read(value, r)]
        if unreadable:
            print(
                f"  SKIP {target.target_name}: vault {target.vault_name} cannot read "
                f"{', '.join(unreadable)} ({label})"
            )
            failures += 1
            continue
        if dry_run:
            print(f"  would set {label} ({target.visibility}) <- vault {target.vault_name}")
        elif set_org_secret(target, app, value):
            print(f"  set  {label} ({target.visibility}) <- vault {target.vault_name}")
        else:
            failures += 1
    return 1 if failures else 0


class TransportError(RuntimeError):
    """A metadata read that is neither a hit nor a definite 404."""


def org_secret_updated_at(org: str, app: str, name: str) -> str | None:
    """The org secret's ``updated_at``; None on 404. Metadata only, never a value."""
    result = subprocess.run(
        ["gh", "api", f"orgs/{org}/{app}/secrets/{name}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        match = _HTTP_STATUS_RE.search(result.stderr or "")
        status = match.group(1) if match else "unknown"
        if status == "404":
            return None
        raise TransportError(f"org {org} {app} {name}: metadata read failed (HTTP {status})")
    try:
        body = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise TransportError(f"org {org} {app} {name}: unreadable metadata") from exc
    updated = body.get("updated_at") if isinstance(body, dict) else None
    if not isinstance(body, dict) or body.get("name") != name or not isinstance(updated, str):
        raise TransportError(f"org {org} {app} {name}: metadata lacks name/updated_at")
    return updated


def vault_metadata(name: str) -> VaultMeta:
    """Infisical ``updatedAt`` for ``name`` at ``/``, requested with ``viewSecretValue=false``.

    Only ``secretKey`` and ``updatedAt`` are read from the response; the payload
    is dropped here and never logged. Status 0 means no identity or unreachable.
    """
    profile = cb._machine_profile()
    if profile is None:
        return VaultMeta(status=0, updated_at=None)
    token = cb._ua_token(profile)
    if not token:
        return VaultMeta(status=0, updated_at=None)
    query = urllib.parse.urlencode(
        {
            "projectId": profile["project_id"],
            "environment": profile["environment"],
            "secretPath": "/",
            "viewSecretValue": "false",
            "expandSecretReferences": "false",
            "includeImports": "false",
        }
    )
    status, payload = infisical_req(
        profile["host"],
        "GET",
        f"/api/v4/secrets/{urllib.parse.quote(name, safe='')}?{query}",
        token,
    )
    secret = payload.get("secret") if isinstance(payload, dict) else None
    if status != 200:
        return VaultMeta(status=status, updated_at=None)
    if not isinstance(secret, dict) or secret.get("secretKey") != name:
        return VaultMeta(status=0, updated_at=None)
    updated = secret.get("updatedAt")
    return VaultMeta(status=200, updated_at=updated if isinstance(updated, str) else None)


def _instant(stamp: str) -> datetime:
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without zone: {stamp!r}")
    return parsed


def _stamp(value: str | None) -> str:
    """A timestamp for the log, re-rendered from its parsed instant; never raw text."""
    if value is None:
        return "-"
    try:
        return _instant(value).isoformat()
    except ValueError:
        return "<unparseable>"


def check_org(targets: list[OrgSecret], org: str, app: str) -> list[dict[str, str | None]]:
    """One drift row per target. Raises TransportError when a row cannot be decided."""
    rows: list[dict[str, str | None]] = []
    for target in targets:
        org_at = org_secret_updated_at(org, app, target.target_name)
        meta = vault_metadata(target.vault_name)
        if meta.status not in (200, 404) or (meta.status == 200 and not meta.updated_at):
            raise TransportError(
                f"vault {target.vault_name}: metadata read failed (status {meta.status})"
            )
        vault_at = meta.updated_at if meta.status == 200 else None
        if vault_at is None:
            verdict = "missing_in_vault"
        elif org_at is None:
            verdict = "missing_in_org"
        else:
            try:
                stale = _instant(org_at) < _instant(vault_at)
            except ValueError as exc:
                raise TransportError(f"{target.target_name}: unparseable timestamp") from exc
            verdict = "drift" if stale else "in_sync"
        rows.append(
            {
                "name": target.target_name,
                "org_updated_at": org_at,
                "vault_updated_at": vault_at,
                "verdict": verdict,
            }
        )
    return rows


def _org_main(args: argparse.Namespace, plan: Plan) -> int:
    report: Path | None = args.report_json
    if report is not None and report.exists():
        report.unlink()  # never leave a previous run's verdict in place
    targets = org_targets(plan, args.org, args.app)
    if not targets:
        print(f"ERROR: plan declares no org secrets for {args.org} {args.app}", file=sys.stderr)
        return 2
    if args.names:
        planned = {t.target_name for t in targets}
        unknown = sorted(set(args.names) - planned)
        if unknown:
            print(
                f"ERROR: not planned for {args.org} {args.app}: {', '.join(unknown)}",
                file=sys.stderr,
            )
            return 2
        targets = [t for t in targets if t.target_name in set(args.names)]
    if not args.check:
        return run_org(targets, args.app, dry_run=args.dry_run)
    try:
        rows = check_org(targets, args.org, args.app)
    except TransportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for row in rows:
        # Only re-rendered timestamps reach the log: check_org reads Infisical
        # metadata with viewSecretValue=false, and printing a value parsed back
        # from a datetime keeps any other payload text out of the output.
        print(
            f"  {row['verdict']:<16} {row['name']} "
            f"org={_stamp(row['org_updated_at'])} vault={_stamp(row['vault_updated_at'])}"
        )
    if report is not None:
        document = {"schema": DRIFT_SCHEMA, "org": args.org, "app": args.app, "rows": rows}
        report.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r["verdict"] == "in_sync" for r in rows) else 1


#: GitHub's own naming rules: an org login, and an Actions/Dependabot secret name.
#: Validated at parse time so no CLI value that looks like an option or a path can
#: reach a ``gh`` argument list (SonarCloud pythonsecurity:S8705).
_ORG_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_SECRET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,254}$")


def _org_login(value: str) -> str:
    if not _ORG_LOGIN_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(f"not a GitHub organization login: {value!r}")
    return value


def _secret_name(value: str) -> str:
    if not _SECRET_NAME_RE.fullmatch(value) or value.upper().startswith("GITHUB_"):
        raise argparse.ArgumentTypeError(f"not a valid GitHub secret name: {value!r}")
    return value


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None,
        allow_abbrev=False,  # "--repo=x" must not silently become --report-json
    )
    ap.add_argument("--dry-run", action="store_true", help="bind and report; write nothing")
    ap.add_argument(
        "--with-sdk-token",
        action="store_true",
        help="also set SDK_TOKEN from the vault GITHUB_TOKEN after a read probe",
    )
    ap.add_argument(
        "--org", type=_org_login, help="org mode: set (or --check) the plan's org secrets for ORG"
    )
    ap.add_argument("--app", choices=ORG_APPS, help="org secret store (required with --org)")
    ap.add_argument(
        "--check",
        action="store_true",
        help="org mode: compare names and timestamps only; write nothing",
    )
    ap.add_argument("--report-json", type=Path, help="org --check: write l9.secret-drift.v1")
    ap.add_argument(
        "names", nargs="*", metavar="NAME", type=_secret_name, help="org mode: limit to these names"
    )
    args = ap.parse_args(argv)
    if bool(args.org) != bool(args.app):
        ap.error("--org and --app go together")
    if not args.org and (args.check or args.report_json or args.names):
        ap.error("--check, --report-json and NAME need --org/--app")
    if args.org and args.with_sdk_token:
        ap.error("--with-sdk-token is repo mode; org SDK_TOKEN comes from org_secrets")
    if args.check and args.dry_run:
        ap.error("--check already writes nothing")
    if args.report_json and not args.check:
        ap.error("--report-json needs --check")
    try:
        # The plan and inventory are this module's own files, never a CLI path
        # (SonarCloud pythonsecurity:S8707); tests patch the module defaults.
        plan = load_plan(DEFAULT_PLAN, DEFAULT_INVENTORY)
    except PlanError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.org:
        return _org_main(args, plan)
    return run(plan, dry_run=args.dry_run, with_sdk_token=args.with_sdk_token)


if __name__ == "__main__":
    sys.exit(main())
