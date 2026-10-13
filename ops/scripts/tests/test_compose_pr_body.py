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
    COMPOSER_MARKER,
    GATE_UNVERIFIED,
    PROTECTED_STAMP,
    REGION_EVIDENCE,
    REGION_FILES,
    REGION_INTENT,
    REGION_PROTECTED_PATHS,
    SCHEMA,
    THIN_PROBLEM_NOTE,
    UNMEASURED,
    GitRangeError,
    MechanicalFacts,
    TemplateError,
    check_inventory,
    collect_mechanical,
    compose_pr_body,
    diff_rows,
    parse_row,
    range_title,
    refresh_body,
    region_content,
    resolve_template,
    validate_template,
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
        self.assertIn("- `open_pr_after_gate.sh` — modified", result.body)
        self.assertIn("Closes #172", result.body)
        self.assertIn("gate-receipt.json present", _section(result.body, "Evidence"))
        self.assertIn("L4 receipt present", _section(result.body, "Evidence"))
        # One inventory: no appended second file list or receipt checklist.
        for heading in ("## Changed files", "## Test plan", "## Commits"):
            self.assertNotIn(heading, result.body)
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
        evidence = _section(result.body, "Evidence")
        self.assertIn("gate-receipt.json absent", evidence)
        self.assertIn("L4 receipt absent", evidence)
        self.assertNotIn("- [x] No secrets", result.body)

    def test_no_template_still_lists_commits_and_files(self) -> None:
        facts = MechanicalFacts(
            commits=["subject one"],
            changed_files=["A\tnew.py"],
            campaign_body="Campaign note",
        )
        result = compose_pr_body(facts, None)
        self.assertIn("Campaign note", result.body)
        self.assertIn("subject one", result.body)
        self.assertIn("- `new.py` — added", result.body)
        self.assertIn("- `new.py` — subject one", result.body)

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

    def test_l4_receipt_evidence_binds_tree_digest_without_kernel_metadata(self) -> None:
        template = TEMPLATE + "\n## L4\n\n- [ ] **L4 local autonomy** — release authorized\n"
        released = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tops/x.py"],
            l4_receipt={"phase": "release_authorized", "tree_digest": "d"},
        )
        body = compose_pr_body(released, template).body
        self.assertIn("L4 receipt present", body)
        self.assertIn("tree_digest=d", body)
        self.assertIn("- [x] **L4 local autonomy**", body)
        self.assertNotIn("kernel_evidence", body)
        self.assertNotIn("Post-exec kernels", body)

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


CANONICAL_TEMPLATE = (ORG_GATES / "pull_request_template.md").read_text(encoding="utf-8")
COMPOSER = REPO / "ops" / "scripts" / "compose_pr_body.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@x",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@x",
    "GIT_CONFIG_NOSYSTEM": "1",
}


