#!/usr/bin/env python3
"""Autonomous PR-body compile fills measured facts; no judgment leftover."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from compose_pr_body import (  # noqa: E402
    GATE_UNVERIFIED,
    SCHEMA,
    THIN_PROBLEM_NOTE,
    UNMEASURED,
    MechanicalFacts,
    compose_pr_body,
    range_title,
    write_handoff,
)

TEMPLATE = """<!-- L9_PROTECTED_ROOT_PR -->

## Protected-root

### Paths

- ` `

### Edit mode (pick one per path)

- [ ] **Append-only** — existing lines kept
- [ ] **Justified rewrite** — commit contains ALLOW-ROOT-DELETION

### Why a root file

<!-- What cannot be done in a non-root path. Composer fills. -->

### Proof of necessity (rewrites only)

<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->

## Problem

```
paste the error / failing output here, or delete this block and describe the gap
```

Closes #

## Type of Change

- [ ] Bug fix
- [ ] Feature / enhancement
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [ ] CI / governance change
- [ ] Breaking change (see rollback below)

## Fix

<!-- What you changed -->

## Risk

- [ ] Low — additive, reversible, no data or contract change
- [ ] Medium — touches shared code, config, or a public interface
- [ ] High — breaking change, migration, IAM/network, or irreversible

Blast radius:
Rollback:

## Evidence

```
$ pytest -q
$ ruff check . && pyright
```

## Gates

- [ ] Regression test added that fails without this fix
- [ ] No secrets, tokens, or customer data in code, tests, fixtures, or logs

## Reviewer focus

<!-- Where to look hardest. Trade-offs accepted. Deferred follow-ups, with issue links. -->

## Changes by intent

**Added**
- `path/to/new_file.py` — why this file needs to exist

**Modified**
- `path/to/existing.py` — what changed in it and why

**Deleted**
- `path/to/dead.py` — why it is safe to remove

## Files touched

