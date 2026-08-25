#!/usr/bin/env python3
"""The one Claude projection engine.

Single entrypoint that converges every managed Claude-native asset onto the
canonical sources in this repository, across all managed domains:

  skills    per-skill symlinks (SKILL_ADAPTER_ROOTS.yaml adapters)
  commands  per-command symlinks from commands/COMMANDS_MANIFEST.yaml
  rules     rules/*.mdc -> generated llm-rules mount -> directory symlinks
  settings  settings.template.json triad (gov / user / workspace merge)
  hooks     consumer hook files installed beside settings
  plugins   declarative state from plugins.desired.json; the imperative
            setup_claude_code_plugins.sh runs only as fallback

Setup (install.sh) and SessionStart both call this entrypoint, so a cached
environment reconciles even when the bootstrap never ran. Every run emits a
structured projection receipt (schema l9.claude-projection.v1) to
~/.l9/claude/projection-receipt.json.

Domain logic lives in the existing reconcilers — this engine orchestrates
them; it does not reimplement them.

Usage:
  python3 ops/scripts/claude_projection.py --root "$HOME/.cursor-governance" \
      --workspace /path/to/repo [--check] [--domains skills,commands,rules]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

RECEIPT_SCHEMA = "l9.claude-projection.v1"
ALL_DOMAINS = ("skills", "commands", "rules", "settings", "hooks", "plugins")
PLUGINS_DESIRED_REL = Path("environment/agents/adapters/claude-code/plugins.desired.json")
PLUGIN_CLASSIFIER_REL = Path("ops/hooks/workspace_open_plugin_loader.py")


def default_receipt_path() -> Path:
    return Path.home() / ".l9" / "claude" / "projection-receipt.json"


def governance_sha(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and sha else "UNKNOWN"


class DomainOutcome:
    def __init__(self, name: str) -> None:
        self.name = name
        self.status = "ok"  # ok | drift | conflict | error | skipped
        self.projected = 0
        self.stale_removed = 0
        self.collisions: list[str] = []
        self.failures: list[str] = []
        self.detail: dict[str, Any] = {}

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.name,
            "status": self.status,
            "projected": self.projected,
            "stale_removed": self.stale_removed,
            "collisions": self.collisions,
            "failures": self.failures,
            "detail": self.detail,
        }


def project_skills(root: Path, workspace: Path, check: bool) -> DomainOutcome:
    outcome = DomainOutcome("skills")
    try:
        from reconcile_llm_skill_adapters import reconcile_adapters, run_orphan_migration

        migration = run_orphan_migration(workspace, check=check, quiet=True)
        if migration is not None:
            outcome.detail["orphan_migration"] = migration
            if migration.get("returncode", 0) != 0:
                outcome.failures.append("orphan-migration-conflict")
        payload = reconcile_adapters(root, workspace=workspace, check=check)
    except Exception as exc:  # noqa: BLE001
        outcome.status = "error"
        outcome.failures.append(str(exc))
        return outcome
    outcome.detail["adapters"] = payload["results"]
    for result in payload["results"]:
        outcome.projected += len(result.get("current", [])) + len(result.get("created", []))
        outcome.stale_removed += len(result.get("removed", []))
        outcome.failures.extend(result.get("conflicts", []))
        if result.get("drift"):
            outcome.status = "drift"
            outcome.detail.setdefault("drift", []).extend(result["drift"])
    if any(str(item).startswith("unmanaged-conflict:") for item in outcome.failures):
        outcome.status = "conflict"
    elif outcome.failures and outcome.status == "ok":
        outcome.status = "conflict"
    return outcome


def project_commands(root: Path, workspace: Path, check: bool) -> DomainOutcome:
    outcome = DomainOutcome("commands")
    try:
        from reconcile_claude_commands import reconcile

        payload = reconcile(root, workspace=workspace, check=check)
    except Exception as exc:  # noqa: BLE001
        outcome.status = "error"
        outcome.failures.append(str(exc))
        return outcome
    outcome.detail["scopes"] = payload["results"]
    for result in payload["results"]:
        outcome.projected += len(result.get("current", [])) + len(result.get("created", []))
        outcome.stale_removed += len(result.get("removed", []))
        outcome.collisions.extend(result.get("collisions", []))
        outcome.failures.extend(result.get("conflicts", []))
        if result.get("drift"):
            outcome.status = "drift"
            outcome.detail.setdefault("drift", []).extend(result["drift"])
    if outcome.failures and outcome.status in ("ok", "drift"):
        outcome.status = "conflict"
    # A command/skill namespace collision is fail-closed per entry (the skill
    # stays authoritative) and reported — it is not a projection failure.
    outcome.collisions = sorted(set(outcome.collisions))
    return outcome


def project_rules(root: Path, workspace: Path, check: bool) -> DomainOutcome:
    outcome = DomainOutcome("rules")
    try:
        import project_llm_rules as rules_projector
        from reconcile_llm_rule_adapters import reconcile_adapters

        if check:
            errors = rules_projector.check_projection(root)
            if errors:
                outcome.status = "drift"
                outcome.detail["projection_errors"] = errors
        else:
            rules_projector.materialize(root)
        payload = reconcile_adapters(root, workspace=workspace, check=check)
    except Exception as exc:  # noqa: BLE001
        outcome.status = "error"
        outcome.failures.append(str(exc))
        return outcome
    outcome.detail["adapters"] = payload["results"]
    for result in payload["results"]:
        if result["status"] == "error":
            outcome.status = "error"
            outcome.failures.append(f"{result.get('adapter_id')}:{result.get('action')}")
        elif result["status"] == "drift" and outcome.status == "ok":
            outcome.status = "drift"
        elif result["status"] == "ok":
            outcome.projected += 1
    return outcome


def project_settings(
    root: Path, workspace: Path, check: bool
) -> tuple[DomainOutcome, DomainOutcome]:
    settings_outcome = DomainOutcome("settings")
    hooks_outcome = DomainOutcome("hooks")
    try:
        from reconcile_claude_settings import run as settings_run

        payload = settings_run(root, workspace=workspace, user=True, gov=True, check=check)
    except Exception as exc:  # noqa: BLE001
        settings_outcome.status = "error"
        settings_outcome.failures.append(str(exc))
        hooks_outcome.status = "error"
        return settings_outcome, hooks_outcome

    def is_hook_path(path: str) -> bool:
        return "/hooks/" in path.replace(os.sep, "/")

    wrote = [str(p) for p in payload.get("wrote", [])]
    drift = [str(p) for p in payload.get("drift", [])]
    settings_outcome.projected = sum(1 for p in wrote if not is_hook_path(p))
    hooks_outcome.projected = sum(1 for p in wrote if is_hook_path(p))
    settings_drift = [p for p in drift if not is_hook_path(p)]
    hooks_drift = [p for p in drift if is_hook_path(p)]
    if settings_drift:
        settings_outcome.status = "drift"
        settings_outcome.detail["drift"] = settings_drift
    if hooks_drift:
        hooks_outcome.status = "drift"
        hooks_outcome.detail["drift"] = hooks_drift
    settings_outcome.detail["scopes"] = {
        key: payload[key] for key in ("governance", "user", "workspace") if key in payload
    }
    return settings_outcome, hooks_outcome


def load_plugins_desired(root: Path) -> dict[str, Any]:
    path = root / PLUGINS_DESIRED_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"plugin desired state must be a mapping: {path}")
    return data


def classify_workspace(root: Path, workspace: Path) -> str:
    classifier = root / PLUGIN_CLASSIFIER_REL
    if not classifier.is_file():
        return "core_default"
    try:
        proc = subprocess.run(
            [sys.executable, str(classifier), "--classify", str(workspace)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "core_default"
    name = proc.stdout.strip()
    return name if proc.returncode == 0 and name else "core_default"


def plugin_desired_set(
    desired: dict[str, Any], workspace_class: str
) -> tuple[list[str], list[str]]:
    core = desired.get("core") or {}
    class_cfg = (desired.get("classes") or {}).get(workspace_class) or {}
    marketplaces = list(core.get("marketplaces") or [])
    for repo in class_cfg.get("marketplaces") or []:
        if repo not in marketplaces:
            marketplaces.append(repo)
    plugins = list(core.get("plugins") or []) + list(class_cfg.get("plugins") or [])
    return marketplaces, plugins


def plugin_desired_hash(marketplaces: list[str], plugins: list[str]) -> str:
    content = "\n".join([*marketplaces, *plugins]) + "\n"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def installed_plugin_names() -> str | None:
    if shutil.which("claude") is None:
        return None
    try:
        proc = subprocess.run(
            ["claude", "plugin", "list"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def project_plugins(root: Path, workspace: Path, check: bool) -> DomainOutcome:
    """Declarative-first plugin convergence.

    The declaration (plugins.desired.json) is the desired state; the stamp +
    `claude plugin list` are the observed state. Only when they disagree does
    the imperative fallback (setup_claude_code_plugins.sh) run — and only in
    apply mode.
    """
    outcome = DomainOutcome("plugins")
    try:
        desired = load_plugins_desired(root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        outcome.status = "error"
        outcome.failures.append(f"desired-state-unreadable: {exc}")
        return outcome

    workspace_class = classify_workspace(root, workspace)
    marketplaces, plugins = plugin_desired_set(desired, workspace_class)
    outcome.detail["workspace_class"] = workspace_class
    outcome.detail["desired_plugins"] = plugins

    if os.environ.get("SKIP_PLUGIN_MARKETPLACE", "") == "true":
        outcome.status = "skipped"
        outcome.detail["reason"] = "marketplace disabled by the platform"
        return outcome

    installed = installed_plugin_names()
    if installed is None:
        outcome.status = "skipped"
        outcome.detail["reason"] = "claude CLI unavailable"
        return outcome

    stamp = Path.home() / ".claude" / "plugins" / f".l9-plugin-desired-hash-{workspace_class}"
    want_hash = plugin_desired_hash(marketplaces, plugins)
    stamp_ok = stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == want_hash
    missing = [
        entry for entry in plugins if entry.split("@", 1)[0].lower() not in installed.lower()
    ]
    satisfied = stamp_ok and not missing
    outcome.detail["stamp_current"] = stamp_ok
    outcome.detail["missing"] = missing

    if satisfied:
        outcome.projected = len(plugins)
        return outcome
    if check:
        outcome.status = "drift"
        return outcome

    fallback = root / "ops" / "scripts" / "setup_claude_code_plugins.sh"
    if not fallback.is_file():
        outcome.status = "error"
        outcome.failures.append("imperative fallback missing")
        return outcome
    try:
        proc = subprocess.run(
            ["bash", str(fallback), "--quiet", "--workspace", str(workspace)],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        outcome.status = "error"
        outcome.failures.append(f"fallback-failed: {exc}")
        return outcome
    outcome.detail["fallback_rc"] = proc.returncode
    installed = installed_plugin_names() or ""
    still_missing = [
        entry for entry in plugins if entry.split("@", 1)[0].lower() not in installed.lower()
    ]
    if still_missing:
        outcome.status = "drift"
        outcome.detail["missing"] = still_missing
        outcome.projected = len(plugins) - len(still_missing)
    else:
        outcome.projected = len(plugins)
        outcome.detail["missing"] = []
    return outcome


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def overall_status(outcomes: list[DomainOutcome]) -> str:
    ranks = {
        status: idx for idx, status in enumerate(("ok", "skipped", "drift", "conflict", "error"))
    }
    worst = "ok"
    for outcome in outcomes:
        if ranks.get(outcome.status, 0) > ranks[worst]:
            worst = outcome.status
    if worst == "skipped":
        return "ok"
    return worst


def run(
    root: Path,
    workspace: Path,
    *,
    check: bool = False,
    domains: tuple[str, ...] = ALL_DOMAINS,
    receipt_path: Path | None = None,
    write_receipt: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    workspace = workspace.resolve()
    outcomes: list[DomainOutcome] = []
    wanted = set(domains)

    if "skills" in wanted:
        outcomes.append(project_skills(root, workspace, check))
    if "commands" in wanted:
        outcomes.append(project_commands(root, workspace, check))
    if "rules" in wanted:
        outcomes.append(project_rules(root, workspace, check))
    if "settings" in wanted or "hooks" in wanted:
        settings_outcome, hooks_outcome = project_settings(root, workspace, check)
        if "settings" in wanted:
            outcomes.append(settings_outcome)
        if "hooks" in wanted:
            outcomes.append(hooks_outcome)
    if "plugins" in wanted:
        outcomes.append(project_plugins(root, workspace, check))

    status = overall_status(outcomes)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "governance_SHA": governance_sha(root),
        "workspace": str(workspace),
        "check": check,
        "managed_domains": sorted(wanted & set(ALL_DOMAINS)),
        "projected_count_by_domain": {o.name: o.projected for o in outcomes},
        "stale_removed_by_domain": {o.name: o.stale_removed for o in outcomes},
        "collisions": sorted({c for o in outcomes for c in o.collisions}),
        "failures": [f"{o.name}:{f}" for o in outcomes for f in o.failures],
        "status": status,
        "domains": [o.as_dict() for o in outcomes],
    }
    if write_receipt and not check:
        atomic_write(
            receipt_path or default_receipt_path(),
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--domains",
        type=str,
        default=",".join(ALL_DOMAINS),
        help=f"comma-separated subset of: {','.join(ALL_DOMAINS)}",
    )
    parser.add_argument("--receipt", type=Path, default=None)
    parser.add_argument("--no-receipt", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--summary", action="store_true", help="grep-friendly per-domain lines")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    domains = tuple(d.strip() for d in args.domains.split(",") if d.strip())
    unknown = [d for d in domains if d not in ALL_DOMAINS]
    if unknown:
        print(f"ERROR: unknown domains: {unknown}", file=sys.stderr)
        return 2

    try:
        receipt = run(
            args.root,
            args.workspace,
            check=args.check,
            domains=domains,
            receipt_path=args.receipt,
            write_receipt=not args.no_receipt,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.summary:
        for domain in receipt["domains"]:
            print(
                f"domain={domain['domain']} status={domain['status']} "
                f"projected={domain['projected']} stale_removed={domain['stale_removed']}"
            )
        print(f"projection={receipt['status']}")
    elif args.json or not args.quiet:
        print(json.dumps(receipt, indent=2, sort_keys=True))

    if receipt["status"] == "error":
        return 2
    return 0 if receipt["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
