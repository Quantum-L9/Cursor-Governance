#!/usr/bin/env python3
"""Derive the hosted Memory operator grants from the L9 repository registry (operator step).

Every operator-bound OAuth subject of the hosted ``MemoryService`` (the keys of
``L9_MEMORY_OAUTH_ACTORS_JSON`` in Infisical project ``l9-graphite-memory``,
``prod``, ``/``) is granted read and write on ``@l9-repositories`` — the
derived token l9-graphiti-memory expands from the ``Quantum-L9/.github``
repository registry projection (ADR-107). No namespace list is typed here:
admitting a repository to the org registry reaches the subject once the
projection is re-released. ``promote_namespaces`` and ``roles`` are kept.

A DRY RUN unless ``--apply`` is given. Idempotent. Output is namespace names,
counts, HTTP statuses and the last six characters of a subject — never a
secret value, token or whole grant document.

Ordering guard (fail closed). A release older than ADR-107 accepts the token,
matches it literally against no namespace and silently denies the subject
every repository (l9-graphiti-memory RUNBOOK, "Hosted Memory on C1"). So
``--apply`` writes only when one of these holds:

* the live service's public ``/healthz`` reports ``package_version`` at least
  :data:`MIN_DERIVED_RELEASE` (a redeploy then picks the grant up); or
* ``--ahead-of-release`` is given and the deployment profile on
  ``Quantum-L9/l9-graphiti-memory@main`` admits only release tags at least
  :data:`MIN_DERIVED_RELEASE`, so the next deploy cannot be an older release.

An existing grant entry that is neither a registry repository id nor a known
legacy namespace of one is an *extra*. Extras are never dropped silently:
``--apply`` stops until ``--keep-extra`` (append them after the token) or
``--drop-extra`` names the decision.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO / "ops" / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from provision_memory_hook_principal import (  # noqa: E402
    ENVIRONMENT,
    EXIT_FAILED,
    EXIT_FORBIDDEN,
    EXIT_OK,
    SECRET_PATH,
    Infisical,
    Stop,
    infisical_as_this_identity,
    load_targets,
)

GRANTS_NAME = "L9_MEMORY_OAUTH_GRANTS_JSON"
ACTORS_NAME = "L9_MEMORY_OAUTH_ACTORS_JSON"
TOKEN = "@l9-repositories"
DERIVED_FIELDS = ("read_namespaces", "write_namespaces")
#: First release carrying ADR-107 (derived token) and ADR-108 (hook principal).
MIN_DERIVED_RELEASE = (3, 1, 0)
MEMORY_REPO = "Quantum-L9/l9-graphiti-memory"
PROFILE_PATH = ".l9/deployment.yaml"
REGISTRY = Path("semantics/repository_registry.yaml")
GROUP_REGISTRY = REPO / "ops" / "graphiti" / "group_registry.yaml"
DEFAULT_AUTHORITY = Path.home() / ".l9" / "authority" / ".github"

#: ``() -> package_version string or None``
VersionProbe = Callable[[], str | None]
#: ``() -> admitted source refs of the deployment profile on main``
ProfileProbe = Callable[[], list[str]]


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None  # type: ignore[return-value]


def suffix(subject: str) -> str:
    return f"…{subject[-6:]}"


def registry_namespaces(authority: Path, group_registry: Path = GROUP_REGISTRY) -> frozenset[str]:
    """Registry ids plus the legacy namespaces this repository records for them.

    Only the org registry decides membership; ``group_registry.yaml`` is read
    for ``legacy_namespaces`` of entries the registry already names, nothing else.
    """
    import yaml  # noqa: PLC0415

    path = authority / REGISTRY
    try:
        registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise Stop(
            f"authority registry unreadable at {path}: {type(exc).__name__}", EXIT_FAILED
        ) from exc
    ids = {str(entry["id"]) for entry in registry.get("repositories") or [] if entry.get("id")}
    if not ids:
        raise Stop(
            "authority registry names no repository; refusing to derive from nothing", EXIT_FAILED
        )
    legacy: set[str] = set()
    repos = (yaml.safe_load(group_registry.read_text(encoding="utf-8")) or {}).get("repos") or {}
    for repo_id, entry in repos.items():
        if repo_id in ids and isinstance(entry, Mapping):
            legacy.update(str(name) for name in entry.get("legacy_namespaces") or [])
    return frozenset(ids | legacy)


def derive(
    current: Iterable[str], covered: frozenset[str], keep_extra: bool
) -> tuple[list[str], list[str]]:
    """``(desired, extras)`` for one grant field."""

    extras = [ns for ns in current if ns != TOKEN and ns not in covered]
    return [TOKEN, *(extras if keep_extra else [])], extras


@dataclass
class Provisioner:
    project: str
    infisical: Infisical
    covered: frozenset[str]
    live_version: VersionProbe
    profile_refs: ProfileProbe
    apply: bool
    ahead_of_release: bool = False
    keep_extra: bool = False
    drop_extra: bool = False
    log: Callable[[str], None] = print
    changes: list[str] = field(default_factory=list)

    def read(self, name: str) -> dict[str, Any]:
        query = urllib.parse.urlencode(
            {
                "workspaceId": self.project,
                "environment": ENVIRONMENT,
                "secretPath": SECRET_PATH,
                "viewSecretValue": "true",
                "include_imports": "false",
            }
        )
        status, body = self.infisical("GET", f"/api/v3/secrets/raw/{name}?{query}", None)
        if status == 403:
            raise Stop(
                f"Infisical 403 reading {name} in l9-graphite-memory/{ENVIRONMENT}", EXIT_FORBIDDEN
            )
        secret = body.get("secret") if status == 200 and isinstance(body, dict) else None
        value = secret.get("secretValue") if isinstance(secret, dict) else None
        if not value:
            raise Stop(
                f"l9-graphite-memory/{ENVIRONMENT} {name} is absent (HTTP {status})", EXIT_FAILED
            )
        try:
            parsed = json.loads(value)
        except ValueError as exc:
            raise Stop(f"{name} is not JSON; not rewritten", EXIT_FAILED) from exc
        if not isinstance(parsed, dict):
            raise Stop(f"{name} is not a JSON object; not rewritten", EXIT_FAILED)
        return parsed

    def release_guard(self) -> None:
        version = self.live_version()
        live = parse_version(version)
        if live is not None and live >= MIN_DERIVED_RELEASE:
            self.log(f"live service package_version {version}: carries {TOKEN}")
            return
        floor = ".".join(map(str, MIN_DERIVED_RELEASE))
        if not self.ahead_of_release:
            raise Stop(
                f"live service package_version {version or 'UNKNOWN'} predates {floor}; "
                f"it would read "
                f"{TOKEN} literally and deny every repository. Deploy v{floor} first, or pass "
                "--ahead-of-release once the deployment profile admits only it"
            )
        refs = self.profile_refs()
        versions = [parse_version(ref.rsplit("/", 1)[-1]) for ref in refs]
        if not refs or any(v is None or v < MIN_DERIVED_RELEASE for v in versions):
            raise Stop(
                f"--ahead-of-release: {MEMORY_REPO}@main {PROFILE_PATH} "
                f"admits {refs or 'nothing'}; "
                f"every admitted ref must be v{floor} or later"
            )
        self.log(f"ahead of release: live {version or 'UNKNOWN'}, profile admits only {refs}")

    def run(self) -> int:
        mode = "APPLY" if self.apply else "DRY RUN (no change; --apply to write)"
        self.log(f"derive operator grants: {mode}")
        self.log(f"org registry namespaces (incl. legacy): {len(self.covered)}")
        subjects = sorted(self.read(ACTORS_NAME))
        if not subjects:
            raise Stop(f"{ACTORS_NAME} binds no operator subject; nothing to derive", EXIT_FAILED)
        grants = self.read(GRANTS_NAME)
        desired = dict(grants)
        all_extras: list[str] = []
        for subject in subjects:
            grant = dict(grants.get(subject) or {})
            for name in DERIVED_FIELDS:
                current = [str(ns) for ns in grant.get(name) or []]
                new, extras = derive(current, self.covered, self.keep_extra)
                all_extras.extend(f"{suffix(subject)} {name}: {ns}" for ns in extras)
                if current != new:
                    self.changes.append(f"{suffix(subject)} {name}")
                    self.log(f"{suffix(subject)} {name}: {len(current)} typed -> {new}")
                else:
                    self.log(f"{suffix(subject)} {name}: already {new}")
                grant[name] = new
            grant.setdefault("promote_namespaces", [])
            grant.setdefault("roles", [])
            desired[subject] = grant
        for extra in all_extras:
            self.log(f"extra (not an org registry namespace): {extra}")
        if not self.changes:
            self.log("done: nothing to change (already derived)")
            return EXIT_OK
        if not self.apply:
            self.log(f"done: would change {', '.join(self.changes)}")
            return EXIT_OK
        if all_extras and not (self.keep_extra or self.drop_extra):
            raise Stop("extras present: pass --keep-extra or --drop-extra")
        self.release_guard()
        status, body = self.infisical(
            "PATCH",
            f"/api/v4/secrets/{urllib.parse.quote(GRANTS_NAME, safe='')}",
            {
                "projectId": self.project,
                "environment": ENVIRONMENT,
                "secretPath": SECRET_PATH,
                "secretValue": json.dumps(desired, separators=(",", ":"), sort_keys=True),
            },
        )
        if status == 403:
            raise Stop(f"Infisical 403 writing {GRANTS_NAME}", EXIT_FORBIDDEN)
        if status == 200 and isinstance(body, dict) and "approval" in body:
            raise Stop(f"{GRANTS_NAME}: a secret approval was requested; not written yet")
        if status not in {200, 201}:
            raise Stop(f"Infisical refused {GRANTS_NAME} (HTTP {status})", EXIT_FAILED)
        where = f"l9-graphite-memory/{ENVIRONMENT}{SECRET_PATH}"
        self.log(f"infisical {where} {GRANTS_NAME}: updated HTTP {status}")
        self.log("done: applied — a redeploy of the memory service loads it")
        return EXIT_OK


# --- real probes ---------------------------------------------------------------


def healthz_url(resource: str) -> str:
    """The service's public ``/healthz`` on the origin of the Memory resource URL.

    The resource comes from ``ops/config/memory-auth0-onboarding.yaml`` (the
    hook provisioner's audience), so no service host is written in code.
    """

    parsed = urllib.parse.urlparse(resource)
    if parsed.scheme != "https" or not parsed.hostname:
        raise Stop(f"onboarding resource is not an https URL: {resource!r}", EXIT_FAILED)
    return f"https://{parsed.netloc}/healthz"


def live_package_version(resource: str) -> str | None:
    import safe_https  # noqa: PLC0415 - ops/lib is not a package

    url = healthz_url(resource)
    host = urllib.parse.urlparse(url).hostname or ""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        response = safe_https.https_exchange(
            request, timeout=15.0, allowed_hosts=frozenset({host}), label="memory-healthz"
        )
        payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None
    return str(payload.get("package_version") or "") or None


def profile_source_refs() -> list[str]:
    import subprocess  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    result = subprocess.run(  # noqa: S603 - fixed argv, gh REST read only
        [
            "gh",
            "api",
            f"repos/{MEMORY_REPO}/contents/{PROFILE_PATH}?ref=main",  # noqa: S607
            "-H",
            "Accept: application/vnd.github.raw",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise Stop(f"cannot read {MEMORY_REPO}@main {PROFILE_PATH}", EXIT_FAILED)
    profile = yaml.safe_load(result.stdout) or {}
    refs: list[str] = []
    for target in (profile.get("targets") or {}).values():
        refs.extend(str(ref) for ref in (target or {}).get("allowed_source_refs") or [])
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply", action="store_true", help="write the derived grants (default: dry run)"
    )
    parser.add_argument(
        "--ahead-of-release",
        action="store_true",
        help="allow --apply before the live service carries the token (see guard)",
    )
    extra = parser.add_mutually_exclusive_group()
    extra.add_argument(
        "--keep-extra", action="store_true", help="append non-registry entries after the token"
    )
    extra.add_argument("--drop-extra", action="store_true", help="drop non-registry entries")
    parser.add_argument(
        "--authority",
        type=Path,
        default=DEFAULT_AUTHORITY,
        help="Quantum-L9/.github checkout (default: the SessionStart authority checkout)",
    )
    args = parser.parse_args(argv)
    try:
        targets = load_targets()
        return Provisioner(
            project=targets.memory_project,
            infisical=infisical_as_this_identity(),
            covered=registry_namespaces(args.authority),
            live_version=lambda: live_package_version(targets.audience),
            profile_refs=profile_source_refs,
            apply=args.apply,
            ahead_of_release=args.ahead_of_release,
            keep_extra=args.keep_extra,
            drop_extra=args.drop_extra,
        ).run()
    except Stop as stop:
        print(f"STOP: {stop}", file=sys.stderr)
        return stop.code


if __name__ == "__main__":
    raise SystemExit(main())