class _Repo:
    """A throwaway git repository: main with a base commit, then a branch."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.env = {**GIT_ENV, "PATH": __import__("os").environ["PATH"], "HOME": str(root)}
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
            env=self.env,
        ).stdout

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message: str, *paths: str) -> None:
        self.git("add", "-A", "--", *(paths or ["."]))
        self.git("commit", "-q", "-m", message)


BODY_TEXT = "".join(f"line {n} of a file that is long enough to be a rename\n" for n in range(40))
# Distinct bytes, so git cannot pair the copy with the rename source.
COPY_TEXT = "".join(f"copy source row {n}\n" for n in range(40))


class DiffRowTests(unittest.TestCase):
    """F3: the inventory is the diff — every status, every awkward path, once."""

    def test_every_status_and_awkward_path_is_one_exact_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _Repo(Path(tmp))
            repo.write("keep.txt", "a\n")
            repo.write("gone.txt", "bye\n")
            repo.write("move_me.py", BODY_TEXT)
            repo.write("copy_src.py", COPY_TEXT)
            repo.write("Makefile", "all:\n")
            repo.commit("base")
            repo.git("checkout", "-q", "-b", "feat")
            repo.write("keep.txt", "b\n")
            repo.git("rm", "-q", "gone.txt")
            (repo.root / "pkg").mkdir()
            repo.git("mv", "move_me.py", "pkg/moved.py")
            repo.write("copy_src.py", COPY_TEXT + "tail\n")
            repo.write("copy_dst.py", COPY_TEXT)
            repo.write("nested/deep/new.py", "x\n")
            repo.write("LICENSE-EXTRA", "extensionless root file\n")
            repo.write("docs/über façade.md", "unicode\n")
            repo.write("Makefile", "all:\n\techo hi\n")
            repo.commit("feat: every status")
            rows = diff_rows(repo.root, "main")

        keys = {row.key: row.status[:1] for row in rows}
        self.assertEqual(keys["keep.txt"], "M")
        self.assertEqual(keys["gone.txt"], "D")
        self.assertEqual(keys["move_me.py -> pkg/moved.py"], "R")
        self.assertEqual(keys["copy_src.py -> copy_dst.py"], "C")
        self.assertEqual(keys["nested/deep/new.py"], "A")
        self.assertEqual(keys["LICENSE-EXTRA"], "A")
        self.assertEqual(keys["docs/über façade.md"], "A")  # byte-exact, never C-quoted
        self.assertEqual(keys["Makefile"], "M")
        self.assertEqual(len(keys), len(rows), "a row was reported twice")
        # A rename is one row, not an add plus a delete.
        self.assertNotIn("pkg/moved.py", keys)
        self.assertNotIn("move_me.py", keys)
        # Round trip through the string form the facts carry.
        self.assertEqual([parse_row(row.line()) for row in rows], rows)

    def test_unresolvable_base_raises_instead_of_listing_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _Repo(Path(tmp))
            repo.write("a.txt", "a\n")
            repo.commit("base")
            with self.assertRaises(GitRangeError):
                diff_rows(repo.root, "origin/not-fetched")
            proc = subprocess.run(
                [sys.executable, str(COMPOSER), "--workspace", tmp, "--pr-base", "nope"],
                capture_output=True,
                text=True,
                check=False,
                env=repo.env,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("ERROR: git diff", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_large_inventory_is_complete_and_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _Repo(Path(tmp))
            repo.write("seed.txt", "s\n")
            repo.commit("base")
            repo.git("checkout", "-q", "-b", "big")
            for n in range(75):
                repo.write(f"gen/part_{n:03d}.txt", f"{n}\n")
            repo.commit("feat: 75 files")
            facts = collect_mechanical(repo.root, pr_base="main")
        body = compose_pr_body(facts, CANONICAL_TEMPLATE).body
        files = region_content(body, REGION_FILES) or ""
        self.assertTrue(files.startswith("**75 files** — 75 files changed"))
        self.assertIn("<details><summary>Expand file list</summary>", files)
        self.assertEqual(files.count("— added"), 75)
        self.assertEqual(
            check_inventory(body, [parse_row(r) for r in facts.changed_files]), ([], [])
        )


def _facts(changed: list[str], **extra: object) -> MechanicalFacts:
    base: dict[str, object] = {
        "commits": ["feat: first", "feat: second"],
        "commit_bodies": ["Why the work started.", ""],
        "changed_files": changed,
        "path_subjects": {},
        "head": "a" * 40,
        "shortstat": f"{len(changed)} files changed",
    }
    base.update(extra)
    return MechanicalFacts(**base)  # type: ignore[arg-type]


class RefreshTests(unittest.TestCase):
    """D5/E4/E5/F4/F5: regions move with the diff; people's text does not."""

    FIRST = ["M\tops/a.py", "A\tops/b.py"]
    LATER = ["M\tops/a.py", "A\tops/c.py", "R100\told/x.py\tnew/x.py"]

    def _reviewed(self) -> str:
        body = compose_pr_body(_facts(self.FIRST), CANONICAL_TEMPLATE).body
        body = body.replace("Why the work started.", "Reviewer-rewritten problem statement.")
        body = body.replace(
            "- `ops/a.py` — feat: first (+1 more)", "- `ops/a.py` — hand-written why"
        )
        body = body.replace(
            "<!-- EVIDENCE:END -->", "<!-- EVIDENCE:END -->\n\nManual: ran the soak for 2h."
        )
        return body.replace(
            "See Changes by intent and Protected-root (if any additive_only path).",
            "Look hardest at the retry loop.",
        )

    def test_refresh_moves_paths_and_keeps_reviewer_text(self) -> None:
        reviewed = self._reviewed()
        self.assertIn("hand-written why", reviewed)
        later = _facts(self.LATER, head="b" * 40)
        body, status = refresh_body(reviewed, later)
        self.assertEqual(status, "updated")
        for kept in (
            "Reviewer-rewritten problem statement.",
            "Look hardest at the retry loop.",
            "Manual: ran the soak for 2h.",
            "- `ops/a.py` — hand-written why",
        ):
            self.assertIn(kept, body)
        self.assertNotIn("`ops/b.py`", body)
        self.assertIn("- `ops/c.py` — ", body)
        self.assertIn("- `old/x.py -> new/x.py` — ", body)
        self.assertEqual(check_inventory(body, [parse_row(r) for r in self.LATER]), ([], []))

    def test_refresh_is_idempotent(self) -> None:
        later = _facts(self.LATER, head="b" * 40)
        once, _ = refresh_body(self._reviewed(), later)
        twice, status = refresh_body(once, later)
        self.assertEqual(status, "unchanged")
        self.assertEqual(twice, once)
        remote_once, _ = refresh_body(once, _facts(self.LATER, head="c" * 40), remote=True)
        remote_twice, status = refresh_body(
            remote_once, _facts(self.LATER, head="c" * 40), remote=True
        )
        self.assertEqual(status, "unchanged")
        self.assertEqual(remote_twice, remote_once)

    def test_unmanaged_body_is_never_edited(self) -> None:
        human = "## Problem\n\nWritten by a person, no template.\n"
        self.assertEqual(refresh_body(human, _facts(self.LATER)), (human, "unmanaged"))
        # An older-template body a person wrote: only its inventory region moves.
        older = (
            "## Changes by intent\n\n- `ops/a.py` — mine\n\n## Files touched\n\n"
            "<!-- FILES-TOUCHED:START -->\n_pending_\n<!-- FILES-TOUCHED:END -->\n"
        )
        body, status = refresh_body(older, _facts(self.LATER))
        self.assertEqual(status, "updated")
        self.assertIn("- `ops/a.py` — mine\n\n## Files touched", body)
        self.assertIn("- `c.py` — added", body)

    def test_remote_refresh_marks_unmeasured_head_stale_and_never_claims(self) -> None:
        composed = compose_pr_body(
            _facts(
                self.FIRST,
                gate_receipt={"schema": "l9.pr_gate_receipt.v2", "content_digest": "d1"},
            ),
            CANONICAL_TEMPLATE,
        ).body
        pushed = _facts(self.LATER, head="b" * 40)
        body, _ = refresh_body(composed, pushed, remote=True)
        evidence = region_content(body, REGION_EVIDENCE) or ""
        self.assertIn(f"STALE: receipts below were composed at {'a' * 40}", evidence)
        self.assertIn(f"PR head is now {'b' * 40}", evidence)
        self.assertIn("content_digest=d1", evidence)  # history kept, not deleted
        # A remote refresh of the head the receipts were composed at changes nothing.
        same, _ = refresh_body(composed, _facts(self.FIRST), remote=True)
        self.assertEqual(
            region_content(same, REGION_EVIDENCE), region_content(composed, REGION_EVIDENCE)
        )
        # A later make pr at the new head replaces the stale block with measurements.
        measured, _ = refresh_body(
            body,
            _facts(
                self.LATER,
                head="b" * 40,
                gate_receipt={"schema": "l9.pr_gate_receipt.v2", "content_digest": "d2"},
            ),
        )
        fresh = region_content(measured, REGION_EVIDENCE) or ""
        self.assertNotIn("STALE", fresh)
        self.assertIn("content_digest=d2", fresh)

    def test_protected_root_paths_refresh_only_when_measured(self) -> None:
        composed = compose_pr_body(_facts(self.FIRST), CANONICAL_TEMPLATE).body
        touched = _facts(["M\tAGENTS.md"], additive_only_paths=["AGENTS.md"])
        remote, _ = refresh_body(composed, touched, remote=True)
        self.assertEqual(
            region_content(remote, REGION_PROTECTED_PATHS), "- N/A — no additive_only root files"
        )
        local, _ = refresh_body(composed, touched)
        self.assertEqual(region_content(local, REGION_PROTECTED_PATHS), "- `AGENTS.md`")
        self.assertIn(PROTECTED_STAMP, local)

    def test_legacy_composer_body_is_migrated_once(self) -> None:
        legacy = "\n".join(
            [
                COMPOSER_MARKER,
                "## Problem",
                "",
                "Something broke.",
                "",
                "## Evidence",
                "",
                "```",
                "gate-receipt.json present: schema=x content_digest=1",
                "```",
                "",
                "## Changes by intent",
                "",
                "**Modified**",
                "- `ops/a.py` — reviewer prose from before regions",
                "- `ops/b.py` — about to disappear",
                "",
                "## Files touched",
                "",
                "<!-- FILES-TOUCHED:START -->",
                "**2 files**",
                "<!-- FILES-TOUCHED:END -->",
                "",
                "## Commits",
                "",
                "- feat: first",
                "",
                "## Test plan",
                "",
                "- [x] `make pr` local gate receipt present",
                "",
                "## Changed files",
                "",
                "- M\tops/a.py",
                "- A\tops/b.py",
                "",
            ]
        )
        later = _facts(self.LATER, head="b" * 40)
        body, status = refresh_body(legacy, later, remote=True)
        self.assertEqual(status, "migrated")
        for gone in ("## Commits", "## Test plan", "## Changed files", "`ops/b.py`"):
            self.assertNotIn(gone, body)
        self.assertIn("- `ops/a.py` — reviewer prose from before regions", body)
        self.assertIn("Something broke.", body)
        self.assertIn("STALE: receipts below were composed at an unrecorded head", body)
        self.assertEqual(check_inventory(body, [parse_row(r) for r in self.LATER]), ([], []))
        self.assertEqual(refresh_body(body, later, remote=True), (body, "unchanged"))


