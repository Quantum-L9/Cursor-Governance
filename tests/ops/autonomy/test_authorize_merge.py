"""Tests for ops/autonomy/authorize_merge.py — human merge grants (§6.2.12, §6.2.13).

A grant is one repository, one PR, one exact head, expiring, issuer ``human``.
It is written after a human confirms the target on a terminal, or — as
``--operator-instruction`` — after the host-recorded operator instruction is
verified against the live pull request and the operator's repository authority.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "ops" / "autonomy" / "authorize_merge.py"
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import authorize_merge  # noqa: E402
import operator_merge_instruction as omi  # noqa: E402
from authorize_merge import MAX_TTL_SECONDS, write_authorization  # noqa: E402
from merge_gate import grant_matches  # noqa: E402

SHA = "abcdef1234567890abcdef1234567890abcdef12"
MOVED = "0" * 40
SLUG = "Quantum-L9/Cursor-Governance"
NOW = 1_800_000_000


#: The session's GitHub identity as fetch_session_principal reports it: the
#: operator's own account, repository admin.
OWNER = {"login": "cryptoxdog", "type": "User", "permission": "admin", "human": True}


def _grant(path: Path, **overrides) -> dict:
    kwargs = {
        "repo": SLUG,
        "pr": "42",
        "head_sha": SHA,
        "reason": "reviewed",
        "path": path,
        "now": 1_000_000,
        "ttl_seconds": 100,
    }
    kwargs.update(overrides)
    return write_authorization(**kwargs)


def test_grant_binds_repo_pr_head_issuer_and_expiry(tmp_path: Path) -> None:
    path = tmp_path / "merge-authorization.json"
    entry = _grant(path, head_sha=SHA.upper())
    assert entry == {
        "repo": SLUG,
        "pr": 42,
        "head_sha": SHA,
        "issuer": "human",
        "issued_at": 1_000_000,
        "expires_at": 1_000_100,
        "reason": "reviewed",
    }
    assert json.loads(path.read_text(encoding="utf-8"))["authorizations"] == [entry]


def test_written_grant_is_one_the_gate_accepts(tmp_path: Path) -> None:
    """Issuer and gate agree on the schema: what one writes, the other matches."""
    entry = _grant(tmp_path / "auth.json")
    assert grant_matches(entry, SLUG, "42", SHA, now=1_000_050)
    assert not grant_matches(entry, SLUG, "42", SHA, now=1_000_100)  # expired
    assert not grant_matches(entry, SLUG, "43", SHA, now=1_000_050)  # other PR
    assert not grant_matches(entry, SLUG, "42", "b" * 40, now=1_000_050)  # moved head


def test_replaces_same_pr_and_keeps_others(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    _grant(path, reason="first")
    _grant(path, reason="second")
    _grant(path, repo="Quantum-L9/SEO-Bot", reason="other")
    entries = json.loads(path.read_text(encoding="utf-8"))["authorizations"]
    assert [(e["repo"], e["reason"]) for e in entries] == [
        (SLUG, "second"),
        ("Quantum-L9/SEO-Bot", "other"),
    ]


@pytest.mark.parametrize("pr", ["*", "all", "", "0", "x"])
def test_repository_wide_scope_is_not_issuable(tmp_path: Path, pr: str) -> None:
    with pytest.raises(ValueError, match="not issuable"):
        _grant(tmp_path / "auth.json", pr=pr)


@pytest.mark.parametrize("sha", ["", "zzzz", "abcdef1", "a" * 39])
def test_head_must_be_a_full_sha(tmp_path: Path, sha: str) -> None:
    with pytest.raises(ValueError, match="40-hex"):
        _grant(tmp_path / "auth.json", head_sha=sha)


def test_rejects_bad_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="owner/name"):
        _grant(tmp_path / "auth.json", repo="not-a-repo")


@pytest.mark.parametrize("ttl", [0, -1, MAX_TTL_SECONDS + 1])
def test_ttl_must_be_positive_and_bounded(tmp_path: Path, ttl: int) -> None:
    with pytest.raises(ValueError, match="expire|exceed"):
        _grant(tmp_path / "auth.json", ttl_seconds=ttl)


# --- issuance: a human at a terminal, never an agent --------------------------


def _cli(tmp_path: Path, *extra: str) -> list[str]:
    return ["--repo", SLUG, "--auth-file", str(tmp_path / "auth.json"), *extra]


def test_cli_without_a_terminal_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """An agent tool shell has no controlling terminal: self-issuance fails."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *_cli(tmp_path, "--pr", "42", "--head-sha", SHA)],
        capture_output=True,
        text=True,
        input="Quantum-L9/Cursor-Governance#42@abcdef123456\n",  # piped stdin is not a tty
        start_new_session=True,  # detach from any controlling terminal
        check=False,
    )
    assert proc.returncode == authorize_merge.NOT_CONFIRMED_EXIT, proc.stderr
    assert "MERGE_PENDING" in proc.stderr
    assert not (tmp_path / "auth.json").exists()


