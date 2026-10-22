#!/usr/bin/env python3
"""Consume the admitted Cursor-Governance operating plane v2 without becoming a verifier.

All bundle, profile, source, receipt and producer verification belongs to the
existing parameterized verify_canonical_binding.py. Admission/currentness is
owned by the existing verify_coding_projection.resolve_admission adapter.

Candidate mode reports BOUND only for verified bytes; it NEVER releases payload.
Admitted mode releases a requested source class or one exact record ONLY after
both shared verifiers establish admission and currency against independent main.

No network writes, selector evaluation, profile creation or automatic skill routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.scripts.coding_projection_status import _authority  # noqa: E402
from tools.authority.verify_coding_projection import (  # noqa: E402
    Rejected,
    Unobserved,
    load_verifier,
    pinned_checkout,
    read_lock,
    resolve,
    resolve_admission,
)

PROFILE_REF = "l9.projection/cursor-governance-operating-plane@2"
PAYLOAD_SCHEMA = "l9.projection.cursor-governance-operating-plane/v2"
EXPECTED_CLASSES = (
    "vocabulary",
    "capabilities",
    "authority_model",
    "lifecycle",
    "invariants",
    "contracts",
    "error_taxonomy",
    "receipt_catalog",
)
BINDING_REL = Path("governance/authority-bindings/operating-plane-v2.yaml")
BUNDLE_REL = Path("generated/governance/operating_plane_v2")
BINDING_SCHEMA = "l9.cursor-governance.operating-plane-v2-binding/v1"
EXIT = {"CURRENT": 0, "BOUND": 5, "STALE": 4, "BLOCKED": 3, "UNVERIFIED": 3, "REJECTED": 1}


def _binding(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Unobserved(f"binding unavailable: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != BINDING_SCHEMA:
        raise Rejected("operating-plane-v2 binding schema mismatch")
    pins = value.get("upstream") or {}
    if pins.get("profile_ref") != PROFILE_REF or pins.get("payload_schema") != PAYLOAD_SCHEMA:
        raise Rejected("wrong upstream profile or payload schema")
    if (
        pins.get("profile_class") != "consumer"
        or pins.get("profile_consumer") != "Cursor-Governance"
    ):
        raise Rejected("wrong upstream profile class/consumer")
    if pins.get("source_classes") != list(EXPECTED_CLASSES):
        raise Rejected("binding source-class order differs from canonical operating plane v2")
    if (value.get("bundle") or {}).get("path") != BUNDLE_REL.as_posix():
        raise Rejected("binding points away from the committed operating-plane-v2 bundle")
    digest = pins.get("profile_digest")
    if not (isinstance(digest, str) and digest.startswith("sha256:") and len(digest) == 71):
        raise Unobserved("no real, digest-bound operating-plane-v2 profile admission")
    return value


def _status(state: str, reason: str, **detail: Any) -> dict[str, Any]:
    return {"profile_ref": PROFILE_REF, "status": state, "reason": reason, **detail}


def _payload(bundle: Path, verified: dict[str, Any], cls: str, record_id: str | None) -> Any:
    """Read ONLY the component already authenticated by the shared verifier."""
    entry = verified["entries"].get(cls)
    if entry is None:
        raise Rejected(f"requested source class not in verified bundle: {cls}")
    # Release exactly the bytes the verifier authenticated: re-hash what is read
    # against the verified lock entry, so a file swapped between verification
    # and release is refused instead of returned as CURRENT.
    data = (bundle / entry["path"]).read_bytes()
    if "sha256:" + hashlib.sha256(data).hexdigest() != entry.get("sha256"):
        raise Rejected(f"component bytes changed after verification: {cls}")
    document = json.loads(data.decode("utf-8"))
    payload = document["payload"]
    if record_id is None:
        return payload
    key = {"invariants": "invariants", "contracts": "contracts"}.get(cls)
    if key is None:
        raise Rejected("--record-id is supported only for invariants or contracts")
    collection = payload.get(key)
    if not isinstance(collection, list):
        raise Rejected(f"verified payload has no {key} record collection")
    matching = [
        item for item in collection if isinstance(item, dict) and item.get("id") == record_id
    ]
    if len(matching) != 1:
        raise Rejected(f"exact record id missing or ambiguous: {record_id}")
    return {key: matching}


def classify(
    *,
    repo_root: Path = REPO_ROOT,
    workspace: Path | None = None,
    authority_root: Path | None = None,
    expect_main: str | None = None,
    mode: str = "admitted",
    source_class: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    try:
        if source_class is not None and source_class not in EXPECTED_CLASSES:
            return _status("REJECTED", "SOURCE_CLASS_UNDECLARED", source_class=source_class)
        if record_id is not None and source_class not in ("invariants", "contracts"):
            return _status("REJECTED", "RECORD_ID_REQUIRES_INVARIANTS_OR_CONTRACTS")
        if mode == "candidate" and source_class is not None:
            return _status("BLOCKED", "CANDIDATE_MODE_NEVER_RELEASES_PROJECTION_CONTENT")
        binding = _binding(repo_root / BINDING_REL)
        bundle = repo_root / BUNDLE_REL
        lock = read_lock(bundle)
        pin = lock.get("projection_profile") or {}
        upstream = binding["upstream"]
        if pin != {"ref": PROFILE_REF, "digest": upstream["profile_digest"]}:
            return _status("STALE", "PROFILE_PIN_NOT_BINDING_PIN", observed=pin)
        if [x.get("source_class") for x in lock.get("components", [])] != list(EXPECTED_CLASSES):
            return _status("REJECTED", "LOCK_SOURCE_CLASSES_MISMATCH")
        root, rejected = _authority(workspace, authority_root)
        if root is None:
            return _status(
                "UNVERIFIED", "CANONICAL_AUTHORITY_CHECKOUT_NOT_AVAILABLE", rejected_roots=rejected
            )
        main = resolve(root, "refs/remotes/origin/main")
        if main is None:
            return _status("UNVERIFIED", "AUTHORITY_MAIN_NOT_RESOLVED")
        if expect_main is not None and expect_main != main:
            return _status(
                "STALE", "INDEPENDENT_MAIN_PIN_MISMATCH", expected=expect_main, observed=main
            )
        verifier = load_verifier(repo_root)
        spec = verifier.ProfileSpec(
            ref=PROFILE_REF,
            profile_class="consumer",
            consumer="Cursor-Governance",
            payload_schema=PAYLOAD_SCHEMA,
        )
        revision = lock["authority"]["revision"]
        with pinned_checkout(root, revision) as holder:
            verifier.verify_profile_bundle(Path(holder) / "authority", bundle, revision, spec)
        if mode == "candidate":
            return _status(
                "BOUND", "SOURCE_BUNDLE_VERIFIED_CANDIDATE_ONLY", authority_revision=revision
            )
        admitted = resolve_admission(root, main, lock, binding, repo_root=repo_root)
        if admitted.get("status") != "ADMITTED_AND_CURRENT":
            return _status(
                "BLOCKED",
                "ADMISSION_NOT_PROVED",
                admission_status=admitted.get("status"),
                admission_reason=admitted.get("reason"),
            )
        with pinned_checkout(root, main) as holder:
            current = verifier.verify_profile_bundle(Path(holder) / "authority", bundle, main, spec)
        result = _status(
            "CURRENT",
            "ADMITTED_AND_SOURCE_CURRENT",
            authority_revision=revision,
            authority_main=main,
            source_classes=list(EXPECTED_CLASSES),
            compiler_revision=(lock.get("producer") or {}).get("revision"),
        )
        if source_class is not None:
            result.update(
                source_class=source_class,
                projection=_payload(bundle, current, source_class, record_id),
            )
            if record_id is not None:
                result["record_id"] = record_id
        return result
    except Unobserved as exc:
        return _status("UNVERIFIED", str(exc))
    except Rejected as exc:
        return _status("REJECTED", str(exc))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return _status("BLOCKED", "REQUIRED_INPUT_UNRESOLVED", detail=str(exc))
    except Exception as exc:
        # Existing shared core gives status/reason via Outcome, no locally invented bypass.
        status, reason = getattr(exc, "status", None), getattr(exc, "reason", None)
        if status and reason:
            status = str(status)
            return _status(status if status in EXIT else "BLOCKED", str(reason))
        return _status("BLOCKED", "VERIFICATION_UNRESOLVED", detail=f"{type(exc).__name__}: {exc}")


def render_line(result: dict[str, Any]) -> str:
    """One SessionStart line; the Claude hook prints it, the Cursor hook renders markdown."""
    return f"operating-plane projection: {result['status']} — {result['reason']} (report-only)"


def render_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "### operating-plane projection",
            f"- {result['status']}: {result['reason']}",
            f"- profile: {PROFILE_REF} (consumer verifier; report-only)",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument(
        "--authority-root",
        type=Path,
        default=Path(os.environ["L9_AUTHORITY_ROOT"])
        if os.environ.get("L9_AUTHORITY_ROOT")
        else None,
    )
    parser.add_argument("--expect-main", default=None, help="independent canonical main tip SHA")
    parser.add_argument("--mode", choices=("candidate", "admitted"), default="admitted")
    parser.add_argument("--source-class", choices=EXPECTED_CLASSES)
    parser.add_argument("--record-id", default=None)
    parser.add_argument(
        "--format",
        choices=("json", "line", "markdown"),
        default="json",
        help="json exits with the status code (CI); line/markdown are SessionStart report-only "
        "renderings that never release payload and always exit 0",
    )
    args = parser.parse_args(argv)
    if args.format != "json" and (args.source_class or args.record_id):
        parser.error("--format line/markdown is report-only; it never releases a source class")
    try:
        result = classify(
            repo_root=args.repo_root,
            workspace=args.workspace,
            authority_root=args.authority_root,
            expect_main=args.expect_main,
            mode=args.mode,
            source_class=args.source_class,
            record_id=args.record_id,
        )
    except Exception as exc:  # noqa: BLE001 - a report-only line must always print
        if args.format == "json":
            raise
        result = _status("BLOCKED", f"classifier error: {type(exc).__name__}: {exc}")
    if args.format == "line":
        print(render_line(result))
        return 0
    if args.format == "markdown":
        print(render_markdown(result))
        return 0
    print(json.dumps(result, indent=2, sort_keys=True))
    return EXIT.get(result["status"], 3)


if __name__ == "__main__":
    raise SystemExit(main())
