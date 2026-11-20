#!/usr/bin/env python3
"""Campaign v1.1.0 static/structural checks. NOT PR, producer or host/runtime validation.

Usage: python tools/verify_campaign.py [--negative-controls]
       python tools/verify_campaign.py --collision-check
       <pr1011.json> <pr1030.json> <planned_d.json>

The collision files must be live API results bound to exact heads by the CTO. This tool
can compare their path sets; it cannot attest that the caller fetched current results.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_SHA = re.compile(r"^[0-9a-f]{40}$")
_H = re.compile(r"^[0-9a-f]{64}$")
_MERGES = {
    "Quantum-L9/.github#255",
    "Quantum-L9/Cursor-Governance#1011",
    "Quantum-L9/Cursor-Governance#1030",
}
_ALLOW = {
    "A": (
        set(),
        {
            "https://github.com/Quantum-L9/.github",
            "https://github.com/Quantum-L9/Cursor-Governance",
        },
    ),
    "B": (
        {"https://github.com/Quantum-L9/l9-semantic-compiler-engine"},
        {
            "https://github.com/Quantum-L9/.github",
            "https://github.com/Quantum-L9/Cursor-Governance",
        },
    ),
    "C": (
        {"https://github.com/Quantum-L9/Cursor-Governance"},
        {
            "https://github.com/Quantum-L9/.github",
            "https://github.com/Quantum-L9/l9-semantic-compiler-engine",
        },
    ),
    "D": (
        {"https://github.com/Quantum-L9/Cursor-Governance"},
        {
            "https://github.com/Quantum-L9/.github",
            "https://github.com/Quantum-L9/l9-semantic-compiler-engine",
        },
    ),
}


def _safe_path(p: str) -> bool:
    return (
        isinstance(p, str)
        and p
        and not p.startswith("/")
        and "\\" not in p
        and "\x00" not in p
        and all(k not in (".", "..", "") for k in p.split("/"))
    )


def header_of(text: str) -> dict:
    m = re.match(r"\A```yaml\n(.*?)\n```(?:\n|\Z)", text, re.DOTALL)
    if not m:
        return {}
    try:
        obj = yaml.safe_load(m.group(1))
        return obj["repository_access"] if isinstance(obj, dict) else {}
    except (yaml.YAMLError, KeyError, TypeError):
        return {}


def _errors(cfg: dict, snap: dict, approval: dict, briefs: dict[str, str]) -> list[str]:
    er = []
    if cfg.get("version") != "1.1.0":
        er.append("campaign version not v1.1.0")
    if cfg.get("status") != "ALIGNED_CAMPAIGN_HANDOFF_NOT_ADMITTED_NOT_EXECUTED":
        er.append("false activation/admission status")
    lane_ids = {lane.get("id") for lane in cfg.get("lanes", [])}
    if len(cfg.get("lanes", [])) != 4 or lane_ids != set("ABCD"):
        er.append("lane identity or capacity invalid")
    sw = cfg.get("swarm") or {}
    if sw.get("agents") != 4 or sw.get("upper_cap", 100) > 5 or sw.get("upper_cap", 0) < 4:
        er.append("swarm capacity breach")
    if set(cfg.get("merge_set", [])) != _MERGES:
        er.append("approved existing PR merge set changed")
    if _MERGES & set(cfg.get("excluded_merge_set", [])):
        er.append("excluded merge set collision")
    if "Quantum-L9/.github#254" not in cfg.get("excluded_merge_set", []):
        er.append("unrelated PR merge exclusion missing")
    if (
        not cfg.get("approval", {}).get("conditional_new_pr_merges")
        or "MERGE_PENDING" not in cfg["approval"]["conditional_new_pr_merges"]
    ):
        er.append("new PR merge authorization not distinguished")
    if cfg.get("admission") != {
        "operator_scoped": True,
        "global_semantics_unchanged": True,
        "exact_approved_content_required": True,
    }:
        er.append("operator scoped admission/global law boundary changed")
    cn = cfg.get("constraints") or {}
    for k in (
        "no_new_global_domain_or_source_registry",
        "strategy_instance_must_not_be_projected_through_canonical_global_source_spoofing",
        "no_second_plan_ssot",
        "unknown_never_pass",
        "existing_global_profiles_remain_immutable",
    ):
        if cn.get(k) is not True:
            er.append("nonnegotiable scope weakened " + k)
    if (
        cn.get("coding_agent_confidentiality_default")
        != "BLOCKED_UNTIL_ENFORCED_REPO_ACCESS_SEPARATION"
    ):
        er.append("unsafe coding agent privacy default")
    if len(approval.get("files", {})) != 5 or not approval.get("not_global_semantic_law"):
        er.append("approved five-file source identity invalid")
    if cfg.get("source_snapshot", {}).get("approved_subject_digest") != approval.get(
        "subject_digest"
    ) or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(approval.get("subject_digest"))):
        er.append("approved exact subject digest mismatch")
    material = copy.deepcopy(approval)
    material.pop("subject_digest", None)
    computed = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
    )
    if computed != approval.get("subject_digest"):
        er.append("approved manifest canonical-JSON subject digest is not self-consistent")
    if any(not _safe_path(k) or not _H.fullmatch(v) for k, v in approval.get("files", {}).items()):
        er.append("approved source path/hash malformed")
    all_lane_ids = {lane.get("id") for lane in cfg.get("lanes", [])}
    if all_lane_ids == set("ABCD"):
        for lane in cfg["lanes"]:
            lid = lane["id"]
            if (
                lane.get("brief") != f"lanes/{lid}.md"
                or cfg.get("lane_briefs", {}).get(lid) != lane["brief"]
            ):
                er.append(f"missing/changed lane brief pointer {lid}")
            intended = lane.get("authorized_repositories") or {}
            writable = set(intended.get("writable", []))
            readonly = set(intended.get("read_only", []))
            if (writable, readonly) != _ALLOW[lid] or intended.get(
                "unlisted_repositories"
            ) != "no_access":
                er.append(f"repository allowlist mismatch for lane {lid}")
            if writable & readonly:
                er.append(f"writable/read-only collision for lane {lid}")
            header = header_of(briefs.get(lid, ""))
            if header != intended:
                er.append(f"first-position repository_access header mismatch {lid}")
            if not lane.get("requires_current_mode") or "/coding-agent" not in (
                briefs.get(lid, "")
            ):
                er.append(f"current coding mode prerequisite not declared {lid}")
            if (
                "no cross-session" not in str(lane.get("reporting_contract", "")).lower()
                and "never" not in str(lane.get("reporting_contract", "")).lower()
            ):
                er.append(f"unsafe cross-session reporting {lid}")
            if not lane.get("outputs") or not lane.get("block_on"):
                er.append(f"missing output/denial contract {lid}")
    xs = snap.get("snapshots", [])
    if len(xs) != 3 or {f"{p.get('repo')}#{p.get('number')}" for p in xs} != _MERGES:
        er.append("PR snapshot is not exact approved merge subset")
    else:
        for p in xs:
            if not _SHA.fullmatch(str(p.get("head", ""))):
                er.append("malformed PR head snapshot")
            if p["number"] == 1030 and p.get("base") != "skills/l9-strategic-plan":
                er.append("Planner stack dependency lost in snapshot")
    if cfg.get("lanes", [{}])[0].get("writes") != []:
        er.append("Lane A violates current Cursor child .github write prohibition")
    if "BLOCKED_UNTIL" not in cfg.get("approval", {}).get("github_writer_status", ""):
        er.append("unresolved .github writer authorizer not fail-closed")
    if not all(
        x in cfg.get("role_release_policy", {})
        for x in ("CTO", "Architect", "Planner", "Meta_Planner", "Coding_Agent")
    ):
        er.append("five role dispositions not complete")
    if "J5" not in cfg.get("role_release_policy", {}).get("Coding_Agent", ""):
        er.append("Coding Agent confidentiality not dependent on enforced J5 gate")
    joins = cfg.get("workflow_joins") or []
    if {j.get("id") for j in joins} != {f"J{v}" for v in range(6)}:
        er.append("expected join census incomplete")
    if len(cfg.get("acceptance_gates", [])) != 8:
        er.append("G0-G7 gates incomplete")
    audit = cfg.get("audit") or {}
    if audit.get("status") != "PARTIAL_EXTERNAL_RUNTIME_UNVERIFIED":
        er.append("audit external limitation discarded")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(audit.get("kernel_sha256"))):
        er.append("kernel pin missing")
    return er


def check_collision(pr1: dict, pr2: dict, planned: dict) -> list[str]:
    e = []
    for n, pr in ((1011, pr1), (1030, pr2)):
        if (
            pr.get("repo") != "Quantum-L9/Cursor-Governance"
            or pr.get("number") != n
            or not _SHA.fullmatch(str(pr.get("head_sha", "")))
        ):
            e.append(f"PR {n} identity/head invalid")
    if planned.get("repo") != "Quantum-L9/Cursor-Governance" or not _SHA.fullmatch(
        str(planned.get("base_main_sha", ""))
    ):
        e.append("D target identity/main invalid")
    c = []
    for pr in (pr1, pr2):
        paths = pr.get("paths")
        if not isinstance(paths, list) or not paths or not all(_safe_path(x) for x in paths):
            e.append("missing/invalid PR path census")
        else:
            c += paths
    d = planned.get("paths")
    if not isinstance(d, list) or not d or not all(_safe_path(x) for x in d):
        e.append("missing/invalid D planned path census")
    elif len(set(d)) != len(d):
        e.append("duplicate D changed path")
    if not e:
        collision = sorted(set(c) & set(d))
        if collision:
            e.append("C/D same-file writer collision: " + ", ".join(collision))
        forbidden = (
            "tools/authority/produce_projection_bundle.py",
            "governance/planner-mode/MODE.yaml",
            "commands/planner.md",
        )
        if any(x in d for x in forbidden):
            e.append("D writes frozen C-owned Planner path")
    return e


def check_manifest(root: Path, strict: bool = True) -> list[str]:
    if not strict:
        return []
    p = root / "manifest.sha256"
    if not p.exists():
        return ["manifest missing"]
    lines = p.read_text().splitlines()
    expected = {str(x.relative_to(root)) for x in root.rglob("*") if x.is_file() and x != p}
    seen = set()
    errors = []
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not m:
            errors.append("invalid manifest line")
            continue
        digest, path = m.groups()
        if not _safe_path(path):
            errors.append("unsafe manifest path")
            continue
        if path in seen:
            errors.append("duplicate manifest path " + path)
        seen.add(path)
        f = root / path
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            errors.append("manifest byte mismatch " + path)
    if seen != expected:
        errors.append(
            "incomplete manifest inventory missing="
            + str(sorted(expected - seen))
            + " unexpected="
            + str(sorted(seen - expected))
        )
    return errors


def negative_tests(cfg: dict, snap: dict, approval: dict, briefs: dict) -> dict[str, bool]:
    """Synthetic known-bad campaigns MUST be rejected. Does not test host."""
    out = {}

    def case(label, mutate):
        c, s, a, b = (
            copy.deepcopy(cfg),
            copy.deepcopy(snap),
            copy.deepcopy(approval),
            copy.deepcopy(briefs),
        )
        mutate(c, s, a, b)
        out[label] = bool(_errors(c, s, a, b))

    case("unauthorized_merge", lambda c, s, a, b: c["merge_set"].append("Quantum-L9/.github#254"))
    case("duplicate_lane", lambda c, s, a, b: c["lanes"][0].__setitem__("id", "B"))
    case(
        "wrong_writable_repo",
        lambda c, s, a, b: c["lanes"][1]["authorized_repositories"]["writable"].append(
            "https://github.com/Quantum-L9/.github"
        ),
    )
    case(
        "missing_first_position_header",
        lambda c, s, a, b: b.__setitem__("D", b["D"].replace("```yaml", "", 1)),
    )
    case(
        "forbidden_github_worker_write",
        lambda c, s, a, b: c["lanes"][0]["authorized_repositories"]["writable"].append(
            "https://github.com/Quantum-L9/.github"
        ),
    )
    case(
        "forged_approved_digest",
        lambda c, s, a, b: a.__setitem__("subject_digest", "sha256:" + "0" * 64),
    )
    case(
        "unapproved_global_source",
        lambda c, s, a, b: c["constraints"].__setitem__(
            "no_new_global_domain_or_source_registry", False
        ),
    )
    case(
        "false_coding_privacy",
        lambda c, s, a, b: c["constraints"].__setitem__(
            "coding_agent_confidentiality_default", "PASS"
        ),
    )
    case(
        "allow_unapproved_new_merges",
        lambda c, s, a, b: c["approval"].__setitem__(
            "conditional_new_pr_merges", "automatically merge future heads"
        ),
    )
    case("lost_planner_parent", lambda c, s, a, b: s["snapshots"][2].__setitem__("base", "main"))
    case("delete_producer_join", lambda c, s, a, b: c["workflow_joins"].pop(2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--negative-controls", action="store_true")
    ap.add_argument("--collision-check", nargs=3, metavar=("PR1011", "PR1030", "PLANNED_D"))
    ap.add_argument("--skip-manifest", action="store_true")
    ns = ap.parse_args()
    if ns.collision_check:
        data = [json.loads(Path(p).read_text()) for p in ns.collision_check]
        errors = check_collision(*data)
        result = {
            "result": "PASS_LOCAL_COLLISION_CENSUS" if not errors else "FAIL",
            "errors": errors,
            "unverified_live_head_currentness": True,
        }
        print(json.dumps(result, indent=2))
        return 0 if not errors else 1
    cfg = yaml.safe_load((ROOT / "campaign.yaml").read_text())
    snap = json.loads((ROOT / "evidence/open_pr_snapshot.json").read_text())
    approval = json.loads((ROOT / "evidence/approved_v1_exact_subject_manifest.json").read_text())
    briefs = {a: (ROOT / f"lanes/{a}.md").read_text() for a in "ABCD"}
    errors = _errors(cfg, snap, approval, briefs)
    report = yaml.safe_load((ROOT / "ALIGNMENT_AUDIT.yaml").read_text())
    if (
        report.get("audit_status") != "PartiallySucceeded"
        or report.get("readiness_status") != "Unknown"
        or len(report.get("high_violations", [])) != 3
    ):
        errors.append("audit verdict or finding census inconsistent")
    if hashlib.sha256(
        (ROOT / "evidence/recursive_alignment_kernel_v1.0.md").read_bytes()
    ).hexdigest() != cfg["audit"]["kernel_sha256"].removeprefix("sha256:"):
        errors.append("kernel byte pin mismatch")
    if (ROOT / "evidence/target_predecessor_sha256.txt").read_text().split("  ")[0] != cfg["audit"][
        "predecessor_zip_sha256"
    ].removeprefix("sha256:"):
        errors.append("predecessor digest mismatch")
    for p in (
        "README.md",
        "CTO_LAUNCH.md",
        "RUNBOOK.md",
        "LANES.md",
        "GATES.md",
        "PR_MERGE_RUNBOOK.md",
        "SECURITY_AND_AUTHORITY.md",
        "EVIDENCE_COLLECTION.md",
        "PRODUCER_CONSUMER_HANDOFF.md",
        "NEGATIVE_CONTROLS.md",
    ):
        if not (ROOT / p).is_file():
            errors.append("missing " + p)
    errors += check_manifest(ROOT, not ns.skip_manifest)
    negatives = negative_tests(cfg, snap, approval, briefs) if ns.negative_controls else {}
    if negatives and not all(negatives.values()):
        errors.append("negative control was accepted")
    status = "PASS_LOCAL_STRUCTURE_ONLY" if not errors else "FAIL"
    result = {
        "result": status,
        "errors": errors,
        "files": len([x for x in ROOT.rglob("*") if x.is_file()]),
        "negative_controls": negatives,
        "negative_controls_rejected": sum(negatives.values()),
        "external_runtime_evidence": "UNRUN",
        "approved_subject_digest": approval.get("subject_digest"),
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
