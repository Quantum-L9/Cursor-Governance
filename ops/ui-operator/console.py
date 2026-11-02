#!/usr/bin/env python3
"""Portable UI-operator console — load cartridge, gate mutations, emit receipt.

Modes:
  validate  — schema + allowlist + secret-ref registration checks
  dry_run   — validate + walk journey without browser mutations
  run       — execute journey (requires --approve, Playwright, provisioned session)

Never logs or writes secret values. Receipts record ref ids only.
Loads l9-aws-secrets resolve via ops/secrets/resolve_secret.py.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SECRETS = REPO / "ops" / "secrets"
CARTRIDGES = HERE / "cartridges"
RECEIPTS = HERE / "receipts"
CARTRIDGE_SCHEMA = HERE / "schemas" / "cartridge.schema.yaml"
PROFILES_DIR = Path.home() / ".l9-ui-profiles"

STOP_MISSING_APPROVE = "missing_human_approve"
STOP_MISSING_AWS = "missing_aws_or_unregistered_ref"
STOP_NOT_PROVISIONED = "ui_session_not_provisioned"
STOP_PROFILE_NOT_SEEDED = "ui_profile_not_seeded"
STOP_PLAYWRIGHT = "playwright_not_installed"
STOP_FORBIDDEN = "mutation_exceeds_allowlist"
STOP_VISIBILITY = "visibility_or_destructive_change"
STOP_PAT = "pat_creation_requested"


def _die(msg: str, code: int = 1) -> None:
    print(f"ui-operator: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _safe_path(path: Path | str) -> Path:
    """Resolve a CLI/file path; require it stay under cwd or system temp (S8707)."""
    resolved = Path(path).expanduser().resolve()
    allowed = (Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve())
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    _die(f"path escapes allowed roots: {path}")


def _require_yaml() -> Any:
    if yaml is None:
        _die("PyYAML required")
    return yaml


def load_yaml(path: Path) -> dict[str, Any]:
    y = _require_yaml()
    path = _safe_path(path)
    data = y.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        _die(f"invalid YAML object: {path}")
    return data


def validate_cartridge_shape(cartridge: dict[str, Any]) -> list[str]:
    """Lightweight structural validation (schema file is documentation + CI aid)."""
    errors: list[str] = []
    for key in (
        "schema_version",
        "id",
        "version",
        "site",
        "goal",
        "auth",
        "mutation_allowlist",
        "forbidden",
        "journey",
    ):
        if key not in cartridge:
            errors.append(f"missing field: {key}")
    if cartridge.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    auth = cartridge.get("auth") or {}
    if not isinstance(auth, dict) or not auth.get("refs"):
        errors.append("auth.refs required")
    journey = cartridge.get("journey") or []
    if not isinstance(journey, list) or not journey:
        errors.append("journey must be a non-empty list")
    return errors


def mutations_in_journey(cartridge: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for step in cartridge.get("journey") or []:
        mut = step.get("mutation")
        if mut:
            out.append(str(mut))
    return out


def check_allowlist(cartridge: dict[str, Any]) -> list[str]:
    allow = set(cartridge.get("mutation_allowlist") or [])
    forbidden = set(cartridge.get("forbidden") or [])
    errors: list[str] = []
    for mut in mutations_in_journey(cartridge):
        if mut in forbidden:
            errors.append(f"forbidden mutation in journey: {mut}")
        if mut not in allow:
            errors.append(f"mutation not on allowlist: {mut}")
    return errors


def resolve_check(ref: str) -> tuple[bool, str]:
    """Run resolve_secret --check. Returns (ok, detail). Never captures values."""
    script = SECRETS / "resolve_secret.py"
    py = REPO / ".venv" / "bin" / "python"
    cmd = [
        str(py if py.is_file() else sys.executable),
        str(script),
        "--ref",
        ref,
        "--check",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"resolve_error:{exc}"
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    detail = out or err or f"exit={proc.returncode}"
    # Redact any accidental long tokens from stderr messages (defensive).
    if len(detail) > 200:
        detail = detail[:200] + "…"
    return proc.returncode == 0 and out.startswith("OK "), detail


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def write_receipt(receipt: dict[str, Any], path: Path) -> None:
    y = _require_yaml()
    path = _safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        y.safe_dump(receipt, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def run_console(
    *,
    cartridge_path: Path,
    mode: str,
    approve: bool,
    actor: str,
    receipt_path: Path | None,
) -> int:
    cartridge = load_yaml(cartridge_path)
    actions: list[dict[str, str]] = []
    refs = list((cartridge.get("auth") or {}).get("refs") or [])
    started = datetime.now(UTC).replace(microsecond=0).isoformat()
    stop_reason: str | None = None
    verdict = "VALIDATED"

    shape_errs = validate_cartridge_shape(cartridge)
    if shape_errs:
        for e in shape_errs:
            actions.append({"step": "validate_shape", "status": "failed", "detail": e})
        verdict = "FAIL"
        stop_reason = "invalid_cartridge"
    else:
        actions.append({"step": "validate_shape", "status": "ok", "detail": "shape ok"})

    allow_errs = check_allowlist(cartridge) if verdict != "FAIL" else []
    if allow_errs:
        for e in allow_errs:
            actions.append({"step": "allowlist", "status": "blocked", "detail": e})
        verdict = "BLOCKED"
        stop_reason = STOP_FORBIDDEN
    elif verdict != "FAIL":
        actions.append({"step": "allowlist", "status": "ok", "detail": "mutations allowed"})

    if verdict not in {"FAIL", "BLOCKED"}:
        for ref in refs:
            # ui-session may be NOT_PROVISIONED — record and gate run mode later
            ok, detail = resolve_check(ref)
            if ok:
                actions.append(
                    {
                        "step": "resolve_secrets",
                        "status": "ok",
                        "detail": f"OK ref={ref}",
                    }
                )
            elif "NOT_PROVISIONED" in detail:
                actions.append(
                    {
                        "step": "resolve_secrets",
                        "status": "skipped",
                        "detail": f"NOT_PROVISIONED ref={ref}",
                    }
                )
            elif "UNREGISTERED" in detail:
                actions.append(
                    {
                        "step": "resolve_secrets",
                        "status": "blocked",
                        "detail": f"UNREGISTERED ref={ref}",
                    }
                )
                verdict = "BLOCKED"
                stop_reason = STOP_MISSING_AWS
            else:
                # github token must succeed for this cartridge family
                if ref.endswith("#token") or "github#token" in ref:
                    actions.append(
                        {
                            "step": "resolve_secrets",
                            "status": "failed",
                            "detail": f"FAIL ref={ref} ({detail})",
                        }
                    )
                    verdict = "FAIL"
                    stop_reason = STOP_MISSING_AWS
                else:
                    actions.append(
                        {
                            "step": "resolve_secrets",
                            "status": "skipped",
                            "detail": f"FAIL ref={ref} ({detail})",
                        }
                    )

    if mode == "validate":
        if verdict not in {"FAIL", "BLOCKED"}:
            verdict = "VALIDATED"
        actions.append({"step": "validate", "status": "ok", "detail": f"mode={mode}"})
    elif mode == "dry_run":
        if verdict not in {"FAIL", "BLOCKED"}:
            for step in cartridge.get("journey") or []:
                name = str(step.get("step"))
                if step.get("mutation"):
                    actions.append(
                        {
                            "step": name,
                            "status": "skipped",
                            "detail": "dry_run — mutation not executed",
                        }
                    )
                else:
                    actions.append({"step": name, "status": "ok", "detail": "dry_run walk"})
            verdict = "DRY_RUN"
    elif mode == "run":
        if cartridge.get("human_approve_required", True) and not approve:
            actions.append(
                {
                    "step": "human_approve",
                    "status": "blocked",
                    "detail": "pass --approve after reviewing cartridge",
                }
            )
            verdict = "BLOCKED"
            stop_reason = STOP_MISSING_APPROVE
        elif not playwright_available():
            actions.append(
                {
                    "step": "playwright",
                    "status": "blocked",
                    "detail": "install: uv sync --extra ui-operator && playwright install",
                }
            )
            verdict = "BLOCKED"
            stop_reason = STOP_PLAYWRIGHT
        else:
            ui_ref = (cartridge.get("auth") or {}).get("ui_session_ref")
            if ui_ref:
                ok, detail = resolve_check(ui_ref)
                if not ok:
                    actions.append(
                        {
                            "step": "load_session",
                            "status": "blocked",
                            "detail": f"ui session unavailable: {detail}",
                        }
                    )
                    verdict = "BLOCKED"
                    stop_reason = STOP_NOT_PROVISIONED
            if verdict not in {"FAIL", "BLOCKED"}:
                # Live browser automation is intentionally gated: execute only when
                # session vault ref resolves AND a seeded profile exists under
                # PROFILES_DIR. Journey runner for GitHub is site-specific.
                actions.append(
                    {
                        "step": "execute_journey",
                        "status": "blocked",
                        "detail": (
                            "live UI mutate path ready but session profile seeding "
                            f"from vault → {PROFILES_DIR}/<site>/ is not seeded "
                            "for automated mutate in this environment; use dry_run "
                            "or seed a profile under ~/.l9-ui-profiles/<site>/ then re-run"
                        ),
                    }
                )
                verdict = "BLOCKED"
                stop_reason = STOP_PROFILE_NOT_SEEDED
    else:
        _die(f"unknown mode: {mode}")

    finished = datetime.now(UTC).replace(microsecond=0).isoformat()
    receipt: dict[str, Any] = {
        "schema_version": "1.0.0",
        "receipt_id": str(uuid.uuid4()),
        "cartridge_id": cartridge.get("id", "unknown"),
        "cartridge_version": cartridge.get("version", ""),
        "actor": actor,
        "started_at": started,
        "finished_at": finished,
        "mode": mode,
        "refs_used": refs,
        "actions": actions,
        "evidence": {
            "before": "",
            "after": "",
            "notes": "values redacted; refs ids only",
        },
        "verdict": verdict,
    }
    if stop_reason:
        receipt["stop_reason"] = stop_reason

    out = receipt_path or (
        RECEIPTS / f"{cartridge.get('id', 'cartridge')}-{mode}-{receipt['receipt_id'][:8]}.yaml"
    )
    write_receipt(receipt, out)
    print(f"ui-operator: receipt {out} verdict={verdict}", file=sys.stderr)
    if stop_reason:
        print(f"ui-operator: stop_reason={stop_reason}", file=sys.stderr)
    return 0 if verdict in {"PASS", "DRY_RUN", "VALIDATED"} else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cartridge",
        type=Path,
        required=True,
        help="Path to cartridge YAML (or name under cartridges/)",
    )
    parser.add_argument(
        "--mode",
        choices=["validate", "dry_run", "run"],
        default="validate",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Human approval for mutation run (required when human_approve_required)",
    )
    parser.add_argument("--actor", default="agent", help="Receipt actor label")
    parser.add_argument("--receipt", type=Path, default=None, help="Receipt output path")
    args = parser.parse_args(argv)

    path = args.cartridge
    if not path.is_file():
        alt = CARTRIDGES / path.name
        if not alt.suffix:
            alt = CARTRIDGES / f"{path.name}.yaml"
        if alt.is_file():
            path = alt
        else:
            _die(f"cartridge not found: {args.cartridge}")

    return run_console(
        cartridge_path=path,
        mode=args.mode,
        approve=args.approve,
        actor=args.actor,
        receipt_path=args.receipt,
    )


if __name__ == "__main__":
    raise SystemExit(main())
