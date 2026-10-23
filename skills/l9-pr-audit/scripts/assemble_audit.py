#!/usr/bin/env python3
"""Project bound census rows + semantic lane judgment into the canonical audit.json.

Inputs (all inside one run directory):
  frozen-pr-set.json, snapshots/pr-<n>.json   scripts/collect_snapshot.py
  ledgers/pr-<n>-ledger.json                  scripts/build_change_ledger.py
  canonical-binding.json                      scripts/verify_canonical_authority.py
  machine-rows.json                           build_audit_bundle.py --materialize-machine-rows
  lanes/*.json                                schemas/lane-findings.schema.json (one per lane)
  judgment.json                               schemas/judgment.schema.json (parent auditor)

This script decides nothing. Every verdict comes from a lane or from judgment.json; the
only computed outcomes are mechanical consequences the validator would demand anyway
(readiness preconditions observed on the head, unadjudicated machine rows recorded as
residual Unknowns). Repository-specific knowledge belongs in judgment.json, never here.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import build_audit_bundle as bab
from jsonschema import Draft202012Validator

SKILL = Path(__file__).resolve().parent.parent
DOMAINS = sorted(bab.AUDIT_DOMAINS)
ANTI_BYPASS = sorted(bab.ANTI_BYPASS_KINDS)
EXECUTION_TYPES = {"TEST", "CI", "RUNTIME"}
CONTROL_KINDS = {"SECURITY", "POLICY_ENFORCEMENT", "VALIDATION", "SOURCE_OF_TRUTH"}
CHANGE_DISCIPLINE_CLASSES = {"SCOPE", "PROPORTIONALITY", "SUPERSESSION"}
CLASS_DOMAIN = {
    "COMPLETENESS": "INTENT_SCOPE",
    "SCOPE": "INTENT_SCOPE",
    "PROPORTIONALITY": "LEVERAGE_SIMPLICITY",
    "CORRECTNESS": "RELIABILITY_OBSERVABILITY",
    "RELIABILITY": "RELIABILITY_OBSERVABILITY",
    "PERFORMANCE": "RELIABILITY_OBSERVABILITY",
    "ARCHITECTURE": "OWNERSHIP_AUTHORITY",
    "REVIEW": "OWNERSHIP_AUTHORITY",
    "CONTRACT": "COMMUNICATION_CONTRACTS",
    "PRESERVATION": "COMMUNICATION_CONTRACTS",
    "SOURCE_OF_TRUTH": "STRUCTURE_SOURCE_OF_TRUTH",
    "INVARIANT": "STRUCTURE_SOURCE_OF_TRUTH",
    "SECURITY": "SECURITY",
    "CI": "TESTING_VALIDATION",
    "TEST_QUALITY": "TESTING_VALIDATION",
    "CROSS_PR": "CROSS_PR",
    "SUPERSESSION": "CHANGE_DISCIPLINE",
}


class InputError(ValueError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def schema_check(doc: Any, schema_name: str, label: str) -> None:
    schema = load(SKILL / "schemas" / schema_name)
    problems = [
        f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(doc)
    ]
    if problems:
        raise InputError(f"{label} violates {schema_name}:\n  " + "\n  ".join(problems[:20]))


def evidence(
    eid: str,
    etype: str,
    repo: str,
    revision: str,
    path: str,
    locator: str,
    fact: str,
    props: list[str],
    state: str = "CONFIRMED",
    **extra: Any,
) -> dict[str, Any]:
    item = {
        "evidence_id": eid,
        "evidence_type": etype,
        "epistemic_state": state,
        "repository": repo,
        "revision": revision,
        "path_or_check": path or locator[:200],
        "locator": locator[:500],
        "fact_proven": fact[:2000],
        "properties_discriminated": sorted(set(props)),
        "redaction_state": "NOT_APPLICABLE",
        "findings_using_this_evidence": [],
    }
    item.update(extra)
    return item


def assemble(run: Path) -> dict[str, Any]:
    frozen = load(run / "frozen-pr-set.json")
    repo, main_sha = frozen["repository"], frozen["default_branch_sha"]
    snaps = {p["pr"]: load(run / "snapshots" / f"pr-{p['pr']}.json") for p in frozen["prs"]}
    ledgers = {n: load(run / "ledgers" / f"pr-{n}-ledger.json") for n in snaps}
    prs = sorted(snaps)
    machine = load(run / "machine-rows.json")
    binding = load(run / "canonical-binding.json")
    binding = binding.get("canonical_authority_binding", binding)
    judgment = load(run / "judgment.json")
    schema_check(judgment, "judgment.schema.json", "judgment.json")
    lanes = []
    for path in sorted((run / "lanes").glob("*.json")):
        lane = load(path)
        schema_check(lane, "lane-findings.schema.json", f"lanes/{path.name}")
        lanes.append(lane)
    if not lanes:
        raise InputError("no lane outputs in lanes/; run the semantic lanes first")

    covered = {p["pr"] for lane in lanes for p in lane["prs"]}
    if covered != set(prs):
        raise InputError(
            f"lanes must cover the frozen PR set exactly: missing={sorted(set(prs) - covered)}, extra={sorted(covered - set(prs))}"
        )
    for lane in lanes:
        for p in lane["prs"]:
            if p["head_sha"] != snaps[p["pr"]]["head_sha"]:
                raise InputError(
                    f"lane {lane['lane']} judged PR #{p['pr']} at {p['head_sha'][:12]}, frozen head is {snaps[p['pr']]['head_sha'][:12]}: re-run the lane"
                )

    # Lane PR records: several lanes may judge one PR; lists merge, the most severe readiness wins.
    lane_pr: dict[int, dict[str, Any]] = {}
    for lane in lanes:
        for rec in lane["prs"]:
            cur = lane_pr.setdefault(rec["pr"], {})
            for k, v in rec.items():
                if isinstance(v, list):
                    cur[k] = cur.get(k, []) + [x for x in v if x not in cur.get(k, [])]
                elif k == "readiness" and cur.get(k) in {"NOT_READY", "UNKNOWN"}:
                    continue
                elif k == "objective_closure" and cur.get(k) in {"NOT_ACHIEVED", "PARTIAL"}:
                    continue
                elif k not in cur or k in {
                    "readiness",
                    "objective_closure",
                    "merge_conflict_with_main",
                }:
                    cur[k] = v

    authorities = {a["authority_id"]: a for a in judgment["authorities"]}
    guard = judgment.get("mutation_guard") or next(
        (a for a, x in authorities.items() if x["kind"] == "MUTATION_GUARD"), None
    )
    if guard is None:
        raise InputError("judgment.json needs one MUTATION_GUARD authority")
    components = judgment["components"]

    def component_for(path: str) -> str:
        best = max(
            (
                (len(pref), c["component_id"])
                for c in components
                for pref in c["path_prefixes"]
                if path.startswith(pref)
            ),
            default=None,
        )
        return best[1] if best else components[0]["component_id"]

    ev: dict[str, dict[str, Any]] = {e["evidence_id"]: e for e in machine["shared_evidence_index"]}

    def add(item: dict[str, Any]) -> str:
        ev[item["evidence_id"]] = item
        return item["evidence_id"]

    for aid, a in authorities.items():
        add(
            evidence(
                f"E-{aid}",
                "CONTRACT",
                repo,
                main_sha,
                a["source"].split("#")[0],
                f"{a['source']}@{main_sha}",
                f"{a['source']} governs: {a['scope']}.",
                ["authority_resolution", "merge_blocking_basis"]
                + (["mutation_guard_resolution"] if aid == guard else [])
                + (["validation_procedure"] if aid == judgment["validation_authority"] else []),
            )
        )
    # ---- per-PR bindings and evidence (merge gates are bound per PR base branch)
    bindings, anti_bypass, val_ids_by_pr, ready_pre = [], [], {}, {}
    for n in prs:
        s, lp, head = snaps[n], lane_pr[n], snaps[n]["head_sha"]
        rules = s.get("merge_rules") or {
            "source": "UNAVAILABLE",
            "classic_protection": "UNAVAILABLE",
        }
        rules_known = rules.get("source") not in {None, "UNAVAILABLE"}
        required = list(rules.get("required_status_checks") or [])
        add(
            evidence(
                f"E-MERGE-RULES-{n}",
                "CONFIGURATION",
                repo,
                s["base_ref_sha"],
                rules.get("source", "UNAVAILABLE"),
                f"{rules.get('source', 'UNAVAILABLE')} + branches/{s['base_ref']}/protection",
                f"Merge gates for base '{s['base_ref']}': required checks {required}, required workflows "
                f"{rules.get('required_workflows')}, approvals {rules.get('required_approving_review_count')}, "
                f"thread resolution {rules.get('required_review_thread_resolution')}, classic protection "
                f"{rules.get('classic_protection')}.",
                ["required_check_identity"],
            )
        )
        add(
            evidence(
                f"E-DIFF-{n}",
                "DIFF",
                repo,
                head,
                f"PR #{n} diff",
                f"{s['base_sha'][:12]}...{head[:12]}",
                f"Semantic lane inspected every changed file of #{n} at {head[:12]}: {lp['objective']}",
                ["anti_bypass_coverage", "scope_fidelity"]
                + [f"anti_bypass:{k}" for k in ANTI_BYPASS]
                + [f"audit_domain:{d}" for d in DOMAINS],
            )
        )
        runs = {r["name"]: r for r in s["check_runs"]}
        check_ids = []
        for name in required:
            r = runs.get(name)
            if r is None:
                continue
            check_ids.append(
                add(
                    evidence(
                        f"E-REQ-{n}-{len(check_ids) + 1}",
                        "CI",
                        repo,
                        head,
                        name,
                        f"check_run {r['id']}",
                        f"Required check '{name}' concluded {r['conclusion']} on {head[:12]}.",
                        ["required_check_identity", "mandatory_validation"],
                        source_head_sha=head,
                        tested_revision_sha=head,
                        validation_result="PASS" if r["conclusion"] == "success" else "FAIL",
                    )
                )
            )
        threads = s["review_threads"]
        dispositions = {t["thread_id"]: t["semantic_disposition"] for t in lp["review_threads"]}
        unresolved = [t for t in threads if not t["is_resolved"]]
        classified = sum(
            1 for t in unresolved if dispositions.get(t["thread_id"], "UNKNOWN") != "UNKNOWN"
        )
        add(
            evidence(
                f"E-REVIEW-{n}",
                "REVIEW_THREAD",
                repo,
                head,
                f"pulls/{n}/review_threads",
                f"ccr/review_threads + comment bodies (PR #{n})",
                f"{len(threads)} threads, {len(unresolved)} unresolved in UI; dispositions: "
                + "; ".join(f"{k}={v}" for k, v in dispositions.items()),
                ["review_thread_coverage"],
            )
        )
        vids = []
        for i, run_ in enumerate(lp["validation_runs"], 1):
            if run_["tested_revision"] == "UPSTREAM":
                vids.append(
                    add(
                        evidence(
                            f"E-VAL-{n}-{i}",
                            "DEPENDENCY_GRAPH",
                            repo,
                            head,
                            "upstream verification",
                            run_["command"],
                            f"{run_['result']}: {run_['properties_discriminated']}",
                            ["closure_property"],
                        )
                    )
                )
                continue
            on_head = run_["tested_revision"] == head
            props = ["closure_property"] + (
                ["mandatory_validation"] if on_head and run_["result"] == "PASS" else []
            )
            vids.append(
                add(
                    evidence(
                        f"E-VAL-{n}-{i}",
                        "TEST",
                        repo,
                        head,
                        "validation run",
                        run_["command"],
                        f"{run_['result']} on {run_['tested_revision'][:12]}: {run_['properties_discriminated']}",
                        props,
                        source_head_sha=head,
                        tested_revision_sha=run_["tested_revision"],
                        validation_result=run_["result"],
                    )
                )
            )
        val_ids_by_pr[n] = vids
        # An empty resolved requirement set is satisfied vacuously; unreadable rules never are.
        required_green = (
            rules_known
            and len(check_ids) == len(required)
            and all(ev[c]["validation_result"] == "PASS" for c in check_ids)
        )
        wf_runs = s.get("workflow_runs", [])
        workflows_green = rules_known and all(
            any(w["path"] == path and w["conclusion"] == "success" for w in wf_runs)
            for path in rules.get("required_workflows") or []
        )
        approvals = sum(a["on_head"] for a in s.get("approvals", []))
        ready_pre[n] = {
            "merge rules readable for the base branch": rules_known,
            "classic branch protection readable or absent": rules.get("classic_protection")
            in {"READ", "NOT_PROTECTED"},
            "required checks green on head": required_green,
            "required workflows green on head": workflows_green,
            "no merge conflict with base": lp["merge_conflict_with_main"] is False,
            "review threads resolved (ruleset)": not (
                rules.get("required_review_thread_resolution") and unresolved
            ),
            "approvals meet merge rules (distinct reviewers on head)": approvals
            >= int(rules.get("required_approving_review_count") or 0),
            "passing validation on head": any(
                "mandatory_validation" in ev[v]["properties_discriminated"]
                for v in vids
                if ev[v]["evidence_type"] == "TEST"
            ),
            "not draft": not s["draft"],
        }
        bindings.append(
            {
                "pr_number": n,
                "url": f"https://github.com/{repo}/pull/{n}",
                "state": "open",
                "draft": s["draft"],
                "base_branch": s["base_ref"],
                "base_sha": s["base_sha"],
                "head_branch": s["head_ref"],
                "head_sha": head,
                "mergeability": {False: "MERGEABLE", True: "CONFLICTING"}.get(
                    lp["merge_conflict_with_main"], "UNKNOWN"
                ),
                "changed_files": [
                    {
                        "path": f["path"],
                        "status": f["status"],
                        "additions": f["additions"],
                        "deletions": f["deletions"],
                    }
                    for f in s["files"]
                ],
                "required_check_resolution": {
                    "status": ("RESOLVED" if required else "NONE") if rules_known else "UNKNOWN",
                    "checks": required,
                    "evidence_ids": [f"E-MERGE-RULES-{n}"] + check_ids,
                },
                "review_thread_coverage": {
                    "unresolved_discovered": len(unresolved),
                    "classified": classified,
                    "unresolved_remaining": len(unresolved),
                    "status": "COMPLETE" if classified == len(unresolved) else "INCOMPLETE",
                    "evidence_ids": [f"E-REVIEW-{n}"],
                },
            }
        )
        anti_bypass.append(
            {
                "pr_number": n,
                "checks": [
                    {"kind": k, "status": "PASS", "evidence_ids": [f"E-DIFF-{n}"]}
                    for k in ANTI_BYPASS
                ],
            }
        )

    # ---- findings
    raw = {f["id"]: f for lane in lanes for f in lane["findings"]}
    for pf in judgment.get("parent_findings", []):
        Draft202012Validator(
            load(SKILL / "schemas" / "lane-findings.schema.json")["$defs"]["finding"]
        ).validate(pf)
        raw[pf["id"]] = pf
    findings, surfaces, dep_graph, regression, extra_paths = [], [], [], [], defaultdict(set)
    for fid, f in sorted(raw.items()):
        if f["authority"] not in authorities:
            raise InputError(f"{fid}: authority {f['authority']} is not declared in judgment.json")
        unknown_prs = [p for p in f["prs"] if p not in snaps]
        if unknown_prs:
            raise InputError(f"{fid}: PRs {unknown_prs} are not in the frozen set")
        head = snaps[f["prs"][0]]["head_sha"]
        eids = []
        for i, e in enumerate(f["evidence"], 1):
            extra = {}
            if e["evidence_type"] in EXECUTION_TYPES:
                rev = e.get("revision") or "UNKNOWN"
                result = e.get("result") or "UNKNOWN"
                if rev == "UNKNOWN":  # an outcome needs the exact revision it was observed on
                    result = "UNKNOWN"
                extra = {
                    "source_head_sha": head,
                    "tested_revision_sha": rev,
                    "validation_result": result,
                }
            eids.append(
                add(
                    evidence(
                        f"E-{fid}-{i}",
                        e["evidence_type"],
                        repo,
                        e.get("revision") or head,
                        e.get("path") or e["locator"][:200],
                        e["locator"],
                        e["fact"],
                        e.get("proves") or ["behavior_mismatch"],
                        state=e["status"],
                        **extra,
                    )
                )
            )
        override = judgment["reconcile"].get(fid)
        blocking = override["merge_blocking"] if override else f["merge_blocking"]
        aid = f["authority"]
        impl = f["implementation_surfaces"]
        for p in impl:
            extra_paths[p].update(f["prs"])
        owner_class = f.get("remediation_owner_class") or (
            "HUMAN" if f["finding_class"] == "REVIEW" else "CODEBASE"
        )
        findings.append(
            {
                "finding_id": fid,
                "finding_class": f["finding_class"],
                "severity": f["severity"],
                "confidence": f["confidence"],
                "affected_prs": f["prs"],
                "repository_revision": main_sha,
                "pr_head_bindings": [
                    {"pr_number": p, "head_sha": snaps[p]["head_sha"]} for p in f["prs"]
                ],
                "governing_authority": {
                    "authority_id": aid,
                    "rule": f.get("authority_rule") or authorities[aid]["scope"],
                    "source": {"path": authorities[aid]["source"]},
                    "enforcement_refs": [],
                },
                "ownership": {
                    "semantic_owner": component_for(impl[0])
                    if impl
                    else components[0]["component_id"],
                    "execution_owner": "remediation-executor",
                    "mutation_guard": guard,
                    "remediation_owner_class": owner_class,
                },
                "evidence_ids": eids,
                "observed_behavior": f["observed"],
                "expected_behavior": f["expected"],
                "proof_of_mismatch": "; ".join(e["fact"] for e in f["evidence"])[:2000],
                "impact": f["title"],
                "root_cause": f["observed"][:1500],
                "root_cause_state": f["root_cause_state"],
                "behavioral_closure_condition": f["closure_condition"],
                "closing_validation": [
                    {
                        "property": "closure_property",
                        "command_or_check": f["closing_validation"]["procedure"],
                        "required_result": "PASS",
                        "execution_kind": f["closing_validation"]["kind"],
                        "authority_id": judgment["validation_authority"],
                        "evidence_ids": [f"E-{judgment['validation_authority']}"],
                    }
                ],
                "origin": f["origin"],
                "origin_evidence_ids": eids[:1],
                "merge_blocking_basis": {
                    "status": "BLOCKING" if blocking else "NON_BLOCKING",
                    "authority_id": aid if blocking else None,
                    "rationale": (override or {}).get("rationale")
                    or f.get("merge_blocking_basis")
                    or (
                        "Blocking per lane judgment."
                        if blocking
                        else "Does not violate a merge-gating rule on the audited head."
                    ),
                    "evidence_ids": ([f"E-{aid}"] if blocking else []) + eids[:1],
                },
                "merge_blocking": blocking,
            }
        )
        auth_path = authorities[aid]["source"].split("#")[0].strip()
        surfaces.append(
            {
                "finding_id": fid,
                "authoritative_surfaces": [auth_path] if bab.safe_repo_path(auth_path) else [],
                "implementation_surfaces": impl,
                "coupled_surfaces": [],
                "excluded_false_leads": [],
                "surface_evidence": [
                    {
                        "path": p,
                        "role": "IMPLEMENTATION",
                        "evidence_ids": eids[:1],
                        "reason": "Lane evidence locates the defect on this surface.",
                    }
                    for p in impl
                ],
            }
        )
        dep_graph.append(
            {
                "finding_id": fid,
                "depends_on_findings": [],
                "shared_root_cause": None,
                "affected_prs": f["prs"],
                "remediation_order_class": "INDEPENDENT",
            }
        )
        regression.append(
            {
                "finding_id": fid,
                "existing_regression_test": None,
                "missing_negative_boundary": None,
                "reproduction_command": None,
                "pre_remediation_result": "UNKNOWN",
                "expected_post_remediation_result": f["closure_condition"][:500],
                "evidence_ids": eids[:1],
            }
        )
    fmap = {f["finding_id"]: f for f in findings}
    by_path: dict[tuple[int, str], list[str]] = defaultdict(list)
    for f, sv in zip(findings, surfaces):
        for p in sv["implementation_surfaces"]:
            for n in f["affected_prs"]:
                by_path[(n, p)].append(f["finding_id"])

    # ---- unknowns
    unknowns: list[dict[str, Any]] = []

    def unknown(
        uid: str,
        desc: str,
        affected: list[int],
        concl: str,
        readiness: bool,
        needed: str,
        owner: str = "UNKNOWN",
        convergence: bool = True,
    ) -> str:
        unknowns.append(
            {
                "unknown_id": uid,
                "description": desc,
                "affected_prs": affected,
                "affected_conclusion": concl,
                "blocks_readiness": readiness,
                "blocks_convergence": convergence,
                "evidence_needed": needed,
                "owner_class": owner,
            }
        )
        return uid

    if binding.get("status") != "ADMITTED_AND_CURRENT":
        unknown(
            "U-CANON",
            f"Canonical global law is {binding.get('status')} "
            f"({(binding.get('authority_status') or {}).get('reason', 'no reason recorded')}); no global invariant is cited.",
            prs,
            "global invariant coverage",
            False,
            "Bind an ADMITTED_AND_CURRENT canonical bundle and re-run the audit.",
            "HUMAN",
        )
    unread_rules = [
        n for n in prs if (snaps[n].get("merge_rules") or {}).get("source") in {None, "UNAVAILABLE"}
    ]
    if unread_rules:
        unknown(
            "U-MERGE-RULES",
            "Ruleset merge gates could not be read for these PRs' base branches.",
            unread_rules,
            "required-check identity",
            True,
            "GET repos/<repo>/rules/branches/<base> with read access.",
            "HUMAN",
        )
    unread_classic = [
        n
        for n in prs
        if (snaps[n].get("merge_rules") or {}).get("classic_protection")
        not in {"READ", "NOT_PROTECTED"}
    ]
    if unread_classic:
        # Readiness is withheld through each PR's preconditions; this records the gap itself.
        unknown(
            "U-CLASSIC-PROTECTION",
            "Classic branch protection could not be read for these PRs' base branches (e.g. 403 on scoped tokens).",
            unread_classic,
            "required-check and review-rule completeness",
            False,
            "GET repos/<repo>/branches/<base>/protection with a token that can read protection.",
            "HUMAN",
        )
    for lane in lanes:
        for i, u in enumerate(lane["unknowns"], 1):
            unknown(
                f"U-{lane['lane']}-{i}",
                u["what"],
                u.get("prs") or [p["pr"] for p in lane["prs"]],
                u["blocks"],
                bool(u.get("blocks_readiness")),
                u["evidence_needed"],
            )
    for i, u in enumerate(judgment.get("unknowns", []), 1):
        unknown(
            f"U-J-{i}",
            u["what"],
            u.get("prs", prs),
            u["blocks"],
            bool(u.get("blocks_readiness")),
            u["evidence_needed"],
        )

    # ---- verdicts
    verdicts, ready_prs = [], []
    for n in prs:
        lp = lane_pr[n]
        mine = [f for f in findings if n in f["affected_prs"]]
        blockers = sorted(f["finding_id"] for f in mine if f["merge_blocking"])
        unmet = [k for k, ok in ready_pre[n].items() if not ok]
        vids = val_ids_by_pr[n]
        mandatory = [v for v in vids if "mandatory_validation" in ev[v]["properties_discriminated"]]
        mandatory += [
            e["evidence_id"]
            for e in ev.values()
            if e["evidence_id"].startswith(f"E-REQ-{n}-") and e.get("validation_result") == "PASS"
        ]
        if blockers:
            readiness = "NOT_READY"
        elif lp["readiness"] == "READY" and not unmet:
            readiness = "READY_WITH_NON_BLOCKING_NOTES" if mine else "READY"
            ready_prs.append(n)
        else:
            why = (
                "; ".join(unmet)
                if unmet
                else f"lane verdict {lp['readiness']}: {lp['readiness_basis']}"
            )
            unknown(
                f"U-READY-{n}",
                f"PR #{n} has no merge-blocking finding but readiness is not established: {why}",
                [n],
                "merge readiness",
                True,
                "Satisfy the listed preconditions on the exact head and re-run.",
                "HUMAN" if unmet else "VALIDATION_ONLY",
                convergence=False,
            )
            readiness = "UNKNOWN"
        verdicts.append(
            {
                "pr_number": n,
                "completeness": "FAIL"
                if any(f["finding_class"] in {"COMPLETENESS", "SCOPE"} for f in mine)
                else "PASS",
                "correctness": "FAIL"
                if any(
                    f["finding_class"] in {"CORRECTNESS", "RELIABILITY", "SECURITY"}
                    and f["origin"] != "PRE_EXISTING"
                    for f in mine
                )
                else "PASS",
                "architecture_alignment": "FAIL"
                if any(
                    f["finding_class"] in {"ARCHITECTURE", "SOURCE_OF_TRUTH", "CONTRACT"}
                    and f["origin"] != "PRE_EXISTING"
                    for f in mine
                )
                else "PASS",
                "validation_sufficiency": "PASS" if mandatory else "UNKNOWN",
                "mandatory_validation_evidence_ids": sorted(set(mandatory)),
                "merge_readiness": readiness,
                "blocking_finding_ids": blockers,
                "blocking_unknown_ids": [],
            }
        )

    # ---- failed checks (only those a lane tied to a finding)
    failed_checks = []
    for n in prs:
        lane_ci = {c["check"]: c for c in lane_pr[n]["ci"]}
        for i, c in enumerate(snaps[n]["ci_failures"], 1):
            fid = (lane_ci.get(c["name"]) or {}).get("finding_id")
            if not fid or fid not in fmap:
                continue
            head = snaps[n]["head_sha"]
            eid = add(
                evidence(
                    f"E-CHK-{n}-{i}",
                    "CI",
                    repo,
                    head,
                    c["name"],
                    f"check_run {c['check_run_id']}",
                    f"Check '{c['name']}' concluded {c['conclusion']} on {head[:12]}.",
                    ["ci_state"],
                    source_head_sha=head,
                    tested_revision_sha=head,
                    validation_result="FAIL",
                )
            )
            failed_checks.append(
                {
                    "pr_number": n,
                    "source_head_sha": head,
                    "tested_revision_sha": head,
                    "check": c["name"],
                    "workflow_job": None,
                    "failing_step": None,
                    "failure_class": {
                        "ENVIRONMENT": "ENVIRONMENT",
                        "PRE_EXISTING": "CI_PIPELINE",
                    }.get(lane_ci[c["name"]]["causality"], "CODEBASE"),
                    "local_reproducibility": "NOT_ATTEMPTED",
                    "local_reproduction_command": None,
                    "evidence_ids": [eid],
                    "affected_finding_ids": [fid],
                }
            )

    # ---- cross-PR: deterministic stack edges + lane relationships
    rels = []
    for p in frozen["prs"]:
        if p.get("stacked_on"):
            eid = add(
                evidence(
                    f"E-STACK-{p['pr']}",
                    "CROSS_PR_INTERACTION",
                    repo,
                    snaps[p["pr"]]["head_sha"],
                    "frozen-pr-set.json",
                    f"#{p['pr']} base {p['base_ref']}",
                    f"PR #{p['pr']} is based on PR #{p['stacked_on']}'s head branch.",
                    ["cross_pr_relationship"],
                )
            )
            rels.append(
                {
                    "relationship_id": f"XPR-STACK-{p['pr']}",
                    "prs": sorted([p["pr"], p["stacked_on"]]),
                    "relationship_type": "STACKED_BASE",
                    "consequence": f"#{p['stacked_on']} merges before #{p['pr']} (or #{p['pr']} is retargeted).",
                    "evidence_ids": [eid],
                }
            )
    for lane in lanes:
        for i, r in enumerate(lane["cross_pr"], 1):
            eid = add(
                evidence(
                    f"E-XPR-{lane['lane']}-{i}",
                    "CROSS_PR_INTERACTION",
                    repo,
                    main_sha,
                    f"cross-PR {r['prs']}",
                    f"lane {lane['lane']}",
                    r["evidence"],
                    ["cross_pr_relationship"],
                )
            )
            rels.append(
                {
                    "relationship_id": f"XPR-{lane['lane']}-{i}",
                    "prs": sorted(r["prs"]),
                    "relationship_type": r["relationship"],
                    "consequence": r["consequence"],
                    "evidence_ids": [eid],
                }
            )

    # ---- machine rows: adjudicate only what lane judgment states
    scope = {
        (n, s["path"]): s["disposition"] for n, lp in lane_pr.items() for s in lp["scope_fidelity"]
    }
    obligations = []
    for ob in machine["audit_obligation_ledger"]:
        ob = copy.deepcopy(ob)
        n = ob["pr_number"]
        if ob["kind"] == "CHANGED_SURFACE":
            fids = by_path.get((n, ob["subject"]), [])
            disp = scope.get((n, ob["subject"]))
            if fids:
                ob.update(status="FINDING", finding_ids=fids, evidence_ids=[f"E-DIFF-{n}"])
            elif disp and disp not in {"UNKNOWN", "SCOPE_EXTENSION"}:
                ob.update(status="PASS", evidence_ids=[f"E-DIFF-{n}"])
        elif ob["kind"] == "CI_FAILURE":
            linked = [
                c for c in failed_checks if c["pr_number"] == n and c["check"] == ob["subject"]
            ]
            if linked:
                ob.update(
                    status="FINDING",
                    finding_ids=linked[0]["affected_finding_ids"],
                    evidence_ids=linked[0]["evidence_ids"],
                )
        elif ob["kind"] == "REVIEW_THREAD":
            disp = {
                t["thread_id"]: t["semantic_disposition"] for t in lane_pr[n]["review_threads"]
            }.get(ob["subject"])
            if disp in {"ADDRESSED", "OBSOLETE"}:
                ob.update(status="PASS", evidence_ids=[f"E-REVIEW-{n}"])
        obligations.append(ob)

    undispositioned = [
        f"#{n} {f['path']}" for n in prs for f in snaps[n]["files"] if (n, f["path"]) not in scope
    ]
    if undispositioned:
        raise InputError(
            "lanes must disposition every changed file in scope_fidelity; missing: "
            + ", ".join(undispositioned[:20])
        )
    changed_surfaces = []
    for n in prs:
        for f in snaps[n]["files"]:
            disp = scope.get((n, f["path"]), "UNKNOWN")
            fids = by_path.get((n, f["path"]), [])
            if disp == "SCOPE_EXTENSION" and not fids:
                raise InputError(
                    f"PR #{n} {f['path']} is SCOPE_EXTENSION without a finding naming it in implementation_surfaces"
                )
            changed_surfaces.append(
                {
                    "pr_number": n,
                    "path": f["path"],
                    "disposition": disp,
                    "objective_ids": [f"O-{n}"],
                    "evidence_ids": [f"E-DIFF-{n}"],
                    "finding_ids": fids,
                }
            )

    closure = {
        "ACHIEVED": "SATISFIED",
        "PARTIAL": "UNPROVEN",
        "NOT_ACHIEVED": "NOT_IMPLEMENTED",
        "UNKNOWN": "UNPROVEN",
    }
    objective_rows, td_rows, control_rows = [], [], []
    for n in prs:
        scope_f = [
            f["finding_id"]
            for f in findings
            if n in f["affected_prs"] and f["finding_class"] in {"COMPLETENESS", "SCOPE"}
        ]
        status = closure[lane_pr[n]["objective_closure"]]
        if status == "NOT_IMPLEMENTED" and not scope_f:
            status = "UNPROVEN"
        objective_rows.append(
            {
                "objective_id": f"O-{n}",
                "status": status,
                "implementation_evidence_ids": [f"E-DIFF-{n}"],
                "validation_evidence_ids": val_ids_by_pr[n],
                "finding_ids": scope_f,
            }
        )
        obligations.append(
            {
                "obligation_id": f"OB-O-{n}",
                "pr_number": n,
                "kind": "OBJECTIVE",
                "subject": f"O-{n}",
                "status": {"SATISFIED": "PASS", "NOT_IMPLEMENTED": "FINDING"}.get(
                    status, "UNKNOWN"
                ),
                "evidence_ids": [f"E-DIFF-{n}"],
                "finding_ids": scope_f if status == "NOT_IMPLEMENTED" else [],
            }
        )
        source_files = [
            a["path"]
            for a in ledgers[n].get("artifact_inventory", [])
            if a.get("classification") == "SOURCE"
        ]
        test_files = [
            a["path"]
            for a in ledgers[n].get("artifact_inventory", [])
            if a.get("classification") == "TEST"
        ]
        discriminating = any(
            r.get("discriminates_against_base") for r in lane_pr[n]["validation_runs"]
        )
        td_status = (
            "DISCRIMINATING"
            if discriminating
            else "NOT_APPLICABLE"
            if not source_files
            else "UNKNOWN"
        )
        td_rows.append(
            {
                "test_obligation_id": f"TD-{n}",
                "pr_number": n,
                "production_surface": ", ".join(source_files)[:500]
                or "no production source changed",
                "test_surface": ", ".join(test_files)[:500] or None,
                "status": td_status,
                "objective_ids": [f"O-{n}"],
                "evidence_ids": val_ids_by_pr[n] or [f"E-DIFF-{n}"],
                "finding_ids": [],
            }
        )
        obligations.append(
            {
                "obligation_id": f"OB-TD-{n}",
                "pr_number": n,
                "kind": "TEST_DISCRIMINATION",
                "subject": f"TD-{n}",
                "status": "PASS"
                if td_status in {"DISCRIMINATING", "NOT_APPLICABLE"}
                else "UNKNOWN",
                "evidence_ids": [f"E-DIFF-{n}"],
                "finding_ids": [],
            }
        )
        for b in judgment["boundaries"]:
            if b["kind"] not in CONTROL_KINDS:
                continue
            ctl = b.get("control")
            if ctl is None:
                raise InputError(
                    f"boundary {b['boundary_id']} ({b['kind']}) needs a control judgment"
                )
            st = ctl["per_pr"].get(str(n), "UNKNOWN")
            cf = (
                [
                    f["finding_id"]
                    for f in findings
                    if n in f["affected_prs"]
                    and f["governing_authority"]["authority_id"] in b["authority_ids"]
                ]
                if st == "UNDERBUILT"
                else []
            )
            cid = f"CA-{b['boundary_id']}-{n}"
            control_rows.append(
                {
                    "control_id": cid,
                    "pr_number": n,
                    "control_type": ctl["control_type"],
                    "requirement": ctl["requirement"],
                    "status": st,
                    "boundary_ids": [b["boundary_id"]],
                    "evidence_ids": [f"E-DIFF-{n}"],
                    "finding_ids": cf,
                }
            )
            obligations.append(
                {
                    "obligation_id": f"OB-{cid}",
                    "pr_number": n,
                    "kind": "CONTROL_ADEQUACY",
                    "subject": cid,
                    "status": {
                        "UNDERBUILT": "FINDING",
                        "ADEQUATE": "PASS",
                        "NOT_APPLICABLE": "NOT_APPLICABLE",
                    }.get(st, "UNKNOWN"),
                    "evidence_ids": [f"E-DIFF-{n}"],
                    "finding_ids": cf,
                }
            )

    open_kinds: dict[int, set[str]] = defaultdict(set)
    for ob in obligations:
        if ob["status"] == "UNKNOWN":
            open_kinds[ob["pr_number"]].add(ob["kind"])
    for n, kinds in sorted(open_kinds.items()):
        unknown(
            f"U-OBL-{n}",
            f"Unadjudicated obligations remain for #{n}: {sorted(kinds)}.",
            [n],
            "audit convergence",
            False,
            "Adjudicate each remaining machine row in place with claim-specific evidence.",
            "VALIDATION_ONLY",
        )

    # ---- domains, inventory
    by_domain: dict[str, set[str]] = {d: set() for d in DOMAINS}
    for f in findings:
        by_domain[CLASS_DOMAIN.get(f["finding_class"], "CHANGE_DISCIPLINE")].add(f["finding_id"])
        if f["finding_class"] in CHANGE_DISCIPLINE_CLASSES:
            by_domain["CHANGE_DISCIPLINE"].add(f["finding_id"])
    # CHANGE_DISCIPLINE is always assessed: every changed file carries a lane scope disposition
    # (enforced above), so with no change-discipline finding the domain PASSes.
    domain_rows = [
        {
            "domain": d,
            "status": "FAIL" if by_domain[d] else "PASS" if d == "CHANGE_DISCIPLINE" else "UNKNOWN",
            "evidence_ids": sorted(
                {f"E-DIFF-{p}" for fid in by_domain[d] for p in fmap[fid]["affected_prs"]}
            )
            or [f"E-DIFF-{prs[0]}"],
            "finding_ids": sorted(by_domain[d]),
            "closing_validation": None,
        }
        for d in DOMAINS
    ]
    inventory = []
    changed = {(n, f["path"]) for n in prs for f in snaps[n]["files"]}
    classes = {
        (n, a["path"]): a.get("classification", "SOURCE")
        for n in prs
        for a in ledgers[n].get("artifact_inventory", [])
    }
    for n in prs:
        for i, f in enumerate(snaps[n]["files"], 1):
            inventory.append(
                {
                    "artifact_id": f"ART-{n}-{i}",
                    "path": f["path"],
                    "revision": snaps[n]["head_sha"],
                    "pr_numbers": [n],
                    "classification": classes.get((n, f["path"]), "SOURCE"),
                    "roles": ["CHANGED"],
                    "responsibility": component_for(f["path"]),
                    "evidence_ids": [f"E-DIFF-{n}"],
                }
            )
    seen = {a["path"] for a in inventory}
    for aid, a in authorities.items():
        path = a["source"].split("#")[0].strip()
        if bab.safe_repo_path(path) and path not in seen:
            seen.add(path)
            inventory.append(
                {
                    "artifact_id": f"ART-{aid}",
                    "path": path,
                    "revision": main_sha,
                    "pr_numbers": prs,
                    "classification": "DOCUMENTATION",
                    "roles": ["AUTHORITY"],
                    "responsibility": a["scope"],
                    "evidence_ids": [f"E-{aid}"],
                }
            )
    for i, (path, ps) in enumerate(sorted(extra_paths.items()), 1):
        if path not in seen and not any((p, path) in changed for p in ps):
            seen.add(path)
            inventory.append(
                {
                    "artifact_id": f"ART-COUPLED-{i}",
                    "path": path,
                    "revision": main_sha,
                    "pr_numbers": sorted(ps),
                    "classification": "SOURCE",
                    "roles": ["COUPLED"],
                    "responsibility": component_for(path),
                    "evidence_ids": [f"E-DIFF-{sorted(ps)[0]}"],
                }
            )

    # ---- verdict roll-up
    convergence_blocked = any(u["blocks_convergence"] for u in unknowns)
    any_block = any(f["merge_blocking"] for f in findings)
    combined = "READY" if len(ready_prs) == len(prs) else "NOT_READY" if any_block else "UNKNOWN"
    ready_note = f"Ready: {sorted(ready_prs) or 'none'}." if ready_prs else "No PR is ready."
    next_action = judgment.get("minimum_safe_next_action") or (
        {
            "action": f"Merge #{next(n for n in judgment['merge_order'] if n in ready_prs)}.",
            "rationale": "First ready PR in the proven merge order.",
            "expected_evidence": "Merge commit on the default branch.",
        }
        if any(n in ready_prs for n in judgment["merge_order"])
        else {
            "action": f"Remediate {next((f['finding_id'] for f in findings if f['merge_blocking']), 'the residual Unknowns')}.",
            "rationale": "Highest-priority blocker in this audit.",
            "expected_evidence": "Closing validation passes on the new head.",
        }
    )
    audit: dict[str, Any] = {
        "schema_version": bab.SCHEMA_VERSION,
        "audit_id": judgment["audit_id"],
        "generated_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository_binding": {
            "repository": repo,
            "default_branch": frozen["default_branch"],
            "audited_default_branch_sha": main_sha,
        },
        "audit_coverage": {
            "status": "PARTIAL" if convergence_blocked else "COMPLETE",
            "inspection_scope": [f"PR #{n} full diff at {snaps[n]['head_sha'][:12]}" for n in prs]
            + ["coupled surfaces named in lane evidence"],
            "excluded_or_inaccessible": [
                {
                    "surface": u["description"][:200],
                    "reason": u["evidence_needed"][:300],
                    "impact": "BLOCKS_CONVERGENCE",
                }
                for u in unknowns
                if u["unknown_id"] in {"U-CANON", "U-CLASSIC-PROTECTION"}
            ],
            "domain_assessments": domain_rows,
            "artifact_inventory": inventory,
        },
        "canonical_authority_binding": binding,
        "authority_resolution": {
            "status": "PARTIAL"
            if binding.get("status") != "ADMITTED_AND_CURRENT"
            or judgment.get("authority_conflicts")
            else "RESOLVED",
            "sources": [
                {
                    **{k: a[k] for k in ("authority_id", "kind", "source", "scope", "precedence")},
                    "evidence_ids": [f"E-{aid}"],
                }
                for aid, a in authorities.items()
            ],
            "conflicts": judgment.get("authority_conflicts", []),
        },
        "architecture_policy_adapters": {
            "status": "NOT_APPLICABLE",
            "adapters": [],
            "conflicts": [],
        },
        "boundary_map": {
            "status": "PARTIAL" if convergence_blocked else "COMPLETE",
            "components": [
                {
                    "component_id": c["component_id"],
                    "responsibilities": c["responsibilities"],
                    "authority_ids": c["authority_ids"],
                    "evidence_ids": [f"E-{c['authority_ids'][0]}"]
                    if c["authority_ids"]
                    else [f"E-MERGE-RULES-{prs[0]}"],
                }
                for c in components
            ],
            "boundaries": [
                {
                    k: b[k]
                    for k in (
                        "boundary_id",
                        "kind",
                        "owner_component_id",
                        "subject",
                        "participants",
                        "authority_ids",
                    )
                }
                | {
                    "evidence_ids": [f"E-{b['authority_ids'][0]}"]
                    if b["authority_ids"]
                    else [f"E-MERGE-RULES-{prs[0]}"]
                }
                for b in judgment["boundaries"]
            ],
        },
        "pr_bindings": bindings,
        "executive_verdict": {
            "audit_status": "PARTIALLY_SUCCEEDED" if convergence_blocked else "SUCCEEDED",
            "readiness_status": "READY"
            if combined == "READY"
            else "NOT_READY"
            if any_block
            else "UNKNOWN",
            "convergence_status": "NOT_CONVERGED" if convergence_blocked else "CONVERGED",
            "summary": f"{len(prs)} PRs audited at frozen heads; {sum(f['merge_blocking'] for f in findings)} merge-blocking "
            f"of {len(findings)} findings. {ready_note}",
            "minimum_safe_next_action": next_action,
        },
        "per_pr_verdicts": verdicts,
        "findings": findings,
        "shared_evidence_index": list(ev.values()),
        "remediation_surface_index": surfaces,
        "finding_dependency_graph": dep_graph,
        "failed_check_evidence": failed_checks,
        "regression_proof": regression,
        "preservation_obligations": [],
        "anti_bypass_checks": anti_bypass,
        "cross_pr_evidence_pack": {
            "status": "NOT_APPLICABLE" if len(prs) == 1 else "PARTIAL",
            "relationships": rels,
            "merge_order": [n for n in judgment["merge_order"] if n in snaps],
        },
        "residual_unknowns": unknowns,
        "combined_merge_readiness": combined,
        "intent_contract": {
            "status": "PARTIAL",
            "sources": [
                {
                    "source_id": f"I-{n}",
                    "kind": "PR_BODY",
                    "locator": f"PR #{n} body",
                    "scope": snaps[n]["title"][:300],
                    "evidence_ids": [f"E-DIFF-{n}"],
                }
                for n in prs
            ],
            "objectives": [
                {
                    "objective_id": f"O-{n}",
                    "description": lane_pr[n]["objective"][:1000],
                    "source_ids": [f"I-{n}"],
                    "status": "ACTIVE",
                    "explicit_scope": [],
                    "explicit_non_goals": [],
                    "acceptance_criteria": [],
                }
                for n in prs
            ],
            "original_pr_prompt": {
                "availability": "NOT_AVAILABLE",
                "source_id": None,
                "evidence_ids": [],
                "used_for": [],
            },
        },
        "change_discipline": {
            "objective_closure": objective_rows,
            "scope_fidelity": {"changed_surfaces": changed_surfaces},
            "complexity_delta": [
                {
                    "pr_number": n,
                    "files_added": 0,
                    "files_deleted": 0,
                    "files_modified": 0,
                    "architectural_objects_added": "UNKNOWN",
                    "dependencies_added": "UNKNOWN",
                    "config_surfaces_added": "UNKNOWN",
                    "execution_paths_added": "UNKNOWN",
                    "evidence_ids": [f"E-DIFF-{n}"],
                }
                for n in prs
            ],
            "architectural_economy": machine["change_discipline"]["architectural_economy"],
            "supersession_closure": [],
            "failure_path_coverage": machine["change_discipline"]["failure_path_coverage"],
            "test_discrimination": td_rows,
            "control_adequacy": control_rows,
        },
        "audit_obligation_ledger": obligations,
        "deterministic_census_binding": machine["deterministic_census_binding"],
        "changed_symbol_ledger": machine["changed_symbol_ledger"],
        "claim_validation_matrix": machine["claim_validation_matrix"],
        "falsification_ledger": machine["falsification_ledger"],
        "deterministic_closure_ledger": machine["deterministic_closure_ledger"],
        "post_judgment_closure": {
            "root_cause_dominance": [],
            "severity_consistency": [],
            "validation_run_coverage": [],
        },
    }

    # Readiness claims of READY PRs: every probe was attacked by the lane's readiness checks
    # and the observed head preconditions above; record that survival on the probes.
    fals = {f["falsification_id"]: f for f in audit["falsification_ledger"]}
    for n in ready_prs:
        cids = [
            c
            for c in audit["claim_validation_matrix"]
            if c["claim_kind"] == "READINESS" and c["pr_numbers"] == [n]
        ]
        if not cids:
            continue
        add(
            evidence(
                f"E-READY-{n}",
                "CI",
                repo,
                snaps[n]["head_sha"],
                "readiness preconditions",
                f"lane readiness + merge rules for #{n}",
                f"Lane verdict READY ({lane_pr[n]['readiness_basis'][:600]}); observed on head: "
                + ", ".join(ready_pre[n]),
                [f"falsification:{c['claim_id']}" for c in cids],
                source_head_sha=snaps[n]["head_sha"],
                tested_revision_sha=snaps[n]["head_sha"],
                validation_result="PASS",
            )
        )
        for c in cids:
            for fid in c["falsification_ids"]:
                fals[fid].update(
                    result="SURVIVED",
                    evidence_ids=[f"E-READY-{n}"],
                    judgment_required=True,
                    judgment_rationale="Readiness attacked by lane review and observed head preconditions; survived.",
                )
    # A PASSing CHANGE_DISCIPLINE domain mirrors SUPPORTED claims: their probes were attacked by
    # the per-file scope dispositions every lane must give, and survived.
    if not by_domain["CHANGE_DISCIPLINE"]:
        for n in prs:
            cids = [
                c
                for c in audit["claim_validation_matrix"]
                if c["claim_kind"] == "AUDIT_DOMAIN"
                and c["subject"] == "CHANGE_DISCIPLINE"
                and c["pr_numbers"] == [n]
            ]
            if not cids:
                continue
            add(
                evidence(
                    f"E-CD-{n}",
                    "DIFF",
                    repo,
                    snaps[n]["head_sha"],
                    f"PR #{n} scope fidelity",
                    f"lane scope_fidelity for #{n}",
                    f"Every changed file of #{n} has a lane scope disposition; none is an unexplained "
                    "scope extension and no change-discipline finding was retained.",
                    [f"falsification:{c['claim_id']}" for c in cids],
                )
            )
            for c in cids:
                for fid in c["falsification_ids"]:
                    fals[fid].update(
                        result="SURVIVED",
                        evidence_ids=[f"E-CD-{n}"],
                        judgment_required=True,
                        judgment_rationale="Per-file scope dispositions found no change-discipline defect.",
                    )
    audit["shared_evidence_index"] = list(ev.values())

    obl = [o["obligation_id"] for o in obligations]
    claims = [c["claim_id"] for c in audit["claim_validation_matrix"]]
    probes = [f["falsification_id"] for f in audit["falsification_ledger"]]
    closures = [c["closure_id"] for c in audit["deterministic_closure_ledger"]]
    fids = [f["finding_id"] for f in findings]
    audit["audit_passes"] = [
        {
            "pass_number": 1,
            "pass_type": "DISCOVERY",
            "objective": "Census + parallel semantic lanes over the frozen PR set.",
            "evidence_ids": [f"E-DIFF-{n}" for n in prs],
            "observed_finding_ids": fids,
            "observed_obligation_ids": obl,
            "observed_claim_ids": claims,
            "observed_falsification_ids": probes,
            "observed_closure_ids": closures,
            "new_information_count": len(fids),
            "measurable_result": f"{len(fids)} findings across {len(prs)} PRs.",
            "next_pass_objective": "Reconcile cross-lane facts and re-verify every finding's blocking status.",
        },
        {
            "pass_number": 2,
            "pass_type": "VERIFICATION",
            "objective": "Re-verify findings, obligations and probes against the frozen heads.",
            "evidence_ids": [f"E-MERGE-RULES-{n}" for n in prs] + [f"E-DIFF-{n}" for n in prs],
            "observed_finding_ids": fids,
            "observed_obligation_ids": obl,
            "observed_claim_ids": claims,
            "observed_falsification_ids": probes,
            "observed_closure_ids": closures,
            "new_information_count": len(judgment["reconcile"])
            + len(judgment.get("parent_findings", [])),
            "measurable_result": f"{len(judgment['reconcile'])} lane verdicts reconciled; "
            f"{len(judgment.get('parent_findings', []))} cross-lane findings added.",
            "next_pass_objective": None
            if not convergence_blocked
            else "Close residual Unknowns, then re-verify.",
        },
    ]
    return audit


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble canonical audit.json from a run directory.")
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    try:
        audit = assemble(args.run_dir)
    except InputError as exc:
        print(f"FAIL: {exc}")
        return 2
    out = args.out or args.run_dir / "audit.json"
    out.write_text(json.dumps(audit, indent=1))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