@pytest.mark.parametrize("extra", [("--all-open",), ("--pr", "*"), ()])
def test_cli_refuses_repository_wide_authority(tmp_path: Path, extra: tuple[str, ...]) -> None:
    asked: list[str] = []
    code = authorize_merge.main(
        _cli(tmp_path, *extra, "--head-sha", SHA), confirm=lambda t: asked.append(t) or True
    )
    assert code == 2
    assert asked == []  # refused before any confirmation is even requested
    assert not (tmp_path / "auth.json").exists()


def test_cli_wrong_confirmation_refuses(tmp_path: Path) -> None:
    code = authorize_merge.main(
        _cli(tmp_path, "--pr", "42", "--head-sha", SHA), confirm=lambda _t: False
    )
    assert code == authorize_merge.NOT_CONFIRMED_EXIT
    assert not (tmp_path / "auth.json").exists()


def test_cli_confirmed_by_human_writes_bound_grant(tmp_path: Path) -> None:
    seen: list[str] = []

    def confirm(token: str) -> bool:
        seen.append(token)
        return True

    code = authorize_merge.main(_cli(tmp_path, "--pr", "42", "--head-sha", SHA), confirm=confirm)
    assert code == 0
    assert seen == [f"{SLUG}#42@{SHA[:12]}"]
    (entry,) = json.loads((tmp_path / "auth.json").read_text(encoding="utf-8"))["authorizations"]
    assert (entry["repo"], entry["pr"], entry["head_sha"], entry["issuer"]) == (
        SLUG,
        42,
        SHA,
        "human",
    )
    assert entry["provenance"] == {"channel": authorize_merge.TERMINAL_CHANNEL}


# --- issuance: the operator's recorded prompt (§6.2.13) ------------------------


