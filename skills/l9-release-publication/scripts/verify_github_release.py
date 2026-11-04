#!/usr/bin/env python3
"""Verify the published GitHub Release for a release tag: the last gate.

A pushed tag or a green release job is not a release. RELEASE_VERIFIED means
the host Release exists for this exact tag, is published (not a draft), the tag
resolves to the admitted commit, every required asset is attached, and, when
named, the maintained major tag points at the same commit.

Print one JSON object on stdout.

Exit 0: RELEASE_VERIFIED
Exit 1: MISMATCH (or invalid input)
Exit 2: RELEASE_ABSENT
Exit 3: TRANSPORT_BLOCKED
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_release_tag as tags  # noqa: E402  (sibling module, same pack)


def release_record(remote: str, tag: str) -> tuple[str, dict[str, Any]]:
    """Return (state, release json): state is present, absent, or blocked."""
    code, out, err = tags.gh_api(f"repos/{remote}/releases/tags/{tag}")
    if code != 0:
        if tags._is_404(out, err):
            return "absent", {}
        return "blocked", {"detail": (err or out).strip() or "release request failed"}
    record = tags._json_object(out)
    if record is None:
        return "blocked", {"detail": "release response was not a JSON object"}
    return "present", record


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a published GitHub Release.")
    parser.add_argument("--remote", required=True, help="owner/name on GitHub")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--peeled-commit", required=True, help="commit the release must name")
    parser.add_argument(
        "--require-asset", action="append", default=[], help="asset name (repeatable)"
    )
    parser.add_argument("--major-tag", help="maintained major tag that must point at the commit")
    parser.add_argument("--allow-prerelease", action="store_true")
    return parser.parse_args()


def _input_error(args: argparse.Namespace) -> str:
    if not tags._accepted(tags._REMOTE, args.remote):
        return "remote is not owner/name"
    if not tags._accepted(tags._TAG, args.tag) or not tags._accepted(tags._SHA, args.peeled_commit):
        return "tag or peeled commit is not an allowlisted token"
    if args.major_tag and not tags._accepted(tags._TAG, args.major_tag):
        return "major tag is not an allowlisted token"
    return ""


def _asset_names(record: dict[str, Any]) -> set[str]:
    """Asset names from a host Release; anything that is not a list of mappings yields none."""
    assets = record.get("assets")
    if not isinstance(assets, list):
        return set()
    return {str(a.get("name")) for a in assets if isinstance(a, dict)}


def _check_release(record: dict[str, Any], args: argparse.Namespace) -> list[str]:
    problems: list[str] = []
    if record.get("tag_name") != args.tag:
        problems.append(f"release tag_name is {record.get('tag_name')!r}")
    if record.get("draft"):
        problems.append("release is a draft")
    if record.get("prerelease") and not args.allow_prerelease:
        problems.append("release is a prerelease")
    missing = sorted(set(args.require_asset) - _asset_names(record))
    if missing:
        problems.append("missing assets: " + ", ".join(missing))
    return problems


def main() -> int:
    args = _parse()
    problem = _input_error(args)
    if problem:
        return tags._emit({"status": "MISMATCH", "detail": problem}, 1)
    peeled = args.peeled_commit.lower()
    payload: dict[str, Any] = {"remote": args.remote, "tag": args.tag, "expected_peeled": peeled}

    state, remote = tags.remote_identity(args.remote, args.tag)
    payload["tag_ref"] = remote
    if state == "blocked":
        payload["status"] = "TRANSPORT_BLOCKED"
        return tags._emit(payload, 3)
    if state == "absent" or remote.get("remote_peeled") != peeled:
        payload["status"] = "MISMATCH"
        payload["detail"] = "release tag is absent or does not resolve to the admitted commit"
        return tags._emit(payload, 1)

    state, record = release_record(args.remote, args.tag)
    if state == "blocked":
        payload.update({"status": "TRANSPORT_BLOCKED", **record})
        return tags._emit(payload, 3)
    if state == "absent":
        payload["status"] = "RELEASE_ABSENT"
        return tags._emit(payload, 2)
    payload["release"] = {
        "url": record.get("html_url"),
        "tag_name": record.get("tag_name"),
        "draft": bool(record.get("draft")),
        "prerelease": bool(record.get("prerelease")),
        "assets": sorted(_asset_names(record)),
    }
    problems = _check_release(record, args)

    if args.major_tag:
        major_state, major = tags.remote_identity(args.remote, args.major_tag)
        payload["major_tag"] = {"tag": args.major_tag, **major}
        if major_state == "blocked":
            payload["status"] = "TRANSPORT_BLOCKED"
            return tags._emit(payload, 3)
        if major_state == "absent" or major.get("remote_peeled") != peeled:
            problems.append(f"{args.major_tag} does not point at the release commit")

    if problems:
        payload["status"] = "MISMATCH"
        payload["detail"] = "; ".join(problems)
        return tags._emit(payload, 1)
    payload["status"] = "RELEASE_VERIFIED"
    return tags._emit(payload, 0)


if __name__ == "__main__":
    sys.exit(main())
