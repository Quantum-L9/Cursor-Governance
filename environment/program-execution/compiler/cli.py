"""Minimal front door: program-execution intent (contract §15, Gate E)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .blueprint_validate import validate_or_repair
from .intent import parse_intent
from .repo_truth import discover
from .resolver import resolve, write_resolution
from .synthesizer import synthesize

STEPS = {
    "intent": "Intent parsed",
    "targets": "Targets resolved",
    "authority": "Authority resolved",
    "truth": "Repository truth loaded",
    "synthesis": "Program synthesized",
    "validation": "Blueprint validation {status}",
    "lock": "Program prepared for lock",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="program-execution",
        description="Compile minimal goal-level intent into a Program Execution Blueprint v2.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    intent_parser = sub.add_parser("intent", help="compile an intent into a Blueprint v2")
    intent_parser.add_argument("objective", help="natural-language goal")
    intent_parser.add_argument("--target", help="repository id (owner/repo) when not discoverable")
    intent_parser.add_argument(
        "--repo-root", type=Path, default=None, help="repository to discover truth from"
    )
    intent_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="blueprint output directory (default: $HOME/.l9/blueprints/<program-id>)",
    )
    intent_parser.add_argument("--policy-profile", default=None, help="autonomy policy profile id")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "intent":
        return 2
    raw: dict[str, object] = {"schema": "program-execution.intent.v1", "objective": args.objective}
    if args.target:
        raw["targets"] = [args.target]
    if args.policy_profile:
        raw["policy_profile"] = args.policy_profile
    try:
        intent = parse_intent(raw)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(STEPS["intent"])
    repo_root = (args.repo_root or Path.cwd()).resolve()
    truth = discover(repo_root)
    resolution = resolve(intent, truth=truth, profile_id=args.policy_profile)
    for target in resolution["targets"]:
        print(f"{STEPS['targets']}: {target['repository_id']}")
    if not resolution["targets"]:
        print(f"{STEPS['targets']}: NONE (explicit blocker, no invented target)", file=sys.stderr)
        print(
            "Explicit blocker: the target repository cannot be resolved safely "
            "(contract §20); supply --target or run inside the target repository.",
            file=sys.stderr,
        )
        return 4
    print(f"{STEPS['authority']}: {resolution['governing_authority']['policy_profile']}")
    print(STEPS["truth"])

    program_id = "pe-" + resolution["intent"]["id"].replace("INTENT-", "").lower()
    output = (args.output or (Path.home() / ".l9" / "blueprints" / program_id)).resolve()

    authority_required = resolution["decisions"]["requires_human_authority"]
    if authority_required:
        print(
            f"Program partially synthesized; {len(authority_required)} authority-bearing "
            "decision(s) require owner input"
        )
        for decision in authority_required:
            print(f"  - {decision}")
        print("Independent work remains unblocked where possible")

    synthesize(resolution, output)
    print(STEPS["synthesis"])
    resolution_path = output / "INTENT_RESOLUTION.yaml"
    write_resolution(resolution, resolution_path)
    from .synthesizer import instantiate as _instantiate

    _instantiate.write_manifest(output)  # resolution artifact participates in the manifest
    result = validate_or_repair(output)
    print(STEPS["validation"].format(status="PASS" if result.ok else "FAIL"))
    if not result.ok:
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)
        print(
            "Explicit blocker: official Blueprint validation failed; no Program Lock.",
            file=sys.stderr,
        )
        return 3

    print(STEPS["lock"])
    print(f"blueprint: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
