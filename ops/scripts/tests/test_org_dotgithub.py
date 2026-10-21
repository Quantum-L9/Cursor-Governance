"""org_dotgithub: the single reader of ``<owner>/.github``, over REST then git."""

from __future__ import annotations

import base64
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import org_dotgithub  # noqa: E402
from org_dotgithub import OrgFileError, read_org_file  # noqa: E402

SHA = "2" * 40
PATH = ".github/pull_request_template.md"


def rest(text: str, calls: list[str]):
    encoded = base64.b64encode(text.encode()).decode()

    def gh(endpoint: str) -> object:
        calls.append(endpoint)
        if endpoint == "repos/Quantum-L9/.github":
            return {"default_branch": "main"}
        if endpoint == "repos/Quantum-L9/.github/commits/main":
            return {"sha": SHA}
        if endpoint == f"repos/Quantum-L9/.github/contents/{PATH}?ref={SHA}":
            return {"type": "file", "encoding": "base64", "content": encoded}
        raise OrgFileError(f"unexpected {endpoint}")

    return gh


def scoped(endpoint: str) -> object:
    raise OrgFileError(f"gh api {endpoint} failed: not enabled for this session (HTTP 403)")


class ReadOrgFileTests(unittest.TestCase):
    def test_rest_first_and_git_untouched_when_rest_answers(self) -> None:
        def no_git(owner: str, path: str) -> tuple[str, str]:
            raise AssertionError("git transport used while REST answered")

        calls: list[str] = []
        got = read_org_file("Quantum-L9", PATH, gh=rest("body", calls), git=no_git)
        self.assertEqual((got.sha, got.text, got.transport), (SHA, "body", "rest"))
        self.assertIn(f"repos/Quantum-L9/.github/contents/{PATH}?ref={SHA}", calls)

    def test_scoped_rest_reads_the_same_path_over_git(self) -> None:
        asked: list[tuple[str, str]] = []

        def git(owner: str, path: str) -> tuple[str, str]:
            asked.append((owner, path))
            return SHA, "body"

        got = read_org_file("Quantum-L9", PATH, gh=scoped, git=git)
        self.assertEqual(asked, [("Quantum-L9", PATH)])
        self.assertEqual((got.sha, got.text, got.transport), (SHA, "body", "git"))

    def test_both_transports_down_fails_closed_naming_both(self) -> None:
        def git_down(owner: str, path: str) -> tuple[str, str]:
            raise OrgFileError("git ls-remote failed")

        with self.assertRaisesRegex(OrgFileError, r"HTTP 403.*git transport also failed"):
            read_org_file("Quantum-L9", PATH, gh=scoped, git=git_down)

    def test_git_read_pins_the_head_commit_and_reads_that_commit(self) -> None:
        """git_read against a local bare 'org repo', with the github.com URL rewritten to it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()

            def git(*args: str, cwd: Path = work) -> str:
                return subprocess.run(
                    ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
                ).stdout

            git("init", "-q", "-b", "main")
            git("config", "user.email", "t@example.com")
            git("config", "user.name", "t")
            (work / ".github").mkdir()
            (work / PATH).write_text("pinned\n")
            git("add", ".")
            git("commit", "-q", "-m", "template")
            head = git("rev-parse", "HEAD").strip()
            bare = root / "Quantum-L9" / ".github"
            bare.parent.mkdir()
            git("clone", "-q", "--bare", str(work), str(bare), cwd=root)
            config = root / "gitconfig"
            config.write_text(
                f'[url "file://{root}/"]\n\tinsteadOf = https://github.com/\n'
                '[protocol "file"]\n\tallow = always\n'
            )
            with mock.patch.dict("os.environ", {"GIT_CONFIG_GLOBAL": str(config)}):
                sha, text = org_dotgithub.git_read("Quantum-L9", PATH)
        self.assertEqual((sha, text), (head, "pinned\n"))


class SingleReaderTests(unittest.TestCase):
    """Every read of <owner>/.github goes through org_dotgithub, so none can lose the git route."""

    PATTERN = re.compile(
        r"repos/(\{owner\}|\$\{?owner\}?|\$\{?OWNER\}?|Quantum-L9|\{org\}|\$\{?org\}?)/\.github"
        r"(?=[/\"'?\s]|$)"
    )

    def test_no_other_module_reads_the_org_repo_over_rest(self) -> None:
        offenders = []
        for root in ("ops", "hooks", "environment", "skills"):
            for path in (REPO / root).rglob("*"):
                if path.suffix not in {".py", ".sh", ".mk"} or not path.is_file():
                    continue
                if "tests" in path.parts or path.name == "org_dotgithub.py":
                    continue
                for number, line in enumerate(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    if self.PATTERN.search(line):
                        offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
        self.assertEqual(
            offenders,
            [],
            "read <owner>/.github through org_dotgithub.read_org_file (REST, then git); "
            "a REST-only read fails on session gateways that scope the API to the "
            "session's own repositories",
        )


if __name__ == "__main__":
    unittest.main()
