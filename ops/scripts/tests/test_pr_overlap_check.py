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

    def test_gh_unavailable_fails_open(self) -> None:
        bare, work, env = _init_world()
        fake = FakeGh(Path(tempfile.mkdtemp(prefix="l9-gh-")), pulls="", files={}, unavailable=True)
        result = _gate(work, fake.env(env))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("WARN: gh CLI unavailable", result.stdout)

    def test_gh_api_failure_fails_open(self) -> None:
        """gh present but the pulls call fails (network loss) — must not brick make pr."""
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
        result = _gate(work, gate_env)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("WARN: could not list open PRs", result.stdout)

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


if __name__ == "__main__":
    unittest.main()
