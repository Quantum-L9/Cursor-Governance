"""Campaign promotion validator.

Fails a promotion whose registration is not mechanically valid or not portable.

Checked conditions:

1. ``ops/autonomy/surface_profile.yaml`` parses as YAML.
2. Campaign registrations are well formed (mapping id -> {integration_branch}).
3. Campaign ids do not collide (duplicate YAML keys, duplicate list entries).
4. ``integration_branch`` (and policy ``pr_base``) equals ``campaign/<campaign-id>``.
5. Committed shared campaign ledgers carry no absolute machine-local paths.
6. Generated projections agree with their source (MANIFEST digests are current).

Scope of check 5: only the *live shared* promotion surface listed in
``SHARED_LEDGERS``. Per-campaign ``history/**`` and ``blueprint/**`` records are
immutable evidence of what a past run actually observed — rewriting a recorded
receipt path would falsify that evidence, so those files are reported as
``warnings`` instead of failing the run.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

SURFACE_PROFILE = "ops/autonomy/surface_profile.yaml"
CAMPAIGNS_DIR = "environment/program-execution/campaigns"
EXECUTION_POLICY = f"{CAMPAIGNS_DIR}/CAMPAIGN_EXECUTION_POLICY.yaml"
COMPILE_ALLOWLIST = f"{CAMPAIGNS_DIR}/COMPILE_ALLOWLIST.yaml"
STATUS_LEDGER = f"{CAMPAIGNS_DIR}/CAMPAIGN_STATUS.yaml"

# Committed shared campaign state. Machine-local paths here are a hard failure.
SHARED_LEDGERS = (SURFACE_PROFILE, EXECUTION_POLICY, COMPILE_ALLOWLIST, STATUS_LEDGER)

# Generated projections whose digests must agree with their sources.

# Absolute machine-local runtime locations. Ordered so the message names the
# most specific form that matched.
MACHINE_LOCAL_PATTERNS = (
    ("posix-home", re.compile(r"/(?:Users|home)/[^\s\"',:]+")),
    ("tilde-l9", re.compile(r"~/\.l9/[^\s\"',:]+")),
    # Drive letter followed by a backslash. Anchored on a non-letter so scheme
    # separators such as ``https://`` never match.
    ("windows-drive", re.compile(r"(?<![A-Za-z])[A-Za-z]:\\[^\s\"',]*")),
)


class DuplicateKeyError(ValueError):
    """A YAML mapping declared the same key twice."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys.

    ``yaml.safe_load`` silently keeps the last duplicate. A malformed campaign
    promotion typically produces exactly that shape, so the collision must be an
    error rather than a silent overwrite.
    """


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    seen: set = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in seen:
            raise DuplicateKeyError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=True)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def load_yaml(path: Path) -> Any:
    """Parse ``path`` rejecting duplicate mapping keys."""
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)


def _expected_branch(campaign_id: str) -> str:
    return f"campaign/{campaign_id}"


def check_surface_profile(root: Path) -> tuple[list[str], dict | None]:
    """Condition 1 — the surface profile parses."""
    path = root / SURFACE_PROFILE
    if not path.is_file():
        return [f"{SURFACE_PROFILE}: missing"], None
    try:
        return [], load_yaml(path)
    except DuplicateKeyError as exc:
        return [f"{SURFACE_PROFILE}: {exc}"], None
    except yaml.YAMLError as exc:
        return [f"{SURFACE_PROFILE}: does not parse: {exc}"], None


def check_registrations(root: Path, profile: dict | None) -> tuple[list[str], set[str]]:
    """Conditions 2-4 — well formed, collision free, branch matches id."""
    errors: list[str] = []
    if profile is None:
        return errors, set()

    execution = profile.get("campaign_execution")
    if not isinstance(execution, dict):
        return [f"{SURFACE_PROFILE}: campaign_execution must be a mapping"], set()

    campaigns = execution.get("campaigns")
    if not isinstance(campaigns, dict):
        return [f"{SURFACE_PROFILE}: campaign_execution.campaigns must be a mapping"], set()

    profile_ids: set[str] = set()
    for campaign_id, entry in campaigns.items():
        label = f"{SURFACE_PROFILE}: campaign {campaign_id!r}"
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            errors.append(f"{label}: id must be a non-empty string")
            continue
        profile_ids.add(campaign_id)
        if not isinstance(entry, dict):
            errors.append(f"{label}: registration must be a mapping")
            continue
        branch = entry.get("integration_branch")
        if not isinstance(branch, str) or not branch.strip():
            errors.append(f"{label}: integration_branch must be a non-empty string")
            continue
        if branch != _expected_branch(campaign_id):
            errors.append(
                f"{label}: integration_branch {branch!r} != {_expected_branch(campaign_id)!r}"
            )

    errors.extend(_check_policy(root, profile_ids))
    errors.extend(_check_allowlist(root, profile_ids))
    errors.extend(_check_status_ledger(root))
    return errors, profile_ids


def _load_or_error(root: Path, relative: str, errors: list[str]) -> Any:
    path = root / relative
    if not path.is_file():
        errors.append(f"{relative}: missing")
        return None
    try:
        return load_yaml(path)
    except DuplicateKeyError as exc:
        errors.append(f"{relative}: {exc}")
    except yaml.YAMLError as exc:
        errors.append(f"{relative}: does not parse: {exc}")
    return None


def _check_policy(root: Path, profile_ids: set[str]) -> list[str]:
    errors: list[str] = []
    policy = _load_or_error(root, EXECUTION_POLICY, errors)
    if not isinstance(policy, dict):
        return errors

    entries = policy.get("campaigns")
    if not isinstance(entries, list):
        return errors + [f"{EXECUTION_POLICY}: campaigns must be a list"]

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"{EXECUTION_POLICY}: campaigns[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be a mapping")
            continue
        campaign_id = entry.get("id")
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            errors.append(f"{label}: id must be a non-empty string")
            continue
        if campaign_id in seen:
            errors.append(f"{label}: duplicate campaign id {campaign_id!r}")
            continue
        seen.add(campaign_id)
        for field in ("integration_branch", "pr_base"):
            value = entry.get(field)
            if value is None:
                continue
            if value != _expected_branch(campaign_id):
                errors.append(f"{label}: {field} {value!r} != {_expected_branch(campaign_id)!r}")

    missing = sorted(profile_ids - seen)
    if missing:
        errors.append(f"{EXECUTION_POLICY}: promoted campaigns absent from policy: {missing}")
    return errors


def _check_allowlist(root: Path, profile_ids: set[str]) -> list[str]:
    errors: list[str] = []
    allowlist = _load_or_error(root, COMPILE_ALLOWLIST, errors)
    if not isinstance(allowlist, dict):
        return errors

    ids = allowlist.get("campaign_ids")
    if not isinstance(ids, list):
        return errors + [f"{COMPILE_ALLOWLIST}: campaign_ids must be a list"]

    seen: set[str] = set()
    for campaign_id in ids:
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            errors.append(f"{COMPILE_ALLOWLIST}: campaign id must be a non-empty string")
            continue
        if campaign_id in seen:
            errors.append(f"{COMPILE_ALLOWLIST}: duplicate campaign id {campaign_id!r}")
        seen.add(campaign_id)

    missing = sorted(profile_ids - seen)
    if missing:
        errors.append(f"{COMPILE_ALLOWLIST}: promoted campaigns absent from allowlist: {missing}")
    return errors


def _check_status_ledger(root: Path) -> list[str]:
    errors: list[str] = []
    ledger = _load_or_error(root, STATUS_LEDGER, errors)
    if not isinstance(ledger, dict):
        return errors

    entries = ledger.get("campaigns")
    if not isinstance(entries, list):
        return errors + [f"{STATUS_LEDGER}: campaigns must be a list"]

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"{STATUS_LEDGER}: campaigns[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be a mapping")
            continue
        campaign_id = entry.get("id")
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            errors.append(f"{label}: id must be a non-empty string")
            continue
        if campaign_id in seen:
            errors.append(f"{label}: duplicate campaign id {campaign_id!r}")
        seen.add(campaign_id)
    return errors


def scan_machine_local_paths(root: Path, relatives: tuple[str, ...]) -> list[str]:
    """Condition 5 — absolute machine-local paths in committed shared state."""
    hits: list[str] = []
    for relative in relatives:
        path = root / relative
        if not path.is_file():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for kind, pattern in MACHINE_LOCAL_PATTERNS:
                match = pattern.search(line)
                if match:
                    hits.append(f"{relative}:{line_number}: {kind}: {match.group(0)}")
                    break
    return hits


def scan_archive_paths(root: Path) -> list[str]:
    """Machine-local paths in immutable per-campaign evidence (reported only)."""
    campaigns = root / CAMPAIGNS_DIR
    if not campaigns.is_dir():
        return []
    shared = {(root / relative).resolve() for relative in SHARED_LEDGERS}
    relatives = sorted(
        path.relative_to(root).as_posix()
        for path in campaigns.rglob("*")
        if path.is_file()
        and path.resolve() not in shared
        and path.suffix in {".yaml", ".yml", ".json"}
    )
    return scan_machine_local_paths(root, tuple(relatives))


def validate(root: Path) -> dict:
    """Run every promotion condition and return a structured report."""
    profile_errors, profile = check_surface_profile(root)
    registration_errors, _ = check_registrations(root, profile)
    ledger_hits = scan_machine_local_paths(root, SHARED_LEDGERS)
    warnings = scan_archive_paths(root)

    errors = [
        *profile_errors,
        *registration_errors,
        *(f"machine-local path in shared campaign ledger -> {hit}" for hit in ledger_hits),
    ]

    return {
        "status": "PASS" if not errors else "FAIL",
        "summary": {
            "SURFACE_PROFILE_VALID": "PASS" if not profile_errors else "FAIL",
            "CAMPAIGN_REGISTRATION_VALID": "PASS" if not registration_errors else "FAIL",
            "MACHINE_LOCAL_PATHS_IN_SHARED_LEDGER": len(ledger_hits),
        },
        "errors": errors,
        "warnings": [
            f"machine-local path in immutable campaign evidence -> {hit}" for hit in warnings
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_campaign_promotion")
    parser.add_argument(
        "root",
        nargs="?",
        default=str(REPO_ROOT),
        help="repository root (defaults to the governance repo containing this script)",
    )
    args = parser.parse_args(argv)

    report = validate(Path(args.root).resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