<!-- FILES-TOUCHED:START -->
_pending — the bot fills this in on push_
<!-- FILES-TOUCHED:END -->
"""


class ComposePrBodyTests(unittest.TestCase):
    def test_autonomous_fill_checks_risk_and_type(self) -> None:
        facts = MechanicalFacts(
            commits=["fix: fill PR body from receipts"],
            changed_files=["M\tops/scripts/open_pr_after_gate.sh"],
            issue_closes=[172],
            gate_receipt={
                "schema": "l9.pr_gate_receipt.v2",
                "head": "abc",
                "passed_at": "2026-08-21T00:00:00Z",
            },
            l4_receipt={"phase": "release_authorized", "head_sha": "abc"},
            template_path=".github/pull_request_template.md",
        )
        result = compose_pr_body(facts, TEMPLATE)
        self.assertIn("fix: fill PR body from receipts", result.body)
        self.assertIn("M\tops/scripts/open_pr_after_gate.sh", result.body)
        self.assertIn("Closes #172", result.body)
        self.assertIn("gate-receipt.json present", result.body)
        self.assertIn("- [x] `make pr` local gate receipt present", result.body)
        self.assertIn("- [x] L4 release receipt present", result.body)
        self.assertIn(f"- [ ] CI green — {UNMEASURED}", result.body)
        self.assertIn(
            "- [x] Medium — touches shared code, config, or a public interface", result.body
        )
        self.assertIn("- [x] CI / governance change", result.body)
        self.assertIn("Rollback: revert this PR", result.body)
        self.assertIn(
            "`ops/scripts/open_pr_after_gate.sh` — fix: fill PR body from receipts", result.body
        )
        self.assertIn("- N/A — no additive_only root files", result.body)
        self.assertEqual(result.needs_completion, [])
        self.assertIn("commits", result.mechanical_filled)

    def test_one_template_fills_summary_and_protected_top(self) -> None:
        root = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        facts = MechanicalFacts(
            commits=["docs: compose PR body"],
            changed_files=["M\tAGENTS.md"],
            issue_closes=[172],
            gate_receipt={"schema": "l9.pr_gate_receipt.v2", "head": "abc", "passed_at": "t"},
            l4_receipt={"phase": "release_authorized", "head_sha": "abc"},
            additive_only_paths=["AGENTS.md"],
        )
        result = compose_pr_body(facts, root)
        self.assertIn("<!-- L9_PROTECTED_ROOT_PR -->", result.body)
        self.assertIn("- `AGENTS.md`", result.body)
        self.assertIn("- [x] **Append-only**", result.body)
        self.assertIn("docs: compose PR body", result.body)
        self.assertIn("Closes #172", result.body)
        self.assertIn("append-only — none.", result.body)
        self.assertEqual(result.needs_completion, [])
        self.assertIn("protected-root", result.mechanical_filled)

    def test_protected_rewrite_checks_justified(self) -> None:
        facts = MechanicalFacts(
            commits=["fix: rewrite agents fragment"],
            changed_files=["M\tAGENTS.md"],
            additive_only_paths=["AGENTS.md"],
            deletion_markers={"AGENTS.md": "fold stale pointer"},
        )
        result = compose_pr_body(facts, TEMPLATE)
        self.assertIn("- [x] **Justified rewrite**", result.body)
        self.assertIn("AGENTS.md: fold stale pointer", result.body)
        self.assertIn("- [x] Breaking change", result.body)

    def test_missing_receipts_do_not_self_certify(self) -> None:
        facts = MechanicalFacts(commits=["wip"], changed_files=["A\tfoo.py"])
        result = compose_pr_body(facts, TEMPLATE)
        self.assertIn(f"- [ ] `make pr` local gate receipt — {UNMEASURED}", result.body)
        self.assertIn(f"- [ ] L4 release receipt — {UNMEASURED}", result.body)
        self.assertNotIn("- [x] `make pr`", result.body)
        self.assertNotIn("- [x] L4 release", result.body)

    def test_no_template_still_lists_commits_and_files(self) -> None:
        facts = MechanicalFacts(
            commits=["subject one"],
            changed_files=["A\tnew.py"],
            campaign_body="Campaign note",
        )
        result = compose_pr_body(facts, None)
        self.assertIn("Campaign note", result.body)
        self.assertIn("subject one", result.body)
        self.assertIn("A\tnew.py", result.body)

    def test_v2_gate_receipt_reports_its_content_digest_not_head(self) -> None:
        facts = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tx"],
            gate_receipt={
                "schema": "l9.pr_gate_receipt.v2",
                "paths_digest": "111",
                "content_digest": "222",
                "pr_base": "origin/main",
                "passed_at": "2026-09-15T00:00:00Z",
            },
        )
        body = compose_pr_body(facts, TEMPLATE).body
        self.assertIn("content_digest=222", body)
        self.assertNotIn("head=None", body)

    def test_unmeasured_additive_only_does_not_claim_none(self) -> None:
        facts = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tMakefile"],
            additive_only_paths=[],
            additive_only_measured=False,
        )
        body = compose_pr_body(facts, TEMPLATE).body
        self.assertIn("NOT MEASURED", body)
        self.assertNotIn("no additive_only root files", body)

    def test_measured_empty_additive_only_still_claims_none(self) -> None:
        facts = MechanicalFacts(commits=["a"], changed_files=["M\tops/x.py"])
        body = compose_pr_body(facts, TEMPLATE).body
        self.assertIn("no additive_only root files", body)
        self.assertNotIn("NOT MEASURED", body)

    def test_named_additive_only_file_must_exist(self) -> None:
        from compose_pr_body import _load_additive_only

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "additive-only.txt"
            with self.assertRaises(FileNotFoundError):
                _load_additive_only(missing)

    def test_post_exec_kernels_tick_needs_evidence_not_just_release_phase(self) -> None:
        template = (
            TEMPLATE + "\n## L4\n\n- [ ] **L4 local autonomy** — release authorized\n"
            "- [ ] **Post-exec kernels** — RA + V&R applied\n"
        )
        released_unevidenced = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tops/x.py"],
            l4_receipt={
                "phase": "release_authorized",
                "tree_digest": "d",
                "kernel_evidence": "absent",
                "kernels": {
                    "recursive_alignment": {"status": "passed", "evidence": "absent"},
                    "validate_repair": {"status": "passed", "evidence": "absent"},
                },
            },
        )
        body = compose_pr_body(released_unevidenced, template).body
        self.assertIn("- [x] **L4 local autonomy**", body)
        self.assertNotIn("- [x] **Post-exec kernels**", body)
        self.assertIn("kernel_evidence=absent", body)

        legacy_receipt = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tops/x.py"],
            l4_receipt={"phase": "release_authorized", "head_sha": "abc"},
        )
        body = compose_pr_body(legacy_receipt, template).body
        self.assertNotIn("- [x] **Post-exec kernels**", body)
        self.assertIn("kernel_evidence=not recorded", body)

        evidenced = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tops/x.py"],
            l4_receipt={
                "phase": "release_authorized",
                "tree_digest": "d",
                "kernel_evidence": "evidenced",
                "kernels": {
                    "recursive_alignment": {"status": "evidenced", "report_sha256": "r"},
                    "validate_repair": {"status": "evidenced", "report_sha256": "r"},
                },
            },
        )
        body = compose_pr_body(evidenced, template).body
        self.assertIn("- [x] **Post-exec kernels**", body)
        self.assertIn("kernel_evidence=evidenced", body)

    def test_breakglass_trail_is_reported_only_for_this_head(self) -> None:
        trail = {
            "schema": "l9.l4_breakglass.v1",
            "variable": "L9_LOCAL_PUSH_AUTHORIZED",
            "reason": "ops: hotfix",
            "head": "abc123",
            "used_at": "2026-09-15T00:00:00Z",
        }
        matching = MechanicalFacts(
            commits=["a"], changed_files=["M\tops/x.py"], breakglass=trail, head="abc123"
        )
        body = compose_pr_body(matching, TEMPLATE).body
        self.assertIn("BREAKGLASS L9_LOCAL_PUSH_AUTHORIZED=ops: hotfix", body)
        self.assertIn("head=abc123", body)

        # The file is never cleaned up: a trail from an earlier push is history,
        # not a statement about this PR.
        older = MechanicalFacts(
            commits=["a"], changed_files=["M\tops/x.py"], breakglass=trail, head="fff999"
        )
        self.assertNotIn("BREAKGLASS", compose_pr_body(older, TEMPLATE).body)

        # No head measured -> no claim either way.
        unknown = MechanicalFacts(
            commits=["a"], changed_files=["M\tops/x.py"], breakglass=trail, head=""
        )
        self.assertNotIn("BREAKGLASS", compose_pr_body(unknown, TEMPLATE).body)

        none = MechanicalFacts(commits=["a"], changed_files=["M\tops/x.py"], head="abc123")
        self.assertNotIn("BREAKGLASS", compose_pr_body(none, TEMPLATE).body)

    def test_multi_commit_range_is_told_oldest_first_not_tip_only(self) -> None:
        facts = MechanicalFacts(
            commits=["first: bind receipts", "second: add ratchet", "third: delegate digest"],
            commit_bodies=["The gate read a stale field.\n\nCloses #1", "", ""],
            changed_files=["M\tops/a.py", "A\tops/b.py", "M\tAGENTS.md"],
            path_subjects={
                "ops/a.py": "first: bind receipts",
                "ops/b.py": "second: add ratchet",
                "AGENTS.md": "third: delegate digest",
            },
            additive_only_paths=["AGENTS.md"],
        )
        body = compose_pr_body(facts, TEMPLATE).body
        # Problem is where the work started, plus how much follows.
        self.assertIn("first: bind receipts (+2 more commits below)", body)
        self.assertIn("The gate read a stale field.", body)
        self.assertNotIn("Closes #1\n\n## ", body.split("## Problem")[1].split("## Type")[0])
        # Fix lists every subject, in the order they were made.
        fix_section = body.split("## Fix")[1].split("## Risk")[0]
        self.assertLess(fix_section.index("- first:"), fix_section.index("- second:"))
        self.assertLess(fix_section.index("- second:"), fix_section.index("- third:"))
        # Each path is explained by the commit that touched it.
        self.assertIn("`ops/a.py` — first: bind receipts", body)
        self.assertIn("`ops/b.py` — second: add ratchet", body)
        self.assertIn("`AGENTS.md` — third: delegate digest", body)
        # Why a root file names the commit that touched the root file, not the tip
        # or the oldest subject by accident.
        why_section = body.split("### Why a root file")[1].split("### Proof")[0]
        self.assertIn("third: delegate digest", why_section)
        self.assertNotIn("first: bind receipts", why_section)

    def test_single_commit_range_reads_as_before(self) -> None:
        facts = MechanicalFacts(commits=["only: one"], changed_files=["M\tops/x.py"])
        body = compose_pr_body(facts, TEMPLATE).body
        self.assertNotIn("more commit", body)
        self.assertNotIn("- only: one", body.split("## Fix")[1].split("## Risk")[0])
        self.assertIn("`ops/x.py` — only: one", body)

    def test_collect_mechanical_orders_oldest_first_and_attributes_paths(self) -> None:
        import subprocess

        from compose_pr_body import collect_mechanical

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            def git(*args: str) -> None:
                subprocess.run(
                    ["git", "-C", str(repo), *args],
                    check=True,
                    capture_output=True,
                    env={
                        "PATH": __import__("os").environ["PATH"],
                        "GIT_AUTHOR_NAME": "t",
                        "GIT_AUTHOR_EMAIL": "t@x",
                        "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@x",
                        "HOME": tmp,
                    },
                )

            git("init", "-q", "-b", "main")
            (repo / "base.txt").write_text("base\n")
            git("add", "base.txt")
            git("commit", "-q", "-m", "base")
            git("checkout", "-q", "-b", "feat")
            (repo / "a.py").write_text("a\n")
            git("add", "a.py")
            git("commit", "-q", "-m", "one: add a", "-m", "Why a exists.\n\nCloses #7")
            (repo / "b.py").write_text("b\n")
            (repo / "a.py").write_text("a2\n")
            git("add", "a.py", "b.py")
            git("commit", "-q", "-m", "two: touch a and b")
            facts = collect_mechanical(repo, pr_base="main")
        self.assertEqual(facts.commits, ["one: add a", "two: touch a and b"])
        self.assertEqual(facts.commit_bodies[0].splitlines()[0], "Why a exists.")
        self.assertEqual(facts.commit_bodies[1], "")
        self.assertEqual(facts.issue_closes, [7])
        # Newest commit that touched a path wins the attribution.
        self.assertEqual(facts.path_subjects["a.py"], "two: touch a and b")
        self.assertEqual(facts.path_subjects["b.py"], "two: touch a and b")

    def test_stacked_range_excludes_inherited_mainline_and_merge_commits(self) -> None:
        """PR #602's title quoted a `main` commit that was never this branch's.

        The stack parent had been cut before its own base was refreshed, so
        `parent..HEAD` inherited a mainline commit and the merges that carried
        it. The narrative range must be this branch's own non-merge commits.
        """
        import subprocess

        from compose_pr_body import collect_mechanical

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            env = {
                "PATH": __import__("os").environ["PATH"],
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@x",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@x",
                "HOME": tmp,
            }

            def git(*args: str) -> None:
                subprocess.run(
                    ["git", "-C", str(repo), *args], check=True, capture_output=True, env=env
                )

            git("init", "-q", "-b", "main")
            (repo / "base.txt").write_text("base\n")
            git("add", "base.txt")
            git("commit", "-q", "-m", "base")
            # The stack root (#600) is cut from main …
            git("checkout", "-q", "-b", "root")
            (repo / "root.py").write_text("r\n")
            git("add", "root.py")
            git("commit", "-q", "-m", "root: its own work")
            # … the parent (#601) is cut from the root …
            git("checkout", "-q", "-b", "parent")
            (repo / "parent.py").write_text("p\n")
            git("add", "parent.py")
            git("commit", "-q", "-m", "parent: its own work")
            # … then main moves on, and the root catches up to it — after the
            # parent was cut, so the parent has neither of those commits.
            git("checkout", "-q", "main")
            (repo / "mainline.py").write_text("m\n")
            git("add", "mainline.py")
            git("commit", "-q", "-m", "mainline: somebody else's fix (#599)")
            git("checkout", "-q", "root")
            git("merge", "-q", "--no-edit", "main")
            (repo / "root.py").write_text("r2\n")
            git("add", "root.py")
            git("commit", "-q", "-m", "root: regenerate manifests after merging #599")
            # The child (#602) starts from the parent, catches up to the root's
            # new tip by merge, and does its own work.
            git("checkout", "-q", "-b", "child", "parent")
            git("merge", "-q", "--no-edit", "root")
            (repo / "child.py").write_text("c\n")
            git("add", "child.py")
            git("commit", "-q", "-m", "child: first real change")
            (repo / "child.py").write_text("c2\n")
            git("add", "child.py")
            git("commit", "-q", "-m", "child: second real change")
            # The composer sees mainline and the chain through remote-tracking
            # names, and the chain itself through the stack-base receipt.
            git("update-ref", "refs/remotes/origin/main", "main")
            git("update-ref", "refs/remotes/origin/root", "root")
            git("update-ref", "refs/remotes/origin/parent", "parent")
            (repo / ".l9" / "pr").mkdir(parents=True)
            (repo / ".l9" / "pr" / "stack-base.json").write_text(
                json.dumps(
                    {
                        "schema": "l9.stack_base.v1",
                        "pr_stack": "auto",
                        "pr_base": "origin/parent",
                        "chain": ["root", "parent"],
                    }
                )
            )

            facts = collect_mechanical(repo, pr_base="origin/parent")
            # Without the chain, the root's later commit is "inherited" too: the
            # receipt is what lets the composer tell whose it is.
            (repo / ".l9" / "pr" / "stack-base.json").unlink()
            without_chain = collect_mechanical(repo, pr_base="origin/parent")
            (repo / ".l9" / "pr" / "stack-base.json").write_text(
                json.dumps({"schema": "l9.stack_base.v1", "chain": ["root", "parent"]})
            )
            # The title the shell asks for goes through the same range, so it can
            # never again quote a commit the body would not tell.
            title = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "ops" / "scripts" / "compose_pr_body.py"),
                    "--workspace",
                    str(repo),
                    "--pr-base",
                    "origin/parent",
                    "--print-title",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()

        self.assertEqual(facts.commits, ["child: first real change", "child: second real change"])
        self.assertEqual(title, "child: first real change")
        self.assertEqual(range_title(facts), title)
        self.assertEqual(range_title(MechanicalFacts()), "")
        self.assertNotIn("mainline.py", facts.path_subjects)
        self.assertNotIn("root.py", facts.path_subjects)
        self.assertEqual(facts.path_subjects["child.py"], "child: second real change")
        # The diff is still the real diff against the parent: the inherited
        # mainline and root files are in it, it is only the *story* that
        # leaves them out.
        self.assertIn("A\tmainline.py", facts.changed_files)
        self.assertIn("M\troot.py", facts.changed_files)
        # Mainline and merges are excluded even with no receipt; the root's own
        # later commit is exactly what the chain adds.
        self.assertEqual(
            without_chain.commits,
            [
                "root: regenerate manifests after merging #599",
                "child: first real change",
                "child: second real change",
            ],
        )

    def test_subject_only_problem_is_marked_thin(self) -> None:
        """A Problem with no commit body paragraph says so, in the body and the handoff.

        The composer has no prose source beyond subjects and the oldest commit's
        first body paragraph. When that paragraph is absent the Problem is a
        subject line, which read as a finished description until a reviewer
        noticed (#614). The note is the floor made visible.
        """
        thin = MechanicalFacts(
            commits=["fix(x): first", "fix(x): second"],
            commit_bodies=["", ""],
            changed_files=["M\tx"],
            template_path=".github/pull_request_template.md",
        )
        result = compose_pr_body(thin, TEMPLATE)
        problem = result.body.split("## Problem")[1].split("## Type")[0]
        self.assertIn("fix(x): first (+1 more commit below)", problem)
        self.assertIn(THIN_PROBLEM_NOTE, problem)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            write_handoff(path, result=result, facts=thin, pr_number=1)
            self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["thin_problem"])

        told = MechanicalFacts(
            commits=["fix(x): first", "fix(x): second"],
            commit_bodies=["The gate read a stale field.\n\nCloses #1", ""],
            changed_files=["M\tx"],
            template_path=".github/pull_request_template.md",
        )
        result = compose_pr_body(told, TEMPLATE)
        problem = result.body.split("## Problem")[1].split("## Type")[0]
        self.assertIn("The gate read a stale field.", problem)
        self.assertNotIn(THIN_PROBLEM_NOTE, result.body)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            write_handoff(path, result=result, facts=told, pr_number=1)
            self.assertFalse(json.loads(path.read_text(encoding="utf-8"))["thin_problem"])

    def test_template_does_not_cite_a_workflow_that_does_not_exist(self) -> None:
        root = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        self.assertNotIn("pr-gates.yml", root)
        self.assertFalse((REPO / ".github" / "workflows" / "pr-gates.yml").exists())

    def test_handoff_lists_empty_needs_completion(self) -> None:
        facts = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tx"],
            template_path=".github/pull_request_template.md",
        )
        result = compose_pr_body(facts, TEMPLATE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr-body-completion.json"
            write_handoff(path, result=result, facts=facts, pr_number=12)
            doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["pr_number"], 12)
        self.assertEqual(doc["commit_count"], 1)
        self.assertEqual(doc["needs_completion"], [])


# The org PR-body validators judge every body make pr composes. They are
# vendored byte-exact under fixtures/org_pr_gates (manifest.json names the
# source ref and sha256) and executed with node, so these tests prove
# compatibility with a named validator version instead of a hand-kept copy of
# its rules. Moving the pin means refreshing the file and its digest together.
ORG_GATES = Path(__file__).resolve().parent / "fixtures" / "org_pr_gates"


def _run_org_validator(workflow: str, body: str, name_status: list[str] | None = None) -> dict:
    node = shutil.which("node")
    if node is None:
        # Not a skip: without node these tests cannot prove the composer
        # passes the real validator, and silence would read as a pass.
        raise AssertionError("node is required to run the vendored org PR validators")
    with tempfile.TemporaryDirectory() as tmp:
        body_file = Path(tmp) / "body.md"
        body_file.write_text(body, encoding="utf-8")
        args = [
            node,
            str(ORG_GATES / "run_workflow_script.js"),
            str(ORG_GATES / workflow),
            str(body_file),
        ]
        if name_status is not None:
            changed = Path(tmp) / "changed.txt"
            changed.write_text("".join(f"{line}\n" for line in name_status), encoding="utf-8")
            args.append(str(changed))
        proc = subprocess.run(args, capture_output=True, text=True, check=False, timeout=60)
    if proc.returncode != 0:
        raise AssertionError(f"{workflow} runner failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def _section(body: str, heading: str) -> str:
    """Text under one ``## heading`` — for assertions, not a validator rule."""
    match = re.search(rf"^## {re.escape(heading)}\n([\s\S]*?)(?=^## |\Z)", body, re.M)
    return match.group(1) if match else ""


class OrgPrGateContractTests(unittest.TestCase):
    NAME_STATUS = [
        "M\tops/scripts/compose_pr_body.py",
        "A\ttests/test_new.py",
        "R100\told/name.py\tnew/name.py",
        "M\tMakefile",
    ]

    def _facts(self) -> MechanicalFacts:
        return MechanicalFacts(
            commits=["fix(pr): align composer with org gates", "test: cover it"],
            commit_bodies=["Every composed body failed the org Gate reason check.", ""],
            changed_files=list(self.NAME_STATUS),
            gate_receipt={"schema": "l9.pr_gate_receipt.v2", "content_digest": "d"},
        )

    def test_vendored_validators_match_their_manifest(self) -> None:
        manifest = json.loads((ORG_GATES / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "l9.org_pr_gate_fixtures.v1")
        for entry in manifest["fixtures"]:
            with self.subTest(fixture=entry["file"]):
                self.assertRegex(entry["ref"], r"^[0-9a-f]{40}$")
                digest = hashlib.sha256((ORG_GATES / entry["file"]).read_bytes()).hexdigest()
                self.assertEqual(digest, entry["sha256"])

    def test_composed_body_passes_pinned_governance_pr(self) -> None:
        for label, template in (
            ("inline", TEMPLATE),
            ("governance fork", (REPO / ".github" / "pull_request_template.md").read_text()),
        ):
            with self.subTest(template=label):
                body = compose_pr_body(self._facts(), template).body
                result = _run_org_validator("governance-pr.yml", body)
                self.assertEqual(result["failures"], [])
                self.assertEqual(result["findings"], [])

    def test_validator_runner_still_rejects(self) -> None:
        # Guards the harness: a runner that silently passed everything would
        # make the test above vacuous.
        result = _run_org_validator("governance-pr.yml", TEMPLATE)
        self.assertTrue(result["failures"])

    def test_unmeasured_gates_are_not_claimed_not_applicable(self) -> None:
        body = compose_pr_body(self._facts(), TEMPLATE).body
        gates = _section(body, "Gates")
        regression = "Regression test added that fails without this fix"
        self.assertIn(f"{regression} — {GATE_UNVERIFIED}", gates)
        self.assertNotIn("not this change", gates)
        self.assertNotIn(UNMEASURED, gates)

    def test_rename_declares_the_canonical_row_key_for_pr_files(self) -> None:
        body = compose_pr_body(self._facts(), TEMPLATE).body
        intent = _section(body, "Changes by intent")
        self.assertIn("- `old/name.py -> new/name.py` — ", intent)
        # Only the row key: a bare endpoint is not a row, and pr-files would
        # report it as declared but not in the diff.
        self.assertNotIn("`new/name.py`", intent)
        self.assertNotIn("`old/name.py`", intent)
        result = _run_org_validator("pr-files.yml", body, self.NAME_STATUS)
        self.assertEqual(result["failures"], [])
        self.assertNotIn("Declared but not in the diff", result["updatedBody"])
        # The strict matcher is what makes the declaration meaningful: the same
        # body declaring only the new path must still fail.
        endpoint = body.replace("`old/name.py -> new/name.py`", "`new/name.py`")
        self.assertTrue(_run_org_validator("pr-files.yml", endpoint, self.NAME_STATUS)["failures"])


if __name__ == "__main__":
    unittest.main()
