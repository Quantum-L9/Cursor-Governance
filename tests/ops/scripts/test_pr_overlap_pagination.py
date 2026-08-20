"""REST listing pagination for the PR overlap gate.

`gh api --paginate` follows the response Link header, and GitHub writes those
links in numeric-id form (`repositories/<id>/pulls/<n>/files?page=2`). An agent
proxy that only permits `repos/<owner>/<repo>/...` answers that with 403, so gh
exits non-zero, the gate reads it as undeterminable collision state, and every
publish behind a >100-file PR is blocked with no collision anywhere. These tests
pin the explicit-page-number fetch that keeps each request on the owner/repo
path, and the fail-closed behavior that must survive it.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
OVERLAP = ROOT / "ops" / "scripts" / "pr_overlap_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("pr_overlap_check", OVERLAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def overlap():
    return _load()


class FakeGh:
    """Records the API paths requested and answers from a canned page map."""

    def __init__(self, pages: dict[int, list[str]], fail_on: int | None = None) -> None:
        self.pages = pages
        self.fail_on = fail_on
        self.paths: list[str] = []

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        path = args[1]
        self.paths.append(path)
        page = int(path.rsplit("page=", 1)[1])
        if page == self.fail_on:
            return subprocess.CompletedProcess(list(args), 1, "", "HTTP 403")
        body = "\n".join(self.pages.get(page, []))
        return subprocess.CompletedProcess(list(args), 0, body + ("\n" if body else ""), "")


def test_every_request_uses_the_owner_repo_path(overlap, monkeypatch) -> None:
    """The proxy rejects numeric-id paths, so none may be requested."""
    fake = FakeGh({1: [f"file{index}.py" for index in range(100)], 2: ["last.py"]})
    monkeypatch.setattr(overlap, "gh", fake)

    files = overlap.pr_files("owner/repo", 236)

    assert files is not None and len(files) == 101
    assert len(fake.paths) == 2
    for path in fake.paths:
        assert path.startswith("repos/owner/repo/"), path
        assert "repositories/" not in path


def test_short_first_page_stops_immediately(overlap, monkeypatch) -> None:
    fake = FakeGh({1: ["a.py", "b.py"]})
    monkeypatch.setattr(overlap, "gh", fake)

    assert overlap.pr_files("owner/repo", 12) == ["a.py", "b.py"]
    assert len(fake.paths) == 1, "a partial page means there is no next page"


def test_exactly_one_full_page_checks_the_next(overlap, monkeypatch) -> None:
    """100 files could mean 100 or 100-of-many; the gate must look."""
    fake = FakeGh({1: [f"file{index}.py" for index in range(100)], 2: []})
    monkeypatch.setattr(overlap, "gh", fake)

    files = overlap.pr_files("owner/repo", 12)

    assert files is not None and len(files) == 100
    assert len(fake.paths) == 2


def test_failed_page_is_telemetry_failure_not_a_short_list(overlap, monkeypatch) -> None:
    """A truncated list would silently under-report overlap. None blocks."""
    fake = FakeGh({1: [f"file{index}.py" for index in range(100)], 2: ["x.py"]}, fail_on=2)
    monkeypatch.setattr(overlap, "gh", fake)

    assert overlap.pr_files("owner/repo", 236) is None


def test_cap_with_a_still_full_page_fails_closed(overlap, monkeypatch) -> None:
    full = [f"file{index}.py" for index in range(100)]
    fake = FakeGh({page: full for page in range(1, overlap._MAX_PAGES + 2)})
    monkeypatch.setattr(overlap, "gh", fake)

    assert overlap.pr_files("owner/repo", 236) is None, "no silent truncation"
    assert len(fake.paths) == overlap._MAX_PAGES


def test_open_prs_paginates_the_same_way(overlap, monkeypatch) -> None:
    rows = [f"{number}\tfeat/b{number}\tmain" for number in range(100)]
    fake = FakeGh({1: rows, 2: ["999\tfeat/last\tmain"]})
    monkeypatch.setattr(overlap, "gh", fake)

    prs = overlap.open_prs("owner/repo")

    assert prs is not None and len(prs) == 101
    assert prs[-1] == {"number": 999, "head": "feat/last", "base": "main"}
    for path in fake.paths:
        assert path.startswith("repos/owner/repo/pulls?state=open&per_page="), path


def test_open_prs_query_keeps_its_existing_parameters(overlap, monkeypatch) -> None:
    """The page parameters must join an existing query string, not replace it."""
    fake = FakeGh({1: ["1\tfeat/a\tmain"]})
    monkeypatch.setattr(overlap, "gh", fake)

    overlap.open_prs("owner/repo")

    assert "state=open" in fake.paths[0]
    assert fake.paths[0].count("?") == 1


def test_failed_pr_listing_is_none(overlap, monkeypatch) -> None:
    monkeypatch.setattr(overlap, "gh", FakeGh({1: ["1\tfeat/a\tmain"]}, fail_on=1))
    assert overlap.open_prs("owner/repo") is None


def test_module_does_not_use_link_header_pagination() -> None:
    """Regression guard: Link-header pagination reintroduces the numeric-id 403.

    Matches the argument form (a quoted string literal passed to gh), not the
    bare word — the docstring explaining why it is gone must not trip this.
    """
    source = OVERLAP.read_text(encoding="utf-8")
    flag_literal = '"--' + 'paginate"'
    code = [line for line in source.splitlines() if flag_literal in line]
    assert not code, f"Link-header pagination is back in a code path: {code}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