class InventoryGuardTests(unittest.TestCase):
    """F7 negative controls: each guard fails a known-bad body and passes the fix."""

    ROWS = ["M\tops/a.py", "A\tops/b.py", "R100\told/x.py\tnew/x.py"]

    def test_stale_body_after_out_of_band_push_fails_until_refreshed(self) -> None:
        rows = [parse_row(r) for r in self.ROWS]
        stale = compose_pr_body(_facts(self.ROWS[:1]), CANONICAL_TEMPLATE).body
        undeclared, phantom = check_inventory(stale, rows)
        self.assertEqual(undeclared, ["ops/b.py", "old/x.py -> new/x.py"])
        self.assertEqual(phantom, [])
        fixed, _ = refresh_body(stale, _facts(self.ROWS))
        self.assertEqual(check_inventory(fixed, rows), ([], []))

    def test_truncated_or_phantom_inventory_fails(self) -> None:
        rows = [parse_row(r) for r in self.ROWS]
        good = compose_pr_body(_facts(self.ROWS), CANONICAL_TEMPLATE).body
        self.assertEqual(check_inventory(good, rows), ([], []))
        truncated = re.sub(r"^- `ops/b.py` — .*\n", "", good, flags=re.M)
        self.assertEqual(check_inventory(truncated, rows), (["ops/b.py"], []))
        phantom = good.replace("- `ops/a.py` — ", "- `ops/ghost.py` — x\n- `ops/a.py` — ", 1)
        self.assertEqual(check_inventory(phantom, rows), ([], ["ops/ghost.py"]))
        # A rename declared by its endpoint alone is both missing and phantom.
        endpoint = good.replace("`old/x.py -> new/x.py`", "`new/x.py`")
        self.assertEqual(check_inventory(endpoint, rows), (["old/x.py -> new/x.py"], ["new/x.py"]))


