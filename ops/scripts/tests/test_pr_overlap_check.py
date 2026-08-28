"""Overlap-gate tests (PR_OVERLAP_GUARDRAIL_V1).

Runs ops/scripts/pr_overlap_check.py against throwaway repos with a local bare
"origin" (refs/pull/<N>/head updated in place) and a fake `gh` shim on PATH that
serves canned pulls/files payloads. Runnable as unittest or pytest.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "pr_overlap_check.py"
SLUG = "test-o/test-n"

SHARED_BASE = "line1\nline2\nline3\nline4\n"


def _git_env(path: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = path + os.pathsep + env.get("PATH", "")
    env["GIT_AUTHOR_NAME"] = "Tester"
    env["GIT_AUTHOR_EMAIL"] = "t@example.com"
    env["GIT_COMMITTER_NAME"] = "Tester"
    env["GIT_COMMITTER_EMAIL"] = "t@example.com"
    return env


def _run(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, check=False)
    if result.returncode != 0:
        raise AssertionError(f"command failed ({' '.join(args)}): {result.stdout}\n{result.stderr}")
    return result


def _commit(repo: Path, env: dict[str, str], message: str) -> None:
    _run(["git", "add", "-A"], repo, env)
    _run(["git", "commit", "-q", "-m", message], repo, env)


class FakeGh:
    """gh shim: --version ok; repo view → FAKE_SLUG; api → canned files."""

    def __init__(
        self, dirpath: Path, pulls: str, files: dict[str, str], unavailable: bool = False
    ) -> None:
        self.unavailable = unavailable
        self.pulls = pulls
        self.files = files
        self.path = dirpath / "gh"
        self.path.write_text(
            "#!/usr/bin/env python3\nimport os, re, sys\n"
            "args = sys.argv[1:]\n"
            'if "--version" in args or args[:1] == ["--version"]:\n'
            '    sys.exit(1 if os.environ.get("FAKE_GH_UNAVAILABLE") == "1" else 0)\n'
            'if "repo" in args:\n'
            '    print(os.environ.get("FAKE_SLUG", "")); sys.exit(0)\n'
            'if args[:1] == ["api"]:\n'
            '    joined = " ".join(args)\n'
            '    m = re.search(r"pulls/(\\d+)/files", joined)\n'
            "    if m:\n"
            '        key = "FAKE_FILES_%s" % m.group(1)\n'
            '        print(os.environ.get(key, os.environ.get("FAKE_FILES", ""))); sys.exit(0)\n'
            '    print(os.environ.get("FAKE_PULLS", "")); sys.exit(0)\n'
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        self.path.chmod(0o755)

    def env(self, base_env: dict[str, str]) -> dict[str, str]:
        env = dict(base_env)
        env["PATH"] = str(self.path.parent) + os.pathsep + env.get("PATH", "")
        env["FAKE_SLUG"] = SLUG
        env["FAKE_PULLS"] = self.pulls
        for key, value in self.files.items():
            env[f"FAKE_FILES_{key}"] = value
        if self.unavailable:
            env["FAKE_GH_UNAVAILABLE"] = "1"
        return env


def _init_world() -> tuple[Path, Path, dict[str, str]]:
    """bare origin + cloned work repo on feat-ours, shared identity env."""
    raw = Path(tempfile.mkdtemp(prefix="l9-overlap-"))
    bare = raw / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, capture_output=True
    )
    work = raw / "work"
    base_env = _git_env(str(raw))
    _run(["git", "clone", "-q", str(bare), str(work)], raw, base_env)
    _run(["git", "config", "user.name", "Tester"], work, base_env)
    _run(["git", "config", "user.email", "t@example.com"], work, base_env)
    (work / "shared.txt").write_text(SHARED_BASE, encoding="utf-8")
    _commit(work, base_env, "base")
    _run(["git", "push", "-q", "-u", "origin", "main"], work, base_env)
    return bare, work, base_env


def _branch_from(work: Path, env: dict[str, str], start: str, name: str, mutate) -> str:
    """Create branch <name> from <start> with mutate() applied, push, return its sha."""
    _run(["git", "checkout", "-q", start], work, env)
    _run(["git", "checkout", "-q", "-b", name], work, env)
    mutate(work)
    _commit(work, env, name)
    _run(["git", "push", "-q", "-u", "origin", name], work, env)
    return subprocess.run(
        ["git", "rev-parse", name], cwd=work, capture_output=True, text=True, env=env, check=True
    ).stdout.strip()


def _gate(
    work: Path, env: dict[str, str], extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    gate_env = dict(env)
    # Host make pr may export PR_OVERLAP=ignore; default the fixture to block
    # unless the test sets an explicit extra_env value.
    gate_env["PR_OVERLAP"] = "block"
    if extra_env:
        gate_env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(GATE), "--workspace", str(work), "--base", "origin/main"],
        cwd=work,
        capture_output=True,
        text=True,
        env=gate_env,
        check=False,
    )


class PrOverlapCheckTests(unittest.TestCase):
    def _world_with_their_pr(self, fake: FakeGh, their_change) -> tuple[Path, Path, dict[str, str]]:
        bare, work, env = _init_world()
        # their PR branch
        sha = _branch_from(work, env, "main", "feat-theirs", their_change)
        subprocess.run(
            ["git", "update-ref", "refs/pull/1/head", sha], cwd=bare, env=env, check=True
        )
        # our branch
        _run(["git", "checkout", "-q", "main"], work, env)
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "shared.txt").write_text(
            SHARED_BASE.replace("line2", "line2-ours"), encoding="utf-8"
        )
        _commit(work, env, "ours")
        return bare, work, env

    @staticmethod
    def _conflict_their(work: Path) -> None:
        (work / "shared.txt").write_text(
            SHARED_BASE.replace("line2", "line2-theirs"), encoding="utf-8"
        )

    @staticmethod
    def _disjoint_their(work: Path) -> None:
        (work / "shared.txt").write_text(
            SHARED_BASE.replace("line4", "line4-theirs"), encoding="utf-8"
        )

    def test_no_open_prs_passes(self) -> None:
        bare, work, env = _init_world()
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "ours.txt").write_text("x\n", encoding="utf-8")
        _commit(work, env, "ours")
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_https_remote_slug_resolves_from_url_alone(self) -> None:
        """Regression: https:// remote URLs must parse owner/name without any
        gh repo view call (GraphQL can be down — live run exposed this)."""
        bare, work, env = _init_world()
        _run(["git", "remote", "set-url", "origin", f"https://github.com/{SLUG}.git"], work, env)
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "ours.txt").write_text("x\n", encoding="utf-8")
        _commit(work, env, "ours")
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        gate_env = fake.env(env)
        gate_env["FAKE_SLUG"] = ""  # repo view would yield nothing — URL parse must carry it
        result = _gate(work, gate_env)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)
        self.assertNotIn("cannot resolve owner/repo", result.stdout)

    def test_empty_pr_overlap_env_defaults_to_block(self) -> None:
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": "shared.txt\n"},
        )
        bare, work, env = self._world_with_their_pr(fake, self._conflict_their)
        result = _gate(work, fake.env(env), extra_env={"PR_OVERLAP": ""})
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("BLOCK", result.stdout)
        self.assertNotIn("unknown PR_OVERLAP", result.stdout)

    def test_generated_only_overlap_passes(self) -> None:
        bare, work, env = _init_world()
        gen = "ops/generated/skill-registry.json"
        sha = _branch_from(
            work,
            env,
            "main",
            "feat-theirs",
            lambda w: (
                (w / gen).parent.mkdir(parents=True, exist_ok=True)
                or (w / gen).write_text('{"skills": ["theirs"]}\n', encoding="utf-8")
            ),
        )
        subprocess.run(
            ["git", "update-ref", "refs/pull/1/head", sha], cwd=bare, env=env, check=True
        )
        _run(["git", "checkout", "-q", "main"], work, env)
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / gen).parent.mkdir(parents=True, exist_ok=True)
        (work / gen).write_text('{"skills": ["ours"]}\n', encoding="utf-8")
        _commit(work, env, "ours")
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": f"{gen}\n"},
        )
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_textual_conflict_blocks_and_names_pr(self) -> None:
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": "shared.txt\n"},
        )
        bare, work, env = self._world_with_their_pr(fake, self._conflict_their)
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("PR #1", result.stdout)
        self.assertIn("feat-theirs", result.stdout)
        self.assertIn("shared.txt", result.stdout)
        self.assertIn("PR_STACK=auto", result.stdout)
        self.assertIn("PR_OVERLAP=ignore", result.stdout)

    def test_conflict_outside_our_changed_files_does_not_block(self) -> None:
        """A conflict in a file this branch never touched is not this branch's.

        Their PR conflicts with main in other.txt while both PRs also touch
        shared.txt disjointly. Publishing our branch cannot cause their
        other.txt conflict -- each PR merges into main separately -- so the gate
        must report it and proceed rather than blocking us for their collision.
        """
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": "shared.txt\nother.txt\n"},
        )
        bare, work, env = _init_world()

        # main gains other.txt, then moves it on -- their branch will diverge.
        (work / "other.txt").write_text("alpha\n", encoding="utf-8")
        _commit(work, env, "add other")
        _run(["git", "push", "-q", "origin", "main"], work, env)

        def their_change(repo: Path) -> None:
            (repo / "shared.txt").write_text(
                SHARED_BASE.replace("line4", "line4-theirs"), encoding="utf-8"
            )
            (repo / "other.txt").write_text("theirs\n", encoding="utf-8")

        sha = _branch_from(work, env, "main", "feat-theirs", their_change)
        subprocess.run(
            ["git", "update-ref", "refs/pull/1/head", sha], cwd=bare, env=env, check=True
        )

        # main moves other.txt again, so their PR now conflicts with main there.
        _run(["git", "checkout", "-q", "main"], work, env)
        (work / "other.txt").write_text("omega\n", encoding="utf-8")
        _commit(work, env, "move other")
        _run(["git", "push", "-q", "origin", "main"], work, env)

        # our branch touches shared.txt only, disjointly from theirs
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "shared.txt").write_text(
            SHARED_BASE.replace("line2", "line2-ours"), encoding="utf-8"
        )
        _commit(work, env, "ours")

        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("does not touch", result.stdout)

    def test_disjoint_hunks_pass_with_note(self) -> None:
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": "shared.txt\n"},
        )
        bare, work, env = self._world_with_their_pr(fake, self._disjoint_their)
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("disjoint hunks", result.stdout)

    def test_warn_mode_exits_zero(self) -> None:
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": "shared.txt\n"},
        )
        bare, work, env = self._world_with_their_pr(fake, self._conflict_their)
        result = _gate(work, fake.env(env), extra_env={"PR_OVERLAP": "warn"})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("WARN: PR overlap", result.stdout)

    def test_ignore_mode_skips(self) -> None:
        bare, work, env = _init_world()
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        result = _gate(work, fake.env(env), extra_env={"PR_OVERLAP": "ignore"})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("overlap gate skipped", result.stdout)

    def test_gh_unavailable_denies_autonomous_publication(self) -> None:
        """E6: no gh means no collision state, and no collision state means no push.

        This gate used to skip itself whenever it could not see GitHub -- switching
        off at exactly the moment an autonomous agent could overwrite a sibling's
        work. Under autonomy it now blocks; only the push is affected.
        """
        bare, work, env = _init_world()
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={}, unavailable=True)
        gate_env = {**fake.env(env), "L9_AUTONOMY_ENABLED": "true"}
        result = _gate(work, gate_env)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("gh CLI unavailable", result.stdout)
        self.assertIn("publication is denied", result.stdout)
        self.assertIn("Local work is unaffected", result.stdout)

    def test_gh_unavailable_may_be_overridden_explicitly(self) -> None:
        """A human may accept the risk, but must say so."""
        bare, work, env = _init_world()
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={}, unavailable=True)
        gate_env = {
            **fake.env(env),
            "L9_AUTONOMY_ENABLED": "true",
            "PR_OVERLAP_TELEMETRY": "open",
        }
        result = _gate(work, gate_env)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PR_OVERLAP_TELEMETRY=open", result.stdout)

    def test_gh_api_failure_denies_autonomous_publication(self) -> None:
        """gh present but the pulls call fails (network loss).

        The open-PR set is unknown, so overlap is unknown, so publication is
        denied under autonomy (E6) rather than proceeding blind.
        """
        shimdir = Path(tempfile.mkdtemp(prefix="l9-gh-"))
        shim = shimdir / "gh"
        shim.write_text(
            "#!/usr/bin/env python3\nimport os, sys\nargs = sys.argv[1:]\n"
            'if "--version" in args:\n    sys.exit(0)\n'
            'if "repo" in args:\n    print(os.environ.get("FAKE_SLUG", "")); sys.exit(0)\n'
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        shim.chmod(0o755)
        bare, work, env = _init_world()
        gate_env = _git_env(str(shimdir))
        gate_env["FAKE_SLUG"] = SLUG
        gate_env["L9_AUTONOMY_ENABLED"] = "true"
        result = _gate(work, gate_env)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("could not enumerate open PRs", result.stdout)
        self.assertIn("publication is denied", result.stdout)

    def test_auto_stack_single_pr_prints_stack_base(self) -> None:
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls="1\tfeat-theirs\tmain\n",
            files={"1": "shared.txt\n"},
        )
        bare, work, env = self._world_with_their_pr(fake, self._conflict_their)
        result = _gate(work, fake.env(env), extra_env={"PR_STACK": "auto"})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("STACK_BASE=feat-theirs", result.stdout)

    def test_auto_stack_chain_uses_top_pr(self) -> None:
        bare, work, env = _init_world()
        # PR1 conflicts with us; PR2 stacks on PR1's head and inherits the conflict.
        sha1 = _branch_from(work, env, "main", "feat-theirs", self._conflict_their)
        subprocess.run(
            ["git", "update-ref", "refs/pull/1/head", sha1], cwd=bare, env=env, check=True
        )
        sha2 = _branch_from(
            work,
            env,
            "feat-theirs",
            "feat-theirs-2",
            lambda w: (w / "other.txt").write_text("top\n", encoding="utf-8"),
        )
        subprocess.run(
            ["git", "update-ref", "refs/pull/2/head", sha2], cwd=bare, env=env, check=True
        )
        _run(["git", "checkout", "-q", "main"], work, env)
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "shared.txt").write_text(
            SHARED_BASE.replace("line2", "line2-ours"), encoding="utf-8"
        )
        _commit(work, env, "ours")
        pulls = "1\tfeat-theirs\tmain\n2\tfeat-theirs-2\tfeat-theirs\n"
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls=pulls,
            files={"1": "shared.txt\n", "2": "shared.txt\n"},
        )
        result = _gate(work, fake.env(env), extra_env={"PR_STACK": "auto"})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("STACK_BASE=feat-theirs-2", result.stdout)

    def test_auto_stack_ambiguous_siblings_block(self) -> None:
        bare, work, env = _init_world()
        sha1 = _branch_from(work, env, "main", "feat-theirs", self._conflict_their)
        subprocess.run(
            ["git", "update-ref", "refs/pull/1/head", sha1], cwd=bare, env=env, check=True
        )
        sha3 = _branch_from(
            work,
            env,
            "main",
            "feat-other",
            lambda w: (w / "shared.txt").write_text(
                SHARED_BASE.replace("line2", "line2-other"), encoding="utf-8"
            ),
        )
        subprocess.run(
            ["git", "update-ref", "refs/pull/3/head", sha3], cwd=bare, env=env, check=True
        )
        _run(["git", "checkout", "-q", "main"], work, env)
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "shared.txt").write_text(
            SHARED_BASE.replace("line2", "line2-ours"), encoding="utf-8"
        )
        _commit(work, env, "ours")
        pulls = "1\tfeat-theirs\tmain\n3\tfeat-other\tmain\n"
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")),
            pulls=pulls,
            files={"1": "shared.txt\n", "3": "shared.txt\n"},
        )
        result = _gate(work, fake.env(env), extra_env={"PR_STACK": "auto"})
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("BLOCK", result.stdout)

    def test_own_open_pr_is_not_an_overlap(self) -> None:
        bare, work, env = _init_world()
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "ours.txt").write_text("x\n", encoding="utf-8")
        _commit(work, env, "ours")
        fake = FakeGh(
            Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="1\tfeat-ours\tmain\n", files={}
        )
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)


class BaseConflictProbeTests(unittest.TestCase):
    """The #319 class: a branch duplicating work already merged into its base.

    The open-PR probe is structurally blind to it — merged work is not an open
    PR, so with nothing else open the gate returned PASS before ever comparing
    the branch against its own base. These fail on the open-PRs-only gate.
    """

    @staticmethod
    def _duplicate_feature_world() -> tuple[Path, dict[str, str]]:
        """main gains feature.txt; a stale branch adds the same path differently."""
        _bare, work, env = _init_world()
        # Fork BEFORE the feature lands — the stale-fork condition.
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        # Meanwhile the feature merges into main.
        _run(["git", "checkout", "-q", "main"], work, env)
        (work / "feature.txt").write_text("their implementation\n", encoding="utf-8")
        _commit(work, env, "feature lands on main")
        _run(["git", "push", "-q", "origin", "main"], work, env)
        # The stale branch independently implements the same file.
        _run(["git", "checkout", "-q", "feat-ours"], work, env)
        (work / "feature.txt").write_text("our parallel implementation\n", encoding="utf-8")
        _commit(work, env, "our parallel implementation")
        _run(["git", "fetch", "-q", "origin"], work, env)
        return work, env

    def test_duplicate_of_already_merged_work_blocks(self) -> None:
        work, env = self._duplicate_feature_world()
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("conflicts with its own base", result.stdout)
        self.assertIn("feature.txt", result.stdout)

    def test_base_conflict_warns_without_blocking_in_warn_mode(self) -> None:
        work, env = self._duplicate_feature_world()
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        result = _gate(work, fake.env(env), {"PR_OVERLAP": "warn"})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("conflicts with its own base", result.stdout)

    def test_branch_disjoint_from_base_still_passes(self) -> None:
        """No false positive: ordinary work on a moved base must not block."""
        _bare, work, env = _init_world()
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        (work / "ours.txt").write_text("ours\n", encoding="utf-8")
        _commit(work, env, "ours")
        _run(["git", "checkout", "-q", "main"], work, env)
        (work / "theirs.txt").write_text("theirs\n", encoding="utf-8")
        _commit(work, env, "unrelated work lands on main")
        _run(["git", "push", "-q", "origin", "main"], work, env)
        _run(["git", "checkout", "-q", "feat-ours"], work, env)
        _run(["git", "fetch", "-q", "origin"], work, env)
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_generated_only_base_conflict_does_not_block(self) -> None:
        """Generated paths self-resolve via the keep-ours driver at the base too.

        Same add/add shape as the blocking case, on a GENERATED_PATH_PREFIXES
        path — the base probe must exempt it exactly as the open-PR probe does.
        """
        generated = "environment/generated/llm-rules/00-global.md"
        _bare, work, env = _init_world()
        _run(["git", "checkout", "-q", "-b", "feat-ours"], work, env)
        _run(["git", "checkout", "-q", "main"], work, env)
        target = work / generated
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("regenerated on main\n", encoding="utf-8")
        _commit(work, env, "generated artifact lands on main")
        _run(["git", "push", "-q", "origin", "main"], work, env)
        _run(["git", "checkout", "-q", "feat-ours"], work, env)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("regenerated on our branch\n", encoding="utf-8")
        _commit(work, env, "our regeneration of the same artifact")
        _run(["git", "fetch", "-q", "origin"], work, env)
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={})
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("conflicts with its own base", result.stdout)


if __name__ == "__main__":
    unittest.main()