def _instructions(tmp_path: Path, prompt: str = f"Fix and merge {SLUG}#42.", **kw) -> Path:
    """A receipt as the Claude UserPromptSubmit wrapper writes it, with the
    host transcript carrying the same human turn."""
    store = tmp_path / "operator-merge-instructions.json"
    transcript = tmp_path / "transcript.jsonl"
    record = {
        "type": "user",
        "sessionId": "sess-1",
        "turnOrigin": "human",
        "origin": {"kind": "human"},
        "message": {"role": "user", "content": prompt},
    }
    with transcript.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    payload = {
        "session_id": "sess-1",
        "transcript_path": str(transcript),
        "cwd": "/ws",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    defaults = {
        "host": "claude-code",
        "session_id": "sess-1",
        "path": store,
        "now": NOW,
        "provenance": omi.host_provenance("claude-code", payload),
        "open_pull_requests": lambda repo: [42, 700],
    }
    defaults.update(kw)
    omi.record_instructions(prompt, cwd_repo=None, **defaults)
    return store


def _view(
    *,
    sha: str = SHA,
    state: str = "open",
    merged: bool = False,
    created_at: str = "2026-10-14T19:19:43Z",
    author: str = "cryptoxdog",
) -> dict:
    return {
        "state": state,
        "merged": merged,
        "created_at": created_at,
        "head": {"sha": sha},
        "user": {"login": author},
    }


def _operator_main(
    tmp_path: Path,
    store: Path,
    *,
    view: dict | None = None,
    principal: dict | None = None,
    principal_error: str | None = None,
    view_error: str | None = None,
    extra: tuple[str, ...] = (),
    now: int = NOW + 60,
) -> int:
    def pull_request(repo: str, pr: int) -> dict:
        assert (repo, pr) == (SLUG, 42)
        if view_error:
            raise RuntimeError(view_error)
        return view if view is not None else _view()

    def session_principal(repo: str) -> dict:
        assert repo == SLUG
        if principal_error:
            raise RuntimeError(principal_error)
        return principal if principal is not None else OWNER

    return authorize_merge.main(
        _cli(tmp_path, "--operator-instruction", "--pr", "42", "--head-sha", SHA, *extra),
        confirm=lambda _t: pytest.fail("operator mode must never ask a terminal"),
        instruction_path=store,
        pull_request=pull_request,
        session_principal=session_principal,
        now=now,
    )


def _grants(tmp_path: Path) -> list[dict]:
    path = tmp_path / "auth.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["authorizations"]


def test_operator_instruction_writes_a_scoped_grant_with_provenance(tmp_path: Path) -> None:
    """Positive 1 + 2: an explicit prompt becomes a grant without a terminal."""
    store = _instructions(tmp_path)
    assert _operator_main(tmp_path, store) == 0
    (entry,) = _grants(tmp_path)
    assert (entry["repo"], entry["pr"], entry["head_sha"], entry["issuer"]) == (
        SLUG,
        42,
        SHA,
        "human",
    )
    assert entry["expires_at"] - entry["issued_at"] == authorize_merge.DEFAULT_TTL_SECONDS
    prov = entry["provenance"]
    assert prov["channel"] == authorize_merge.OPERATOR_CHANNEL
    assert prov["recorded_by"] == "agent"
    assert (prov["host"], prov["session_id"], prov["scope"]) == ("claude-code", "sess-1", "pr")
    assert prov["instruction_id"] == omi.load_instructions(store)[0]["id"]
    assert prov["prompt_sha256"] == omi.prompt_digest(f"Fix and merge {SLUG}#42.")
    assert "merge" in prov["excerpt"]
    assert prov["pull_request_author"] == "cryptoxdog"
    assert grant_matches(entry, SLUG, "42", SHA, now=NOW + 120)


def test_operator_grant_never_outlives_the_instruction(tmp_path: Path) -> None:
    store = _instructions(tmp_path)
    late = NOW + omi.DEFAULT_TTL_SECONDS - 300
    assert _operator_main(tmp_path, store, now=late) == 0
    (entry,) = _grants(tmp_path)
    assert entry["expires_at"] == NOW + omi.DEFAULT_TTL_SECONDS


def test_operator_mode_without_an_instruction_refuses(tmp_path: Path, capsys) -> None:
    store = tmp_path / "operator-merge-instructions.json"  # never written
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []
    out = capsys.readouterr()
    record = json.loads(out.out)
    assert record["status"] == "MERGE_PENDING"
    assert "no live operator merge instruction" in record["reason"]
    assert "REFUSED" in out.err


def test_agent_written_instruction_text_is_not_a_recorded_instruction(tmp_path: Path) -> None:
    """Negative 2: a file an agent wrote has no recorder stamp and binds nothing."""
    store = tmp_path / "operator-merge-instructions.json"
    store.write_text(
        json.dumps(
            {
                "schema": omi.SCHEMA,
                "instructions": [
                    {
                        "id": "a" * 16,
                        "host": "claude-code",
                        "session_id": "sess-1",
                        "recorded_at": NOW,
                        "expires_at": NOW + 3600,
                        "scope": "pr",
                        "repo": SLUG,
                        "pr": 42,
                        "excerpt": "merge PR #42",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []


def test_operator_mode_wrong_repository_refuses(tmp_path: Path) -> None:
    store = _instructions(tmp_path, prompt="Fix and merge Quantum-L9/SEO-Bot#42.")
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []


def test_operator_mode_wrong_pull_request_refuses(tmp_path: Path) -> None:
    store = _instructions(tmp_path, prompt=f"Fix and merge {SLUG}#43.")
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []


def test_operator_mode_expired_instruction_refuses(tmp_path: Path, capsys) -> None:
    store = _instructions(tmp_path)
    code = _operator_main(tmp_path, store, now=NOW + omi.DEFAULT_TTL_SECONDS + 1)
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    assert "expired" in json.loads(capsys.readouterr().out)["reason"]
    assert _grants(tmp_path) == []


def test_operator_mode_moved_head_refuses_but_keeps_the_task_alive(tmp_path: Path, capsys) -> None:
    """Negative 7 / positive 4: the old head binds nothing; the instruction still covers the PR."""
    store = _instructions(tmp_path)
    code = _operator_main(tmp_path, store, view=_view(sha=MOVED))
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    reason = json.loads(capsys.readouterr().out)["reason"]
    assert "head moved" in reason and MOVED in reason
    assert _grants(tmp_path) == []
    # The same instruction authorizes the final head once it is the live one.
    live = authorize_merge.main(
        _cli(tmp_path, "--operator-instruction", "--pr", "42", "--head-sha", MOVED),
        instruction_path=store,
        pull_request=lambda repo, pr: _view(sha=MOVED),
        session_principal=lambda repo: OWNER,
        now=NOW + 120,
    )
    assert live == 0
    (entry,) = _grants(tmp_path)
    assert entry["head_sha"] == MOVED
    assert entry["provenance"]["instruction_id"] == omi.load_instructions(store)[0]["id"]


def test_operator_mode_closed_or_merged_pull_request_refuses(tmp_path: Path) -> None:
    store = _instructions(tmp_path)
    assert (
        _operator_main(tmp_path, store, view=_view(state="closed"))
        == authorize_merge.OPERATOR_REFUSED_EXIT
    )
    assert (
        _operator_main(tmp_path, store, view=_view(state="closed", merged=True))
        == authorize_merge.OPERATOR_REFUSED_EXIT
    )
    assert _grants(tmp_path) == []


def test_operator_mode_unreadable_pull_request_refuses(tmp_path: Path, capsys) -> None:
    """Negative 10: a verifier that cannot run grants nothing."""
    store = _instructions(tmp_path)
    code = _operator_main(tmp_path, store, view_error="HTTP 503")
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    assert "cannot verify the live pull request" in json.loads(capsys.readouterr().out)["reason"]
    store2 = _instructions(tmp_path)
    code = _operator_main(tmp_path, store2, principal_error="HTTP 503")
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []


def test_cohort_instruction_grants_each_pull_request_open_at_the_time(tmp_path: Path) -> None:
    """Positive 5 / negative 8: a cohort resolves into scoped grants for the pull
    requests in the recorder's snapshot, never for one that was not open then."""
    prompt = f"Remediate and merge all currently open PRs in {SLUG}."
    store = _instructions(tmp_path, prompt=prompt, open_pull_requests=lambda repo: [42, 700])
    assert _operator_main(tmp_path, store) == 0
    (entry,) = _grants(tmp_path)
    assert entry["provenance"]["scope"] == "open_cohort"
    assert entry["provenance"]["cohort_members"] == [42, 700]
    (tmp_path / "auth.json").unlink()
    store = _instructions(tmp_path, prompt=prompt, open_pull_requests=lambda repo: [700])
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []


def test_operator_may_authorize_their_own_pull_request_on_protected_paths(
    tmp_path: Path,
) -> None:
    """§6.2.14 / L9-ORG-007 as amended: an authorized owner's chat instruction is the
    authorization, even when the owner authored the pull request and it touches
    governance-protected paths. No second human, no GitHub comment."""
    store = _instructions(tmp_path)
    assert _operator_main(tmp_path, store, view=_view(author="cryptoxdog")) == 0
    (entry,) = _grants(tmp_path)
    assert entry["provenance"]["pull_request_author"] == "cryptoxdog"
    assert entry["provenance"]["authorizer_login"] == "cryptoxdog"
    assert entry["provenance"]["authorizer_permission"] == "admin"


@pytest.mark.parametrize(
    "principal",
    [
        {"login": "drive-by", "type": "User", "permission": "read", "human": True},
        {"login": "triager", "type": "User", "permission": "triage", "human": True},
        {"login": "someone", "type": "User", "permission": "", "human": True},
        {"login": "github-actions[bot]", "type": "Bot", "permission": "write", "human": False},
    ],
)
def test_operator_without_repository_authority_cannot_authorize(
    tmp_path: Path, capsys, principal: dict
) -> None:
    """A person (or bot) without write authority over the repository authorizes nothing."""
    store = _instructions(tmp_path)
    code = _operator_main(tmp_path, store, principal=principal)
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    reason = json.loads(capsys.readouterr().out)["reason"]
    assert "outside the operator's authorized scope" in reason
    assert _grants(tmp_path) == []


def test_operator_authority_that_cannot_be_read_fails_closed(tmp_path: Path, capsys) -> None:
    store = _instructions(tmp_path)
    code = _operator_main(tmp_path, store, principal_error="HTTP 403")
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    assert "cannot verify the operator's authority" in json.loads(capsys.readouterr().out)["reason"]
    assert _grants(tmp_path) == []


def test_refusal_never_prescribes_magic_wording(tmp_path: Path, capsys) -> None:
    store = tmp_path / "empty.json"
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    reason = json.loads(capsys.readouterr().out)["reason"]
    assert "no particular wording is required" in reason
    assert "authorize merge " not in reason


def test_operator_mode_cli_subprocess_needs_no_terminal(tmp_path: Path) -> None:
    """Run the real CLI detached from any terminal; only the verifiers are offline here."""
    store = _instructions(tmp_path)
    argv = _cli(tmp_path, "--operator-instruction", "--pr", "42", "--head-sha", SHA)
    driver = tmp_path / "driver.py"
    driver.write_text(
        "\n".join(
            [
                "import sys",
                f"sys.path.insert(0, {str(REPO / 'ops' / 'autonomy')!r})",
                "import authorize_merge",
                "from pathlib import Path",
                "code = authorize_merge.main(",
                f"    {argv!r},",
                f"    instruction_path=Path({str(store)!r}),",
                f"    pull_request=lambda r, p: {_view()!r},",
                f"    session_principal=lambda r: {OWNER!r},",
                f"    now={NOW + 60},",
                ")",
                "raise SystemExit(code)",
            ]
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(driver)],
        capture_output=True,
        text=True,
        start_new_session=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["provenance"]["channel"] == "operator_prompt"


# --- GAR-MERGE-AUTHORITY-735 findings: the grant writer validates provenance ------


def _transcript(path: Path, text: str, *, origin: str = "human", session: str = "sess-1") -> Path:
    record = {
        "type": "user",
        "userType": "external",
        "isSidechain": False,
        "sessionId": session,
        "turnOrigin": origin,
        "origin": {"kind": origin.replace("_", "-")},
        "promptSource": "sdk" if origin == "human" else "system",
        "message": {"role": "user", "content": text},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def _hosted(
    tmp_path: Path,
    prompt: str = f"Fix and merge {SLUG}#42.",
    *,
    now: int = NOW,
    transcript_text: str | None = None,
    origin: str = "human",
    store: Path | None = None,
    open_pull_requests=None,
) -> Path:
    """A receipt the Claude UserPromptSubmit wrapper would have written."""
    store = store or tmp_path / "operator-merge-instructions.json"
    transcript = _transcript(tmp_path / f"t-{now}.jsonl", transcript_text or prompt, origin=origin)
    payload = {
        "session_id": "sess-1",
        "transcript_path": str(transcript),
        "cwd": "/ws",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }
    omi.record_instructions(
        prompt,
        host="claude-code",
        session_id="sess-1",
        cwd="/ws",
        path=store,
        now=now,
        cwd_repo=None,
        provenance=omi.host_provenance("claude-code", payload),
        open_pull_requests=open_pull_requests,
    )
    return store


def test_f01_hosted_receipt_still_becomes_a_grant(tmp_path: Path) -> None:
    store = _hosted(tmp_path)
    assert _operator_main(tmp_path, store) == 0
    (entry,) = _grants(tmp_path)
    prov = entry["provenance"]
    assert prov["channel"] == authorize_merge.OPERATOR_CHANNEL
    assert prov["hook_event_name"] == "UserPromptSubmit"
    assert prov["transcript_path"].endswith(".jsonl")


def test_f01_receipt_not_corroborated_by_the_transcript_is_refused(tmp_path: Path, capsys) -> None:
    """The receipt names a transcript whose human turns never said this."""
    store = _hosted(tmp_path, transcript_text="Review PR #42 and report.")
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []
    assert "transcript" in json.loads(capsys.readouterr().out)["reason"]


def test_f01_relayed_turn_in_the_transcript_does_not_corroborate(tmp_path: Path) -> None:
    store = _hosted(tmp_path, origin="task_notification")
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []


def test_f01_cursor_host_is_blocked_host_origin(tmp_path: Path, capsys) -> None:
    store = tmp_path / "operator-merge-instructions.json"
    payload = {
        "conversation_id": "conv-1",
        "generation_id": "gen-1",
        "workspace_roots": ["/ws"],
        "hook_event_name": "beforeSubmitPrompt",
        "prompt": f"Fix and merge {SLUG}#42.",
    }
    omi.record_instructions(
        f"Fix and merge {SLUG}#42.",
        host="cursor",
        session_id="conv-1",
        path=store,
        now=NOW,
        cwd_repo=None,
        provenance=omi.host_provenance("cursor", payload),
    )
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert omi.BLOCKED_HOST_ORIGIN in json.loads(capsys.readouterr().out)["reason"]
    assert _grants(tmp_path) == []


def test_f03_revocation_before_grant_refuses(tmp_path: Path, capsys) -> None:
    store = _hosted(tmp_path, now=NOW)
    _hosted(tmp_path, f"Do not merge {SLUG}#42.", now=NOW + 30, store=store)
    assert _operator_main(tmp_path, store) == authorize_merge.OPERATOR_REFUSED_EXIT
    assert "revoked" in json.loads(capsys.readouterr().out)["reason"]
    assert _grants(tmp_path) == []


def test_f03_reauthorization_after_revocation_grants(tmp_path: Path) -> None:
    store = _hosted(tmp_path, now=NOW)
    _hosted(tmp_path, f"Do not merge {SLUG}#42.", now=NOW + 30, store=store)
    _hosted(tmp_path, f"Merge {SLUG}#42 after all.", now=NOW + 45, store=store)
    assert _operator_main(tmp_path, store) == 0
    assert len(_grants(tmp_path)) == 1


def test_f04_cohort_grant_requires_snapshot_membership(tmp_path: Path, capsys) -> None:
    prompt = f"Remediate and merge all currently open PRs in {SLUG}."
    store = _hosted(tmp_path, prompt, open_pull_requests=lambda repo: [42, 700])
    assert _operator_main(tmp_path, store, view=_view(created_at="2026-10-14T19:19:43Z")) == 0
    (entry,) = _grants(tmp_path)
    assert entry["provenance"]["scope"] == "open_cohort"
    # A PR that existed earlier but was not open at instruction time
    store2 = _hosted(tmp_path, prompt, now=NOW + 5, open_pull_requests=lambda repo: [700])
    (tmp_path / "auth.json").unlink()
    code = _operator_main(tmp_path, store2, view=_view(created_at="2026-10-01T00:00:00Z"))
    assert code == authorize_merge.OPERATOR_REFUSED_EXIT
    assert _grants(tmp_path) == []
    capsys.readouterr()