class TemplateResolutionTests(unittest.TestCase):
    """B4/D2/F2: one canonical template, at one exact org commit, or an error."""

    SHA = "1" * 40

    def _gh(self, template: str, calls: list[str]):
        encoded = __import__("base64").b64encode(template.encode()).decode()

        def gh(endpoint: str) -> object:
            calls.append(endpoint)
            if endpoint == "repos/Quantum-L9/.github":
                return {"default_branch": "main"}
            if endpoint == "repos/Quantum-L9/.github/commits/main":
                return {"sha": self.SHA}
            if endpoint.startswith("repos/Quantum-L9/.github/contents/"):
                return {"type": "file", "encoding": "base64", "content": encoded}
            raise TemplateError(f"unexpected {endpoint}")

        return gh

    def test_consumer_copy_is_ignored_and_revision_is_exact(self) -> None:
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".github").mkdir()
            (workspace / ".github" / "pull_request_template.md").write_text("## Divergent\n")
            source = resolve_template(
                workspace, "Quantum-L9", "consumer", gh=self._gh(CANONICAL_TEMPLATE, calls)
            )
        self.assertEqual(source.text, CANONICAL_TEMPLATE)
        self.assertEqual(source.revision, f"Quantum-L9/.github@{self.SHA}")
        self.assertIn(
            f"repos/Quantum-L9/.github/contents/.github/pull_request_template.md?ref={self.SHA}",
            calls,
        )
        facts = _facts(["M\tops/a.py"], template_revision=source.revision)
        body = compose_pr_body(facts, source.text).body
        self.assertIn(f"<!-- l9-pr-template: Quantum-L9/.github@{self.SHA} -->", body)
        self.assertNotIn("## Divergent", body)

    def test_unreachable_or_invalid_template_fails_closed(self) -> None:
        def down(endpoint: str) -> object:
            raise TemplateError(f"gh api {endpoint} failed: HTTP 502")

        with self.assertRaises(TemplateError):
            resolve_template(Path("."), "Quantum-L9", "consumer", gh=down)
        broken = CANONICAL_TEMPLATE.replace("## Files touched", "## Files")
        with self.assertRaisesRegex(TemplateError, "missing heading '## Files touched'"):
            resolve_template(Path("."), "Quantum-L9", "consumer", gh=self._gh(broken, []))
        with self.assertRaises(TemplateError):
            resolve_template(Path("."), "", "consumer", gh=self._gh(CANONICAL_TEMPLATE, []))

    def test_org_repository_composes_from_its_own_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _Repo(Path(tmp))
            repo.write(".github/pull_request_template.md", CANONICAL_TEMPLATE)
            repo.commit("template")
            head = repo.git("rev-parse", "HEAD").strip()
            # Uncommitted bytes are not the PR's template.
            repo.write(".github/pull_request_template.md", "## Scratch\n")

            def no_network(endpoint: str) -> object:
                raise AssertionError(f"the org repo must not fetch itself: {endpoint}")

            source = resolve_template(repo.root, "Quantum-L9", ".github", gh=no_network)
        self.assertEqual(source.text, CANONICAL_TEMPLATE)
        self.assertEqual(source.revision, f"Quantum-L9/.github@{head}")

    def test_vendored_canonical_template_is_valid_and_passes_org_gate(self) -> None:
        self.assertEqual(validate_template(CANONICAL_TEMPLATE), [])
        for name in (REGION_PROTECTED_PATHS, REGION_EVIDENCE, REGION_INTENT, REGION_FILES):
            self.assertIsNotNone(region_content(CANONICAL_TEMPLATE, name), name)
        facts = MechanicalFacts(
            commits=["fix(pr): canonical regions"],
            commit_bodies=["The body drifted from the diff after later pushes."],
            changed_files=list(OrgPrGateContractTests.NAME_STATUS),
            gate_receipt={"schema": "l9.pr_gate_receipt.v2", "content_digest": "d"},
        )
        body = compose_pr_body(facts, CANONICAL_TEMPLATE).body
        result = _run_org_validator("governance-pr.yml", body)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["findings"], [])


