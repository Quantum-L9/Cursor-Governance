"""A recording in-memory GitHub REST double for handoff delivery tests.

It answers exactly the endpoints ``ops/reports/handoff_delivery.py`` calls, with
the shapes GitHub documents (issue comments list/create/update, repository
issues list/create). Anything else is a test failure, not a silent pass.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from ops.reports.handoff_delivery import TransportError


class FakeGitHub:
    def __init__(self) -> None:
        self.comments: dict[tuple[str, int], list[dict[str, Any]]] = {}
        self.issues: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[tuple[str, str]] = []
        self.refuse: set[str] = set()  # repositories whose every call fails
        self._next = 1000

    def _id(self) -> int:
        self._next += 1
        return self._next

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        self.calls.append((method, path))
        bare, _, query = path.partition("?")
        match = re.match(r"repos/([^/]+/[^/]+)/(.*)$", bare)
        if not match:
            raise AssertionError(f"unexpected path {path}")
        repo, rest = match.group(1), match.group(2)
        if repo in self.refuse:
            raise TransportError(f"{method} {path}: HTTP 403 not enabled for this session")
        page = int(dict(p.split("=") for p in query.split("&") if p).get("page", "1"))
        if method == "GET" and (m := re.fullmatch(r"issues/(\d+)/comments", rest)):
            return list(self.comments.get((repo, int(m.group(1))), [])) if page == 1 else []
        if method == "POST" and (m := re.fullmatch(r"issues/(\d+)/comments", rest)):
            assert body is not None
            comment = {
                "id": self._id(),
                "body": body["body"],
                "html_url": f"https://github.com/{repo}/issues/{m.group(1)}#c",
            }
            self.comments.setdefault((repo, int(m.group(1))), []).append(comment)
            return comment
        if method == "PATCH" and (m := re.fullmatch(r"issues/comments/(\d+)", rest)):
            assert body is not None
            for thread in self.comments.values():
                for comment in thread:
                    if comment["id"] == int(m.group(1)):
                        comment["body"] = body["body"]
                        return comment
            raise TransportError("HTTP 404")
        if method == "GET" and rest == "issues":
            return list(self.issues.get(repo, [])) if page == 1 else []
        if method == "POST" and rest == "issues":
            assert body is not None
            number = len(self.issues.get(repo, [])) + 1
            issue = {
                "number": number,
                "title": body["title"],
                "body": body["body"],
                "html_url": f"https://github.com/{repo}/issues/{number}",
            }
            self.issues.setdefault(repo, []).append(issue)
            return issue
        raise AssertionError(f"unexpected call {method} {path}")

    def thread(self, repo: str, number: int) -> list[dict[str, Any]]:
        return self.comments.get((repo, number), [])


@pytest.fixture()
def github() -> FakeGitHub:
    return FakeGitHub()
