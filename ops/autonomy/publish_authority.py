#!/usr/bin/env python3
"""Per-repository publish route (``ops/config/publish-authority.json``).

``make pr`` / ``l9 pr`` is the publish verb on every surface. For almost every
repository the governance Makefile runs its own gate and opens the PR against
``origin/main``. A repository that *owns* a publication ceremony (today
``github.com/cryptoxdog/ib-odoo_19``, whose ``make pr`` refuses any base but ``Staging``)
is declared here, Governance-side, and the governance ``pr`` target delegates to
that native target exactly once. The registry is the only place such a route can
be declared: no consumer marker, no environment override (ORG L9-ORG-006 forbids
a consumer-granted exemption). CANONICAL_LAW §13 is the legal basis.

Stdlib only: ``ops/make/publish.mk`` calls this at Make parse time.

Exit codes (run-time use with ``--expect``):
  0  resolved route matches ``--expect`` (or no expectation)
  2  PUBLISH_ROUTE_DRIFT / PUBLISH_BASE_MISMATCH
  3  PUBLISH_REGISTRY_INVALID (unreadable or malformed registry)

``--format make`` never fails: it prints one ``route=…`` line and exits 0 so a
parse-time failure can only ever fall back to the governance branch, which then
re-verifies with ``--expect governance`` and stops on drift.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

GOV_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = GOV_ROOT / "ops" / "config" / "publish-authority.json"
SCHEMA = "l9.publish-authority.v1"
ROUTES = ("governance", "native")

EXIT_OK = 0
EXIT_DRIFT = 2
EXIT_REGISTRY = 3

ROUTE_DRIFT = "PUBLISH_ROUTE_DRIFT"
BASE_MISMATCH = "PUBLISH_BASE_MISMATCH"
REGISTRY_INVALID = "PUBLISH_REGISTRY_INVALID"


def normalize_origin(url: str | None) -> str | None:
    """``host/owner/name`` (lowercase) for any spelling of one remote, else None.

    One repository is spelled several ways: ``git@host:owner/name.git``,
    ``https://host/owner/name``, ``ssh://git@host/owner/name``,
    ``git://host/owner/name``. This is the single normalizer;
    ``ops/autonomy/local_execution_gate._origin_identity`` delegates here.
    """
    if not url:
        return None
    text = url.strip()
    scheme = False
    for prefix in ("ssh://", "git://", "https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            scheme = True
            break
    if scheme:
        # URL form: authority is everything before the first "/"; drop the
        # userinfo and an optional ":port" (ssh://git@github.com:22/o/n).
        authority, _, path = text.partition("/")
        authority = authority.rsplit("@", 1)[-1]
        host, _, port = authority.partition(":")
        if port and not port.isdigit():
            return None
        text = f"{host}/{path}"
    else:
        # scp form: git@github.com:owner/name — the colon separates host and path.
        text = text.rsplit("@", 1)[-1].replace(":", "/", 1)
    if text.endswith(".git"):
        text = text[: -len(".git")]
    return text.strip("/").lower() or None


def origin_of(workspace: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(workspace), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return normalize_origin(out.stdout)


class RegistryError(ValueError):
    """The registry file is unreadable or does not match the schema."""


@dataclass(frozen=True)
class Decision:
    route: str
    origin: str | None
    native_target: str | None = None
    native_check_target: str | None = None
    declared_base: str | None = None
    reason: str = ""
    registry_error: str | None = None
    ceremony: dict | None = None

    def make_line(self) -> str:
        if self.route != "native":
            return "route=governance"
        parts = [
            "route=native",
            f"target={self.native_target}",
            f"check_target={self.native_check_target or ''}",
            f"base={self.declared_base}",
            f"origin={self.origin}",
        ]
        return " ".join(parts)


def load_registry(path: Path) -> dict:
    # A missing registry is not an empty policy: the run-time check must surface
    # it as PUBLISH_REGISTRY_INVALID, or an Odoo workspace that should route
    # native would pass `--expect governance` on a clone that lost the file.
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"{path}: registry missing") from exc
    except (OSError, ValueError) as exc:
        raise RegistryError(f"{path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise RegistryError(f"{path}: schema must be {SCHEMA!r}")
    if document.get("default_route", "governance") != "governance":
        raise RegistryError(f"{path}: default_route must be 'governance'")
    repos = document.get("repositories", {})
    if not isinstance(repos, dict):
        raise RegistryError(f"{path}: repositories must be an object")
    for key, entry in repos.items():
        if key != key.lower() or key.count("/") != 2:
            raise RegistryError(f"{path}: key {key!r} must be lowercase host/owner/name")
        if not isinstance(entry, dict) or entry.get("route") not in ROUTES:
            raise RegistryError(f"{path}: {key}: route must be one of {ROUTES}")
        if entry["route"] == "native":
            for field in ("native_target", "declared_base", "authority"):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    raise RegistryError(f"{path}: {key}: native route requires {field!r}")
            ceremony = entry.get("ceremony")
            if not isinstance(ceremony, dict):
                raise RegistryError(f"{path}: {key}: native route requires 'ceremony'")
            kernel = ceremony.get("kernel")
            if not isinstance(kernel, str) or not kernel.strip() or kernel.startswith("/"):
                raise RegistryError(f"{path}: {key}: ceremony.kernel must be a relative path")
            requires = ceremony.get("kernel_requires")
            if (
                not isinstance(requires, list)
                or not requires
                or not all(isinstance(s, str) and s.strip() for s in requires)
            ):
                raise RegistryError(
                    f"{path}: {key}: ceremony.kernel_requires must list the kernel's guards"
                )
    return document


CEREMONY_UNVERIFIED = "PUBLISH_CEREMONY_UNVERIFIED"


def _recipe_of(workspace: Path, target: str) -> str | None:
    """The recipe lines Make would run for *target* in *workspace*, or None if undeclared."""
    try:
        out = subprocess.run(
            ["make", "-C", str(workspace), "--no-print-directory", "-rRpn", "help"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.stdout.splitlines()
    for index, line in enumerate(lines):
        if line == f"{target}:" or line.startswith(f"{target}: "):
            recipe: list[str] = []
            for follow in lines[index + 1 :]:
                if follow.startswith("\t"):
                    recipe.append(follow)
                elif follow.startswith("#"):
                    continue
                else:
                    break
            return "\n".join(recipe)
    return None


def verify_ceremony(workspace: Path, decision: Decision) -> list[str]:
    """Why *workspace* does not run the ceremony the registry declares, if it does not.

    The origin URL is consumer-editable, so it is never the only basis for the
    native route. The registry also pins the publication kernel the consumer
    must own and the guards that kernel must carry; the declared target's recipe
    must invoke that kernel. A workspace that merely spells the right origin
    does not reach the consumer's `pr` target, and a target that does not run
    the approved kernel is not the approved ceremony.
    """
    if decision.route != "native" or not decision.ceremony:
        return ["no native ceremony declared"]
    problems: list[str] = []
    kernel = workspace / decision.ceremony["kernel"]
    try:
        body = kernel.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"publication kernel {decision.ceremony['kernel']} unreadable: {exc}"]
    for guard in decision.ceremony["kernel_requires"]:
        if guard not in body:
            problems.append(f"kernel {decision.ceremony['kernel']} lacks guard {guard!r}")
    recipe = _recipe_of(workspace, str(decision.native_target))
    if recipe is None:
        problems.append(f"Makefile declares no {decision.native_target!r} target")
    elif decision.ceremony["kernel"] not in recipe:
        problems.append(
            f"{decision.native_target!r} recipe does not invoke {decision.ceremony['kernel']}"
        )
    return problems


def resolve(workspace: Path, registry: Path = DEFAULT_REGISTRY) -> Decision:
    origin = origin_of(workspace)
    try:
        document = load_registry(registry)
    except RegistryError as exc:
        # Fail closed toward the governance branch; the run-time check with
        # --expect surfaces the error as PUBLISH_REGISTRY_INVALID.
        return Decision(route="governance", origin=origin, reason=str(exc), registry_error=str(exc))
    if origin is None:
        return Decision(route="governance", origin=None, reason="no origin remote")
    entry = document["repositories"].get(origin)
    if not entry or entry.get("route") != "native":
        return Decision(route="governance", origin=origin, reason="origin not declared native")
    return Decision(
        route="native",
        origin=origin,
        native_target=entry["native_target"],
        native_check_target=entry.get("native_check_target") or None,
        declared_base=entry["declared_base"],
        reason=entry.get("reason", ""),
        ceremony=entry["ceremony"],
    )


def _strip_remote(ref: str) -> str:
    ref = ref.strip()
    return ref[len("origin/") :] if ref.startswith("origin/") else ref


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True, help="the WS being published")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--pr-base", default="", help="an explicitly requested PR_BASE")
    parser.add_argument("--expect", choices=ROUTES, help="fail with exit 2 when the route differs")
    parser.add_argument("--format", choices=("make", "json"), default="make")
    parser.add_argument(
        "--verify-ceremony",
        action="store_true",
        help="json mode: also prove the workspace runs the declared native ceremony (exit 2)",
    )
    args = parser.parse_args(argv)

    decision = resolve(Path(args.workspace).expanduser(), args.registry)

    if args.format == "make":
        # Parse-time contract: one line, exit 0, never raise.
        print(decision.make_line())
        return EXIT_OK

    payload = asdict(decision)
    if decision.registry_error and args.expect is not None:
        payload["verdict"] = REGISTRY_INVALID
        print(json.dumps(payload))
        print(f"{REGISTRY_INVALID}: {decision.registry_error}", file=sys.stderr)
        return EXIT_REGISTRY
    if args.expect is not None and decision.route != args.expect:
        payload["verdict"] = ROUTE_DRIFT
        print(json.dumps(payload))
        print(
            f"{ROUTE_DRIFT}: {args.workspace} resolves to route={decision.route}"
            f" (origin={decision.origin}); expected {args.expect}",
            file=sys.stderr,
        )
        return EXIT_DRIFT
    if decision.route == "native" and args.pr_base.strip():
        requested = _strip_remote(args.pr_base)
        if requested != decision.declared_base:
            payload["verdict"] = BASE_MISMATCH
            print(json.dumps(payload))
            print(
                f"{BASE_MISMATCH}: {decision.origin} declares base {decision.declared_base!r};"
                f" PR_BASE={args.pr_base!r} is refused",
                file=sys.stderr,
            )
            return EXIT_DRIFT
    if decision.route == "native" and args.verify_ceremony:
        problems = verify_ceremony(Path(args.workspace).expanduser(), decision)
        if problems:
            payload["verdict"] = CEREMONY_UNVERIFIED
            payload["problems"] = problems
            print(json.dumps(payload))
            print(
                f"{CEREMONY_UNVERIFIED}: {args.workspace} spells origin {decision.origin} but does"
                f" not run its declared publication ceremony: {'; '.join(problems)}",
                file=sys.stderr,
            )
            return EXIT_DRIFT
    payload["verdict"] = "OK"
    print(json.dumps(payload))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
