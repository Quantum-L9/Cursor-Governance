#!/usr/bin/env python3
"""Read-only static validator for the proposed canonical-law revision runbook.

It validates the package graph and append guards. With --repo, it additionally
verifies the source repository and tracked blob identities WITHOUT editing it.
A PASS never proves a future patch, human authorization, full CI, or deployment.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("BLOCKED: install PyYAML to validate the YAML input")


class Invalid(ValueError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise Invalid(message)


def unique(items: list[dict], name: str) -> set[str]:
    result = [z.get("id") for z in items]
    check(all(isinstance(z, str) and z.strip() for z in result), f"{name}: an id is empty")
    check(len(result) == len(set(result)), f"{name}: duplicate ids")
    return set(result)


def validate(d: dict) -> dict:
    check(
        isinstance(d, dict) and d.get("schema") == "l9.canonical-law-revision-runbook/proposal-v1",
        "wrong artifact schema",
    )
    check(d.get("revision") == "2.0.0", "not the recursively aligned revision 2.0.0")
    check(
        "NOT_APPLIED" in d.get("status", ""), "artifact is incorrectly claiming an applied policy"
    )
    s = d["subject"]
    check(
        re.fullmatch(r"[0-9a-f]{40}", s["frozen_commit"]) is not None, "not a frozen git revision"
    )
    check(
        re.fullmatch(r"[0-9a-f]{40}", s["law_git_blob_sha1"]) is not None, "law blob hash malformed"
    )
    check(
        s["law_last_content_line"] == 1848 and s["law_total_split_lines"] == 1849,
        "law baseline line coordinates moved",
    )
    check(s["proposed_application_requires_repin"] is True, "missing live re-pin gate")

    app = d["canonical_append"]
    check(
        app["operation"] == "APPEND_ONLY_EXACT" and app["must_not_change_existing_bytes"] is True,
        "law rewrite is forbidden",
    )
    check(
        app["expected_git_blob_sha1"] == s["law_git_blob_sha1"],
        "law blob guard disagrees with subject",
    )
    check(
        app["expected_last_nonempty_line_number"] == s["law_last_content_line"],
        "last line anchor mismatch",
    )
    check(
        app["expected_last_nonempty_line_exact"] == s["law_last_content_exact"],
        "last line text anchor mismatch",
    )
    payload = app["payload"]
    check(
        payload.startswith("\n<!-- CANONICAL_LAW_CURRENT_CONSUMER_CLOSURE_20261103_V2 -->\n"),
        "payload start is not append only or marker absent",
    )
    check(payload.endswith("\n"), "append payload must end in newline")
    raw = payload.splitlines()
    begin = s["law_last_content_line"] + 1
    anchors = {
        "marker": None,
        "section_6_2_17": None,
        "section_6_2_18": None,
        "section_6_2_19": None,
    }
    for i, line in enumerate(raw):
        if line.startswith("<!-- CANONICAL_LAW_CURRENT_CONSUMER_CLOSURE_20261103_V2 -->"):
            check(anchors["marker"] is None, "duplicate law marker")
            anchors["marker"] = begin + i
        match = re.match(r"^## (6\.2\.1[789])\b", line)
        if match:
            key = "section_" + match.group(1).replace(".", "_")
            check(anchors[key] is None, "duplicate law heading " + key)
            anchors[key] = begin + i
    check(
        all(v is not None for v in anchors.values()),
        "law append is missing its three numbered clauses",
    )
    anchors["result_last_content_line"] = begin + len(raw) - 1
    for key, value in anchors.items():
        check(
            app["proposed_post_append_lines"].get(key) == value, f"projected {key} line misaligned"
        )
    for needle in (
        "original PR",
        "UNKNOWN",
        "rename",
        "local",
        "Semgrep",
        "gitleaks",
        "pre-commit",
        "UPSTREAM_BLOCKED",
        "Infisical",
        "merge-authority",
    ):
        check(needle in payload, "missing material law clause: " + needle)

    law_ids = unique(d["canonical_law_line_dispositions"], "law dispositions")
    finding_ids = unique(d["findings"], "findings")
    change_ids = unique(d["downstream_changes"], "downstream changes")
    test_ids = unique(d["validation_matrix"], "verification cases")
    check(
        len(law_ids) >= 30 and len(change_ids) >= 45 and len(test_ids) >= 35,
        "coverage census shrank",
    )
    check(len(set(d["new_reference_resolution"])) >= 10, "new law-reference graph incomplete")
    for item in d["canonical_law_line_dispositions"]:
        check(
            item["new_reference"] in d["new_reference_resolution"],
            "unknown law new_reference " + item["id"],
        )
        check(
            item["operation"] in {"RETAIN_HISTORY", "KEEP_ACTIVE", "KEEP_DORMANT_WHILE_DISABLED"},
            "non-additive law action " + item["id"],
        )
        for span in item["existing_lines"].split(","):
            match = re.fullmatch(r"([0-9]+)(?:-([0-9]+))?", span.strip())
            check(match is not None, "invalid law line range " + item["id"])
            a, b = int(match.group(1)), int(match.group(2) or match.group(1))
            check(
                1 <= a <= b <= s["law_last_content_line"],
                "law line range outside frozen prefix: " + item["id"],
            )
    check(
        next(item for item in d["canonical_law_line_dispositions"] if item["id"] == "L16")[
            "operation"
        ]
        == "RETAIN_HISTORY",
        "superseded pr-check incorrectly marked live",
    )
    changes = {v["id"]: v for v in d["downstream_changes"]}
    paths = [v["path"] for v in changes.values()]
    check(len(paths) == len(set(paths)), "duplicate downstream edit path (D29/D33 must be folded)")
    check("D33" not in changes, "duplicate D33 action remains")
    for item in changes.values():
        check(item.get("finding_ids"), "downstream action lacks finding id: " + item["id"])
        check(
            set(item["finding_ids"]) <= finding_ids,
            "downstream action has an unknown finding: " + item["id"],
        )
        check(item.get("operation"), "missing operation: " + item["id"])
        check(
            item.get("required_code_delta")
            or item.get("reason")
            or item.get("amendment_id")
            or item.get("payload")
            or (item.get("operation") == "REGENERATE_FROM_SOURCE" and item.get("never_hand_edit")),
            "no operation rationale or delta: " + item["id"],
        )
        if item["operation"] in {
            "EXACT_REPLACE",
            "PROTECTED_ROOT_REPLACE_AFTER_OWNER_AUTH",
            "PROTECTED_ROOT_REMOVE_AFTER_OWNER_AUTH",
            "EXACT_REMOVE_MANAGED_IGNORE_LINES",
        }:
            check(
                item.get("expected_blob_sha1")
                and (
                    item.get("exact_before")
                    or item.get("expected_source_fragment")
                    or item.get("exact_before_lines")
                ),
                "unsafe unguarded exact edit: " + item["id"],
            )
    all_covered = {fid for v in changes.values() for fid in v["finding_ids"]}
    check(
        finding_ids <= all_covered, "unowned finding(s): " + str(sorted(finding_ids - all_covered))
    )
    for id_, path in [
        ("D41", ".pre-commit-config.yaml"),
        ("D42", ".semgrepignore"),
        ("D43", ".gitleaks.toml"),
    ]:
        check(changes[id_]["path"] == path, "missing scanner owner " + id_)
    check(
        changes["D03"]["operation"] == "VERIFY_WRITE_VS_PUBLISH_DISTINCTION",
        "worker local-write grant incorrectly changed",
    )
    check(
        changes["D07"]["operation"] == "CENSUS_THEN_CONDITIONAL_OWNER_RETIREMENT",
        "PE entrypoint retirement is not consumer-censused",
    )
    check(
        changes["D14"]["operation"] == "UPDATE_HAND_AUTHORED_COMMENTS_PRESERVE_GENERATED_OVERRIDES",
        "generated Claude settings not owned at field level",
    )
    for id_ in ("D41", "D43"):
        item = changes[id_]
        pp = item["protected_root"]
        check(
            pp["tier"] == "additive_only" and pp["non_additive"] is True,
            "lost protected-root classification " + id_,
        )
        prefix = "ALLOW-ROOT-DELETION: " + item["path"] + " \u2014 "
        check(
            pp["commit_marker"].startswith(prefix),
            "incorrect mandatory root marker grammar for " + id_,
        )
        check(
            pp["pr_body_stamp"] == "<!-- L9_PROTECTED_ROOT_PR -->",
            "missing protected root PR stamp",
        )
        check(
            pp["human_owner_authorization"] == "REQUIRED_NOT_GRANTED",
            "invented human approval " + id_,
        )
    check(
        changes["D04"]["replacement_fragment"].strip() == ".venv/ node_modules/",
        "resolver excludes active path after correction",
    )
    check(
        changes["D05"]["replacement_fragment"].strip() == ".venv/ node_modules/",
        "security selector excludes active path after correction",
    )
    check(
        "UNKNOWN" in " ".join(d["recursive_alignment"]["obligations_still_blocked"]).upper()
        or "original_PR_immutable_footprint_source"
        in d["recursive_alignment"]["obligations_still_blocked"],
        "missing original-scope blocker",
    )
    check(
        d["closure_contract"]["completion_status_now"] != "DONE",
        "falsely claims implementation complete",
    )
    check(
        d["source_evidence"]["local_runtime_tests_performed"] is False,
        "unexecuted tests misrepresented",
    )
    for x in ("U01", "U08", "U09", "U10"):
        check(
            x in {u["id"] for u in d["unknowns_and_stop_conditions"]},
            "missing material blocker " + x,
        )
    return {
        "verdict": "STATIC_PASS_WITH_EXECUTION_BLOCKERS",
        "revision": d["revision"],
        "law_payload_start_line": begin,
        "law_payload_final_line": anchors["result_last_content_line"],
        "law_heading_coordinates": anchors,
        "law_line_dispositions": len(law_ids),
        "findings": len(finding_ids),
        "downstream_actions": len(change_ids),
        "validation_cases": len(test_ids),
        "host_runtime_tests": "NOT_RUN",
        "global_authority_projection": "NOT_REPLAYED",
        "repo_mutation": "NONE",
    }


def git(repo: Path, *argv: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True, text=True, timeout=30, check=False
    )
    check(p.returncode == 0, "git " + " ".join(argv) + " failed: " + p.stderr.strip()[:200])
    return p.stdout.strip()


def verify_live_repo(d: dict, repo: Path) -> dict:
    check((repo / ".git").exists(), "--repo is not a Git checkout")
    check(
        git(repo, "rev-parse", "HEAD") == d["subject"]["frozen_commit"],
        "repo HEAD differs from proposal snapshot: STOP_AND_REBASE_REVIEW",
    )
    law = repo / d["subject"]["law_path"]
    check(law.is_file(), "canonical law does not exist")
    check(
        git(repo, "hash-object", str(law)) == d["subject"]["law_git_blob_sha1"],
        "law blob differs from frozen baseline",
    )
    raw = law.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    check(len(lines) == d["subject"]["law_last_content_line"], "law total source lines changed")
    check(lines[-1] == d["subject"]["law_last_content_exact"], "law last content line differs")
    found = []
    for action in d["downstream_changes"]:
        if not action.get("expected_blob_sha1"):
            continue
        path = repo / action["path"]
        check(path.is_file(), "target missing: " + action["path"])
        check(
            git(repo, "hash-object", str(path)) == action["expected_blob_sha1"],
            "source blob differs: " + action["path"],
        )
        found.append(action["path"])
    return {
        "repo_head_match": True,
        "law_blob_match": True,
        "guarded_downstream_file_count": len(found),
        "edits": "NONE",
    }


def self_test(d: dict) -> dict:
    validate(d)
    witnessed = []
    tests = [
        (
            "law rewrite guard",
            lambda a: a["canonical_append"].__setitem__("must_not_change_existing_bytes", False),
        ),
        (
            "duplicate edit path",
            lambda a: a["downstream_changes"].append(copy.deepcopy(a["downstream_changes"][0])),
        ),
        (
            "unknown finding",
            lambda a: a["downstream_changes"][0]["finding_ids"].append("NONEXISTENT"),
        ),
        (
            "wrong law coordinate",
            lambda a: a["canonical_append"]["proposed_post_append_lines"].__setitem__(
                "section_6_2_17", 12
            ),
        ),
        (
            "unauthorized root rewrite",
            lambda a: next(q for q in a["downstream_changes"] if q["id"] == "D43")[
                "protected_root"
            ].__setitem__("human_owner_authorization", "GRANTED"),
        ),
        (
            "pr-check false current",
            lambda a: next(
                q for q in a["canonical_law_line_dispositions"] if q["id"] == "L16"
            ).__setitem__("operation", "KEEP_ACTIVE"),
        ),
        (
            "delete scope unknown",
            lambda a: a["unknowns_and_stop_conditions"].__setitem__(
                slice(None), [q for q in a["unknowns_and_stop_conditions"] if q["id"] != "U01"]
            ),
        ),
        (
            "generated worker conflation",
            lambda a: next(q for q in a["downstream_changes"] if q["id"] == "D03").__setitem__(
                "operation", "APPLY_WITH_TARGET_OWNER"
            ),
        ),
    ]
    for name, mut in tests:
        candidate = copy.deepcopy(d)
        try:
            mut(candidate)
            validate(candidate)
        except Invalid:
            witnessed.append(name)
        else:
            raise Invalid("negative fixture unexpectedly passed: " + name)
    return {"negative_fixture_count": len(witnessed), "caught": witnessed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runbook", nargs="?", default="canonical_law_revision_runbook_v2.yaml")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--repo", type=Path, help="read-only check against frozen live checkout; never edits"
    )
    ns = parser.parse_args()
    try:
        source = Path(ns.runbook)
        with source.open(encoding="utf-8") as fd:
            d = yaml.safe_load(fd)
        result = validate(d)
        if ns.self_test:
            result["negative_fixtures"] = self_test(d)
        if ns.repo:
            result["actual_source_guards"] = verify_live_repo(d, ns.repo.resolve())
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (Invalid, ValueError, KeyError, OSError, yaml.YAMLError) as exc:
        print("FAIL_STATIC_ALIGNMENT: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
