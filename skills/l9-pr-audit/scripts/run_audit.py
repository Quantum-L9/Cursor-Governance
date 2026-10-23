#!/usr/bin/env python3
"""One entry point for an l9-pr-audit run, in two phases around the semantic lanes.

  prepare   collect snapshots -> build change ledgers -> bind canonical authority
            -> materialize machine rows -> write lanes.plan.json
  (lanes)   run one semantic lane per planned group (references/semantic-lane.md);
            each writes lanes/<lane>.json; then one independent verifier lane reproduces
            every merge-blocking finding into lanes/verify-<lane>.json; the parent writes
            judgment.json
  finalize  validate lanes + judgment -> assemble audit.json -> derive -> validate
            -> build the bundle -> verify the bundle

Every artifact lives in --run-dir; nothing is written to the audited repository except
PR head refs fetched into the given clone.

Usage:
  run_audit.py prepare  --repo OWNER/NAME --clone PATH --run-dir DIR [--pr N ...] [--authority-root PATH]
  run_audit.py finalize --run-dir DIR [--autoremediate 0|1]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable


def step(label: str, *cmd: str | Path, out: Path | None = None) -> str:
    print(f"== {label}", flush=True)
    result = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if out is not None:
        out.write_text(result.stdout)
    if result.returncode != 0 and out is None:
        sys.stderr.write(result.stdout[-4000:] + result.stderr[-4000:])
        raise SystemExit(f"FAIL: {label} (exit {result.returncode})")
    return result.stdout


def ledger_args(run: Path) -> list[str]:
    args: list[str] = []
    for path in sorted((run / "ledgers").glob("pr-*-ledger.json")):
        args += ["--change-ledger", str(path)]
    return args


def lane_plan(frozen: dict) -> list[dict]:
    """Group PRs into lanes: a stack or a set of overlapping PRs is one lane (its merged tree must
    be tested together); dependency-bot PRs share one lane; the rest run alone."""
    parent = {p["pr"]: p["pr"] for p in frozen["prs"]}

    def root(n: int) -> int:
        while parent[n] != n:
            n = parent[n]
        return n

    for p in frozen["prs"]:
        for other in [p.get("stacked_on"), *(p.get("overlaps_with") or [])]:
            if other in parent and root(other) != root(p["pr"]):
                parent[root(p["pr"])] = root(other)
    groups: dict[str, list[int]] = defaultdict(list)
    for p in frozen["prs"]:
        snap_author = p.get("author", "")
        key = (
            "deps"
            if snap_author.endswith("[bot]") and root(p["pr"]) == p["pr"]
            else f"pr-{root(p['pr'])}"
        )
        groups[key].append(p["pr"])
    return [{"lane": k, "prs": sorted(v)} for k, v in sorted(groups.items())]


def prepare(args: argparse.Namespace) -> None:
    run: Path = args.run_dir
    (run / "ledgers").mkdir(parents=True, exist_ok=True)
    (run / "lanes").mkdir(exist_ok=True)
    collect = [
        PY,
        SCRIPTS / "collect_snapshot.py",
        "--repo",
        args.repo,
        "--clone",
        args.clone,
        "--out",
        run,
    ]
    for n in args.pr:
        collect += ["--pr", str(n)]
    step("collect snapshots", *collect)
    frozen = json.loads((run / "frozen-pr-set.json").read_text())
    for p in frozen["prs"]:
        snap = json.loads((run / "snapshots" / f"pr-{p['pr']}.json").read_text())
        p["author"] = snap["author"]
        step(
            f"change ledger #{p['pr']}",
            PY,
            SCRIPTS / "build_change_ledger.py",
            "--snapshot",
            run / "snapshots" / f"pr-{p['pr']}.json",
            "--output",
            run / "ledgers" / f"pr-{p['pr']}-ledger.json",
        )
    verify = [PY, SCRIPTS / "verify_canonical_authority.py", "--mode", "admitted"]
    if args.authority_root:
        verify += ["--authority-root", args.authority_root]
    step("bind canonical authority", *verify, out=run / "canonical-binding.json")
    binding = json.loads((run / "canonical-binding.json").read_text())
    status = binding.get("canonical_authority_binding", binding).get("status")
    print(f"   canonical authority: {status}")
    # Canonical invariants are seeded only from an admitted binding; otherwise the global
    # layer stays a typed Unknown and the builder must not try to load its composed view.
    seed = (
        ["--canonical-binding", run / "canonical-binding.json"]
        if status == "ADMITTED_AND_CURRENT"
        else []
    )
    step(
        "materialize machine rows",
        PY,
        SCRIPTS / "build_audit_bundle.py",
        "--materialize-machine-rows",
        run / "machine-rows.json",
        "--authority-id",
        args.authority_id,
        *seed,
        *ledger_args(run),
    )
    plan = {
        "lanes": lane_plan(frozen),
        "verify": "After the lanes: one verifier lane that authored none of the findings reproduces "
        "every merge_blocking finding on the exact head and writes lanes/verify-<verifier>.json "
        "(schemas/finding-verification.schema.json).",
    }
    (run / "lanes.plan.json").write_text(json.dumps(plan, indent=1))
    print(json.dumps(plan, indent=1))
    print(
        f"\nNext: run one semantic lane per group (references/semantic-lane.md) writing {run}/lanes/<lane>.json,\n"
        f"then the independent verifier lane writing {run}/lanes/verify-<verifier>.json,\n"
        f"write {run}/judgment.json (schemas/judgment.schema.json, authority_id {args.authority_id} must be declared),\n"
        f"then: run_audit.py finalize --run-dir {run}"
    )


def finalize(args: argparse.Namespace) -> None:
    run: Path = args.run_dir
    ledgers = ledger_args(run)
    step("assemble audit.json", PY, SCRIPTS / "assemble_audit.py", "--run-dir", run)
    print(
        step(
            "derive post-judgment fields",
            PY,
            SCRIPTS / "build_audit_bundle.py",
            "--audit",
            run / "audit.json",
            "--derive",
            run / "audit.json",
            *ledgers,
        ).count("\n"),
        "derived changes",
    )
    step(
        "validate audit.json",
        PY,
        SCRIPTS / "build_audit_bundle.py",
        "--audit",
        run / "audit.json",
        *ledgers,
        "--validate-only",
    )
    out = step(
        "build bundle",
        PY,
        SCRIPTS / "build_audit_bundle.py",
        "--audit",
        run / "audit.json",
        *ledgers,
        "--output-dir",
        run / "bundle",
        "--autoremediate",
        str(args.autoremediate),
    )
    zip_path = next(line for line in out.splitlines() if line.endswith(".zip"))
    step(
        "verify bundle",
        PY,
        SCRIPTS / "build_audit_bundle.py",
        "--verify-bundle",
        zip_path,
        *ledgers,
    )
    audit = json.loads((run / "audit.json").read_text())
    verdict = audit["executive_verdict"]
    print(f"\nPASS: {zip_path}\n{verdict['summary']}\nconvergence: {verdict['convergence_status']}")
    for v in audit["per_pr_verdicts"]:
        print(f"  #{v['pr_number']}: {v['merge_readiness']} {v['blocking_finding_ids'] or ''}")
    caught_only = [
        f["finding_id"]
        for f in audit["findings"]
        if f["detection"]["ci"] != "CAUGHT" and f["detection"]["bot_review"] != "CAUGHT"
    ]
    print(
        f"caught only by audit: {len(caught_only)} of {len(audit['findings'])} {caught_only or ''}"
    )
    gaps = [
        u["unknown_id"]
        for u in audit["residual_unknowns"]
        if u["unknown_id"].startswith(("U-PROBE-", "U-VERIFY-", "U-OBJECTIVE-"))
    ]
    if gaps:
        print(f"method gaps: {', '.join(gaps)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="phase", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--repo", required=True)
    p.add_argument("--clone", required=True, type=Path)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--pr", type=int, action="append", default=[])
    p.add_argument("--authority-root", type=Path)
    p.add_argument(
        "--authority-id",
        default="AUTH-REPO-LAW",
        help="authority_id the machine claims cite; declare it in judgment.json",
    )
    f = sub.add_parser("finalize")
    f.add_argument("--run-dir", required=True, type=Path)
    f.add_argument("--autoremediate", type=int, choices=(0, 1), default=0)
    args = ap.parse_args()
    (prepare if args.phase == "prepare" else finalize)(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