class CliTests(unittest.TestCase):
    """The modes governance-pr.yml and make pr call, end to end."""

    def test_remote_refresh_and_check_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _Repo(Path(tmp) / "repo")
            repo.write("a.py", "a\n")
            repo.commit("base")
            repo.git("checkout", "-q", "-b", "feat")
            repo.write("b.py", "b\n")
            repo.commit("feat: add b")
            facts = collect_mechanical(repo.root, pr_base="main")
            first = compose_pr_body(facts, CANONICAL_TEMPLATE).body
            repo.write("c.py", "c\n")
            repo.commit("feat: add c from another client")
            body_file = Path(tmp) / "body.md"
            body_file.write_text(first, encoding="utf-8")

            def run(*extra: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        sys.executable,
                        str(COMPOSER),
                        "--workspace",
                        str(repo.root),
                        "--pr-base",
                        "main",
                        *extra,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=repo.env,
                )

            stale = run("--check-body", str(body_file))
            self.assertEqual(stale.returncode, 1)
            self.assertIn("UNDECLARED: c.py", stale.stderr)
            status = Path(tmp) / "status.json"
            refreshed = run(
                "--refresh-body", str(body_file), "--remote", "--status-file", str(status)
            )
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertEqual(json.loads(status.read_text())["status"], "updated")
            self.assertIn("- `c.py` — feat: add c from another client", refreshed.stdout)
            self.assertIn("STALE:", refreshed.stdout)
            body_file.write_text(refreshed.stdout, encoding="utf-8")
            self.assertEqual(run("--check-body", str(body_file)).returncode, 0)
            again = run("--refresh-body", str(body_file), "--remote", "--status-file", str(status))
            self.assertEqual(json.loads(status.read_text())["status"], "unchanged")
            self.assertEqual(again.stdout, refreshed.stdout)


if __name__ == "__main__":
    unittest.main()
