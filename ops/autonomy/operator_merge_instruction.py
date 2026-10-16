#!/usr/bin/env python3
"""Operator merge instructions, recorded by the host's prompt-submission hook.

CANONICAL_LAW §6.2.13 (operator-prompt channel). The human who types a prompt is
the authorizer of the merges that prompt explicitly orders; the agent records
and executes that authority. This module is the recorder and the reader:

* ``record`` runs **only** inside a host prompt hook — Claude Code
  ``UserPromptSubmit`` or Cursor ``beforeSubmitPrompt`` — on the payload the host
  delivered. It records one receipt per explicit instruction into
  ``~/.l9/autonomy/operator-merge-instructions.json`` together with the hook's
  own provenance (event name, session, transcript path). A payload without that
  provenance records nothing, and ``merge_gate.py`` denies an agent tool call
  that runs this recorder, its host adapters, or writes the receipt file.
* ``find_instruction`` answers whether a live, unrevoked receipt covers one
  repository and one pull request. ``authorize_merge.py --operator-instruction``
  turns that into a head-bound grant after rechecking the live pull request and
  the receipt's provenance; ``merge_gate.py`` binds the receipt to the live
  session before letting that run proceed.

What is recognised: an **affirmative instruction directed at the agent**, in
the imperative or first person, naming its pull request:

    merge PR #735 after the checks pass
    fix and merge Quantum-L9/Cursor-Governance#735
    I authorize the merge of PR #735
    remediate and merge all currently open PRs in Quantum-L9/Cursor-Governance

and an **explicit cancellation**, which revokes the authority above:

    do not merge PR #735 after all
    cancel the merge of #735
    do not merge any open PRs in Quantum-L9/Cursor-Governance

What is not an instruction: a question, a verb with no pull-request object,
text inside quotation marks, code fences, block quotes or ``<pasted_content>``,
material introduced by a colon ("the report says: …"), a third-person report
("the reviewer recommends that we merge …"), and any prompt carrying a host
relay marker (a scheduled task firing, a subagent reporting back, a
cross-session message, a webhook payload). Clauses are read independently, so
"don't merge #735, but merge #736" revokes one and authorizes the other.

A cohort instruction ("all currently open PRs in <owner/name>") must name the
repository. At recording time the recorder lists the repository's open pull
requests through the GitHub REST path and stores that membership; a pull
request not in the snapshot — opened later, or closed at the time and reopened
since — is outside the cohort, and a snapshot that could not be taken covers
nothing. It is never standing repository-wide authority.

Assurance, stated plainly. A receipt proves two things the agent cannot
produce through a gated tool call: the host prompt hook wrote it with the
hook's own provenance, and a human turn of the same session in the host-written
transcript carries the same text (Claude Code records ``turnOrigin: "human"``
on a typed prompt and ``task_notification`` on a relayed one; that field was
observed on 2026-10-15, it is not a documented contract, and its absence fails
closed). It is not cryptographic proof of who typed it, it does not establish a
GitHub identity (L9-ORG-007 protected changes still need the GitHub record),
and a worker that runs arbitrary code as the same OS account could forge the
store and the transcript alike — the §6.2.12 item 7 gap. Cursor exposes no
PreToolUse merge gate and no transcript this module can read, so a Cursor
receipt is recorded for audit but never becomes a grant: BLOCKED_HOST_ORIGIN.

Metadata:
  layer: ops
  role: merge_authorization
  version: 2.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA = "l9.operator-merge-instruction.v1"
INSTRUCTION_FILE_NAME = "operator-merge-instructions.json"
#: An instruction outlives the grants it backs (grants expire within four
#: hours) so authorized remediation can re-issue a head-specific grant without
#: a repeated approval. After this the operator must say it again. A revocation
#: lives as long, so it outlives everything it revokes.
DEFAULT_TTL_SECONDS = 8 * 60 * 60
MAX_RECORDS = 64
EXCERPT_CHARS = 300
HOSTS = ("claude-code", "cursor")
#: The prompt-submission event each host fires; the payload names it.
HOST_EVENTS = {"claude-code": "UserPromptSubmit", "cursor": "beforeSubmitPrompt"}
RECORDER = "host_prompt_hook"
KIND_AUTHORIZE = "authorize"
KIND_REVOKE = "revoke"
KINDS = (KIND_AUTHORIZE, KIND_REVOKE)
#: Hosts whose receipts can be bound to a live session and corroborated by a
#: host-written transcript. Cursor is not one yet (see module docstring).
GRANTABLE_HOSTS = ("claude-code",)
BLOCKED_HOST_ORIGIN = "BLOCKED_HOST_ORIGIN"
#: Transcript ``turnOrigin`` / ``origin.kind`` values that mean a person typed it.
HUMAN_TURN_ORIGINS = frozenset({"human"})
_GH_TIMEOUT_SECONDS = 6

_SLUG = r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"
_SLUG_RE = re.compile(rf"(?<![\w/.@-])(?P<slug>{_SLUG})(?![\w/-])")
_GITHUB_URL_RE = re.compile(rf"https?://github\.com/(?P<slug>{_SLUG})(?:/|\b)", re.I)
#: One pull-request reference: ``owner/name#12``, ``#12``, ``PR 12``,
#: ``pull request #12`` or a github.com pull URL.
_PR_REF = re.compile(
    rf"(?:(?P<qualified>{_SLUG})#"
    rf"|https?://github\.com/(?P<url>{_SLUG})/pull/"
    r"|(?:pull[\s-]*requests?|prs?)\s*#?\s*"
    r"|#)"
    r"(?P<num>[1-9]\d*)\b",
    re.I,
)
_REF_SEPARATOR = r"(?:\s*(?:,|and|&|then)\s*)"
_PR_REF_ANON = re.sub(r"\(\?P<\w+>", "(?:", _PR_REF.pattern)
_REF_RUN = re.compile(
    rf"(?:{_PR_REF_ANON})(?:{_REF_SEPARATOR}(?:{_PR_REF_ANON}))*",
    re.I,
)
_MERGE_VERB = re.compile(r"\bmerg(?:e|es|ing)\b", re.I)
#: Words that may sit between the verb and its object: "merge of PR #1",
#: "merge the PRs #1 and #2". "merge and close PR #3" is deliberately NOT glue.
_GLUE = re.compile(
    r"^(?:\s*(?:(?:of|the|both|all|these|those|then|also|now|please|and\s+(?:then|also))\b"
    r"|them\s*:|,|&))*\s*",
    re.I,
)
#: A cancellation names its object through more words: "cancel the merge
#: authorization for #1", "withdraw my merge instruction on #2".
_REVOKE_GLUE = re.compile(
    r"^(?:\s*(?:(?:of|for|on|to|the|a|an|my|your|our|this|that|both|all|these|those|"
    r"authori[sz]ations?|instructions?|grants?|approvals?|requests?|orders?|commands?|"
    r"go-ahead)\b|them\s*:|,|&))*\s*",
    re.I,
)
#: What may precede the verb in an instruction directed at the agent: a
#: politeness or sequencing word, a permission ("you may"), a first-person
#: authorization ("I authorize the"), or a chain of coordinated verbs ("fix and",
#: "remediate, test and"). A third-person subject ("the report recommends that
#: we merge") never matches: the word before ``merge`` must be a coordinator.
_LEAD_IN = (
    r"(?:please|now|then|also|next|finally|just|kindly|and|&|ok|okay|yes|"
    r"go\s+ahead\s+and|"
    r"you\s+(?:may|can|should|must|are\s+(?:authori[sz]ed|cleared|free)\s+to)|"
    r"i\s+(?:authori[sz]e|approve|want|need|would\s+like|am\s+authori[sz]ing)(?:\s+you)?(?:\s+to)?|"
    r"(?:authori[sz]ation|approval|go-ahead)\s+(?:granted|given)\s*:?)"
)
_VERB_CHAIN = r"(?:[a-z][a-z-]*(?:\s*(?:,|and|&|then)\s*[a-z][a-z-]*)*\s*,?\s*(?:and|then|&)\s+)"
_DIRECTED = re.compile(
    rf"^\s*(?:{_LEAD_IN}\s+)*(?:(?:the|a|an)\s+)?(?:{_VERB_CHAIN})?(?:(?:the|a|an)\s+)?"
    r"(?:(?:eventual|final|actual|subsequent|full|clean|safe|squash)\s+)?"
    r"merg(?:e|es|ing)\b",
    re.I,
)
_COHORT_TAIL = re.compile(
    r"^(?:\s*(?:of|the|then|also|now|please|,|and\s+(?:then|also)))*"
    r"\s*(?:all\s+|any\s+|every\s+)?(?:of\s+)?(?:the\s+)?(?:currently\s+|now\s+|still\s+|remaining\s+)?"
    r"open\s+(?:pull[\s-]*requests?|prs?)\s+(?:in|of|on|for|from|under|across)\s+"
    rf"(?:the\s+)?(?:repo(?:sitory)?\s+)?(?P<repo>{_SLUG})",
    re.I,
)
#: "cancel all merges in owner/name" — a repository-wide cancellation.
_COHORT_REVOKE_SHORT = re.compile(
    rf"^\s*(?:in|for|on|across|of)\s+(?:the\s+)?(?:repo(?:sitory)?\s+)?(?P<repo>{_SLUG})",
    re.I,
)
_NEGATION = re.compile(
    r"\b(?:don'?t|do\s+not|never|not|without|no|instead\s+of|rather\s+than|stop|"
    r"avoid|refrain\s+from|cannot|can'?t|won'?t|will\s+not|must\s+not|should\s+not|"
    r"shouldn'?t|forbid(?:den)?|prohibit(?:ed)?|no\s+longer)\b(?:\s+\S+){0,2}\s+merg",
    re.I,
)
_REVOKE_VERB = re.compile(
    r"\b(?:cancel|revoke|withdraw|rescind|retract|abort|halt|stop|hold(?:\s+off)?(?:\s+on)?|"
    r"pause|freeze|suspend|undo|call\s+off)\b",
    re.I,
)
_QUESTION_LEAD = re.compile(
    r"^\s*(?:should|shall|can|could|may|might|would|will|is|are|was|were|do|does|did|"
    r"have|has|what|when|why|how|who|which|whether)\b",
    re.I,
)
#: Prompt text that the host relayed rather than a person typed. Claude Code
#: delivers these through UserPromptSubmit as well; none of them is an operator.
RELAY_MARKERS = (
    "<task-notification",
    "<wake ",
    "<event source=",
    "<webhook-payload",
    "<<autonomous-loop",
    "[artifact comment sent to claude]",
    "<standing_owner_message",
    "<child-session-event",
    "<untrusted_external_data",
    "<scheduled-task",
    "<cross-session-message",
)
_STRIP_BLOCKS = (
    re.compile(r"<pasted_content\b[^>]*>.*?</pasted_content[^>]*>", re.I | re.S),
    re.compile(r"<system-reminder\b[^>]*>.*?</system-reminder>", re.I | re.S),
    re.compile(r"```.*?```", re.S),
    re.compile(r"~~~.*?~~~", re.S),
)
#: Quoted material is being talked about, not said. Straight double quotes,
#: curly quotes, backticks, and a single-quoted *phrase* (an apostrophe inside
#: a word such as "don't" has no opening delimiter and is left alone).
_STRIP_QUOTES = (
    re.compile(r'"[^"\n]*"'),
    re.compile(r"“[^”\n]*”"),
    re.compile(r"‘[^’\n]*’"),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"(?:^|(?<=[\s:(\[,]))'[^'\n]*'(?=$|[\s.,;:!?)\]])", re.M),
)
_BLOCKQUOTE = re.compile(r"^[ \t]*>.*$", re.M)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
#: Clause boundaries inside a sentence. A colon marks presented material: what
#: follows "the report says:" is quoted, whatever its mood.
_CLAUSE_SPLIT = re.compile(
    r"\s*;\s*|:\s+|,?\s+(?:but|however|whereas|while|instead|although|except|yet)\s+|\s+[—–]\s+|\s+--\s+",
    re.I,
)


# --- prompt parsing ----------------------------------------------------------


def sanitize_prompt(text: str) -> str | None:
    """Prompt text that may carry an operator instruction, or None when relayed.

    Pasted blocks, system reminders, fenced code, block quotes and quoted spans
    are removed: text copied from a repository file, a PR comment, a report or a
    tool result is not an instruction even when the operator pasted or quoted it.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    folded = text.casefold()
    if any(marker in folded for marker in RELAY_MARKERS):
        return None
    cleaned = text
    for pattern in _STRIP_BLOCKS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = _BLOCKQUOTE.sub(" ", cleaned)
    for pattern in _STRIP_QUOTES:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


def _slug_candidates(text: str) -> list[str]:
    found: list[str] = []
    for match in _GITHUB_URL_RE.finditer(text):
        found.append(match.group("slug"))
    for match in _SLUG_RE.finditer(text):
        slug = match.group("slug")
        owner, _, name = slug.partition("/")
        # A bare "owner/name" token; path-like fragments ("ops/autonomy") read
        # the same, so a slug must look like a repository, not a directory.
        if owner.startswith(".") or name in {"", "."} or "." in owner:
            continue
        if re.search(r"\.(?:py|md|json|ya?ml|sh|toml|txt|js|ts)$", name, re.I):
            continue
        found.append(slug)
    unique: list[str] = []
    for slug in found:
        if slug.casefold() not in {item.casefold() for item in unique}:
            unique.append(slug)
    return unique


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(text) if part and part.strip()]


def _clauses(sentence: str) -> list[tuple[str, bool]]:
    """``(clause, presented)`` pairs; ``presented`` marks text after a colon."""
    parts: list[tuple[str, bool]] = []
    position = 0
    presented = False
    for match in _CLAUSE_SPLIT.finditer(sentence):
        chunk = sentence[position : match.start()].strip()
        if chunk:
            parts.append((chunk, presented))
        presented = match.group(0).strip().startswith(":")
        position = match.end()
    tail = sentence[position:].strip()
    if tail:
        parts.append((tail, presented))
    return parts


_NEGATED_LEAD = re.compile(r"\s*(?:not|n'?t)\b", re.I)


def _is_question(sentence: str) -> bool:
    """A question mark, or an inverted auxiliary ("should we merge …").

    "Do not merge …" / "Don't merge …" start with an auxiliary too but are
    negative imperatives, read as cancellations rather than skipped.
    """
    stripped = sentence.strip()
    if stripped.endswith("?"):
        return True
    lead = _QUESTION_LEAD.match(stripped)
    if not lead:
        return False
    return not _NEGATED_LEAD.match(stripped[lead.end() :])


def _is_negative(clause: str) -> bool:
    if _NEGATION.search(clause):
        return True
    return bool(_REVOKE_VERB.search(clause) and _MERGE_VERB.search(clause))


def _refs_in_run(run: str) -> list[tuple[str | None, int]]:
    refs: list[tuple[str | None, int]] = []
    for match in _PR_REF.finditer(run):
        repo = match.group("qualified") or match.group("url")
        refs.append((repo, int(match.group("num"))))
    return refs


def _resolve_repo(
    explicit: str | None, sentence_slugs: list[str], prompt_slugs: list[str], cwd_repo: str | None
) -> str | None:
    if explicit:
        return explicit
    if len(sentence_slugs) == 1:
        return sentence_slugs[0]
    if len(prompt_slugs) == 1:
        return prompt_slugs[0]
    return cwd_repo


def repo_from_cwd(cwd: str | None) -> str | None:
    """``owner/name`` of the GitHub ``origin`` remote at ``cwd``, else None."""
    if not cwd:
        return None
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    match = re.search(rf"github\.com[:/](?P<slug>{_SLUG})(?:\.git)?/?$", url, re.I)
    if not match:
        return None
    return match.group("slug").removesuffix(".git")


def _objects_after(
    tail: str, *, glue: re.Pattern[str]
) -> tuple[str | None, list[tuple[str | None, int]]]:
    """(cohort repo, PR refs) named right after a merge verb; both empty when none."""
    cohort = _COHORT_TAIL.match(tail)
    if cohort:
        return cohort.group("repo"), []
    stripped = glue.match(tail)
    rest = tail[stripped.end() :] if stripped else tail
    run = _REF_RUN.match(rest)
    if run:
        return None, _refs_in_run(run.group(0))
    return None, []


def parse_instructions(prompt: str, *, cwd_repo: str | None = None) -> list[dict[str, Any]]:
    """Explicit merge instructions in ``prompt``, authorizations and revocations.

    Each item: ``{"kind": "authorize"|"revoke", "scope": "pr"|"open_cohort",
    "repo": str|None, "pr": int|None, "excerpt": str}``. An authorization is
    returned only for a clause directed at the agent (imperative or first
    person) that is not presented material; a revocation is returned for any
    negative clause that names its pull request or repository — over-applying a
    cancellation fails closed. A PR instruction whose repository cannot be
    resolved is still returned with ``repo: None``; it binds nothing.
    """
    cleaned = sanitize_prompt(prompt)
    if cleaned is None:
        return []
    prompt_slugs = _slug_candidates(cleaned)
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None, int | None]] = set()

    def _add(kind: str, scope: str, repo: str | None, pr: int | None, text: str) -> None:
        key = (kind, scope, repo.casefold() if repo else None, pr)
        if key in seen:
            return
        seen.add(key)
        found.append(
            {
                "kind": kind,
                "scope": scope,
                "repo": repo,
                "pr": pr,
                "excerpt": text.strip()[:EXCERPT_CHARS],
            }
        )

    for sentence in _sentences(cleaned):
        if _is_question(sentence):
            continue
        sentence_slugs = _slug_candidates(sentence)
        for clause, presented in _clauses(sentence):
            if _is_negative(clause):
                for verb in _MERGE_VERB.finditer(clause):
                    tail = clause[verb.end() :]
                    cohort, refs = _objects_after(tail, glue=_REVOKE_GLUE)
                    if cohort is None and not refs:
                        short = _COHORT_REVOKE_SHORT.match(tail)
                        if short and verb.group(0).lower() in {"merges", "merging", "merge"}:
                            cohort = short.group("repo")
                    if cohort:
                        _add(KIND_REVOKE, "open_cohort", cohort, None, clause)
                    for explicit, number in refs:
                        repo = _resolve_repo(explicit, sentence_slugs, prompt_slugs, cwd_repo)
                        _add(KIND_REVOKE, "pr", repo, number, clause)
                continue
            if presented:
                continue
            directed = _DIRECTED.match(clause)
            if not directed:
                continue
            tail = clause[directed.end() :]
            cohort, refs = _objects_after(tail, glue=_GLUE)
            if cohort:
                _add(KIND_AUTHORIZE, "open_cohort", cohort, None, clause)
            for explicit, number in refs:
                repo = _resolve_repo(explicit, sentence_slugs, prompt_slugs, cwd_repo)
                _add(KIND_AUTHORIZE, "pr", repo, number, clause)
    return found


# --- host provenance -----------------------------------------------------------


def host_provenance(host: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """The hook payload's own provenance, or None when the payload is not one.

    Claude Code's ``UserPromptSubmit`` carries ``session_id`` and
    ``transcript_path``; Cursor's ``beforeSubmitPrompt`` carries
    ``conversation_id`` and ``generation_id``. A payload that does not name the
    event, or lacks the session identity, is not a host prompt event.
    """
    if host not in HOSTS or not isinstance(payload, dict):
        return None
    event = str(payload.get("hook_event_name") or "")
    if event != HOST_EVENTS[host]:
        return None
    if host == "claude-code":
        session = payload.get("session_id")
        transcript = payload.get("transcript_path")
        if not isinstance(session, str) or not session.strip():
            return None
        if not isinstance(transcript, str) or not transcript.strip():
            return None
        cwd = payload.get("cwd")
        return {
            "hook_event_name": event,
            "session_id": session.strip(),
            "transcript_path": transcript.strip(),
            "cwd": cwd if isinstance(cwd, str) else None,
        }
    conversation = payload.get("conversation_id")
    if not isinstance(conversation, str) or not conversation.strip():
        return None
    transcript = payload.get("transcript_path")
    roots = payload.get("workspace_roots")
    return {
        "hook_event_name": event,
        "session_id": conversation.strip(),
        "generation_id": payload.get("generation_id")
        if isinstance(payload.get("generation_id"), str)
        else None,
        "transcript_path": transcript if isinstance(transcript, str) and transcript else None,
        "workspace_roots": [r for r in roots if isinstance(r, str)]
        if isinstance(roots, list)
        else None,
    }


def _valid_provenance(host: str, provenance: Any, session_id: str) -> bool:
    if not isinstance(provenance, dict) or host not in HOSTS:
        return False
    if provenance.get("hook_event_name") != HOST_EVENTS[host]:
        return False
    if str(provenance.get("session_id") or "") != session_id or not session_id:
        return False
    if host == "claude-code":
        transcript = provenance.get("transcript_path")
        return isinstance(transcript, str) and bool(transcript.strip())
    return True


# --- receipt store -----------------------------------------------------------


def default_store_path() -> Path:
    """Where the host hooks write: the hook environment's home."""
    return Path.home() / ".l9" / "autonomy" / INSTRUCTION_FILE_NAME


def account_store_path() -> Path:
    """Where readers that an agent may run look: the account's home from the
    password database, not ``$HOME`` and not an environment override."""
    try:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError):
        home = Path.home()
    return home / ".l9" / "autonomy" / INSTRUCTION_FILE_NAME


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()


def _normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def _instruction_id(host: str, session_id: str, digest: str, item: dict[str, Any]) -> str:
    seed = "|".join(
        [
            host,
            session_id,
            digest,
            item["kind"],
            item["scope"],
            str(item.get("repo")),
            str(item.get("pr")),
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def load_instructions(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or default_store_path()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return []
    entries = payload.get("instructions")
    return (
        [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
    )


def _write_store(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"schema": SCHEMA, "instructions": entries}, indent=2) + "\n"
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)


def is_live(entry: dict[str, Any], now: float) -> bool:
    """A well-formed, unexpired receipt carrying the host hook's provenance."""
    expires = entry.get("expires_at")
    recorded = entry.get("recorded_at")
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        return False
    if not isinstance(recorded, (int, float)) or isinstance(recorded, bool):
        return False
    if entry.get("recorder") != RECORDER or entry.get("kind") not in KINDS:
        return False
    host = str(entry.get("host") or "")
    if not _valid_provenance(host, entry.get("provenance"), str(entry.get("session_id") or "")):
        return False
    return recorded <= now < expires


def list_open_pull_requests(repo: str) -> list[int]:
    """Every open pull request number of ``repo`` over REST. Raises RuntimeError."""
    from shutil import which

    if not which("gh"):
        raise RuntimeError("gh not on PATH")
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{repo}/pulls?state=open&per_page=100",
            ],
            capture_output=True,
            text=True,
            timeout=_GH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"gh failed: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or "gh returned non-zero").strip().splitlines()
        raise RuntimeError(detail[-1][:200] if detail else "gh returned non-zero")
    try:
        payload = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh emitted non-JSON: {exc}") from exc
    pages = payload if isinstance(payload, list) else []
    if pages and all(isinstance(page, list) for page in pages):
        records = [item for page in pages for item in page]
    else:
        records = pages
    numbers: list[int] = []
    for item in records:
        if not isinstance(item, dict) or "number" not in item:
            raise RuntimeError("pull request listing was not a list of pull requests")
        numbers.append(int(item["number"]))
    return sorted(numbers)


def record_instructions(
    prompt: str,
    *,
    host: str,
    session_id: str,
    cwd: str | None = None,
    path: Path | None = None,
    now: float | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    cwd_repo: str | None = None,
    provenance: dict[str, Any] | None = None,
    open_pull_requests: Callable[[str], list[int]] | None = None,
) -> list[dict[str, Any]]:
    """Append one receipt per explicit instruction in ``prompt``; return them.

    Called by the host prompt hooks only, with the payload's provenance from
    :func:`host_provenance`; a missing or inconsistent provenance is a
    ``ValueError``, never a receipt. Cohort instructions snapshot the
    repository's open pull requests through ``open_pull_requests`` (GitHub REST
    by default); a snapshot that fails is stored as ``members: None`` and covers
    nothing. Expired receipts are pruned on every write and the store is capped.
    """
    if host not in HOSTS:
        raise ValueError(f"host must be one of {HOSTS}")
    if ttl_seconds <= 0 or ttl_seconds > DEFAULT_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be in 1..{DEFAULT_TTL_SECONDS}")
    if not _valid_provenance(host, provenance, session_id):
        raise ValueError(
            "a receipt needs the host prompt hook's provenance (hook_event_name, session, "
            "transcript); an agent-shaped payload records nothing"
        )
    assert provenance is not None
    stamp = int(now if now is not None else time.time())
    resolved_cwd_repo = cwd_repo if cwd_repo is not None else repo_from_cwd(cwd)
    parsed = parse_instructions(prompt, cwd_repo=resolved_cwd_repo)
    if not parsed:
        return []
    lister = open_pull_requests or list_open_pull_requests
    digest = prompt_digest(prompt)
    target = path or default_store_path()
    kept = [entry for entry in load_instructions(target) if is_live(entry, stamp)]
    written: list[dict[str, Any]] = []
    snapshots: dict[str, tuple[list[int] | None, str | None]] = {}
    for item in parsed:
        entry: dict[str, Any] = {
            "id": _instruction_id(host, session_id, digest, item),
            "schema": SCHEMA,
            "recorder": RECORDER,
            "kind": item["kind"],
            "host": host,
            "session_id": session_id,
            "cwd": str(cwd) if cwd else None,
            "recorded_at": stamp,
            "expires_at": stamp + int(ttl_seconds),
            "scope": item["scope"],
            "repo": item.get("repo"),
            "pr": item.get("pr"),
            "excerpt": item["excerpt"],
            "prompt_sha256": digest,
            "provenance": dict(provenance),
        }
        if item["scope"] == "open_cohort" and item["kind"] == KIND_AUTHORIZE and item.get("repo"):
            repo = str(item["repo"])
            if repo not in snapshots:
                try:
                    snapshots[repo] = (list(lister(repo)), None)
                except Exception as exc:  # noqa: BLE001 - recorded as unavailable, never guessed
                    snapshots[repo] = (None, f"{type(exc).__name__}: {exc}"[:200])
            members, error = snapshots[repo]
            entry["members"] = members
            entry["snapshot_at"] = stamp
            entry["membership"] = "snapshot" if members is not None else "unavailable"
            if error:
                entry["membership_error"] = error
        kept = [k for k in kept if k.get("id") != entry["id"]]
        kept.append(entry)
        written.append(entry)
    _write_store(target, kept[-MAX_RECORDS:])
    return written


def _covers(entry: dict[str, Any], repo: str, pr: int) -> tuple[bool, str]:
    entry_repo = str(entry.get("repo") or "")
    if not entry_repo or entry_repo.casefold() != repo.casefold():
        return False, "other repository"
    scope = entry.get("scope")
    if scope == "pr":
        if entry.get("pr") == pr:
            return True, "explicit instruction names this pull request"
        return False, "other pull request"
    if scope == "open_cohort":
        if entry.get("kind") == KIND_REVOKE:
            return True, "repository-wide cancellation"
        members = entry.get("members")
        if not isinstance(members, list):
            return (
                False,
                "cohort membership could not be snapshotted when the instruction was given",
            )
        if pr in members:
            return True, "pull request was open when the cohort was authorized"
        return False, "pull request was not open when the cohort was authorized"
    return False, "unknown scope"


def _latest(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    return max(enumerate(entries), key=lambda pair: (float(pair[1]["recorded_at"]), pair[0]))[1]


def _covering(
    repo: str, pr: int, *, path: Path | None, now: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    authorizations: list[dict[str, Any]] = []
    revocations: list[dict[str, Any]] = []
    for entry in load_instructions(path):
        if not is_live(entry, now):
            continue
        covered, _ = _covers(entry, repo, pr)
        if not covered:
            continue
        (authorizations if entry.get("kind") == KIND_AUTHORIZE else revocations).append(entry)
    return authorizations, revocations


def find_instruction(
    repo: str,
    pr: str | int,
    *,
    path: Path | None = None,
    now: float | None = None,
) -> dict[str, Any] | None:
    """The live authorizing receipt covering ``repo#pr``, unless revoked since.

    The latest instruction wins: a cancellation recorded at or after the latest
    authorization withdraws it; an authorization recorded after a cancellation
    stands.
    """
    number = str(pr).strip()
    if not repo or not number.isdigit():
        return None
    stamp = time.time() if now is None else now
    authorizations, revocations = _covering(repo, int(number), path=path, now=stamp)
    latest_authorization = _latest(authorizations)
    if latest_authorization is None:
        return None
    latest_revocation = _latest(revocations)
    if latest_revocation is not None and float(latest_revocation["recorded_at"]) >= float(
        latest_authorization["recorded_at"]
    ):
        return None
    return dict(latest_authorization)


def revocation_for(
    repo: str,
    pr: str | int,
    *,
    path: Path | None = None,
    now: float | None = None,
    since: float | None = None,
) -> dict[str, Any] | None:
    """The live cancellation that withdraws authority over ``repo#pr``, else None.

    ``since`` is when the authority being checked was issued (a grant's
    ``issued_at``, a GitHub record's time); a cancellation recorded before it
    was already superseded by that issuance. A cancellation followed by a newer
    authorization is spent.
    """
    number = str(pr).strip()
    if not repo or not number.isdigit():
        return None
    stamp = time.time() if now is None else now
    authorizations, revocations = _covering(repo, int(number), path=path, now=stamp)
    latest_revocation = _latest(revocations)
    if latest_revocation is None:
        return None
    revoked_at = float(latest_revocation["recorded_at"])
    if since is not None and revoked_at < float(since):
        return None
    newer = [a for a in authorizations if float(a["recorded_at"]) > revoked_at]
    if newer:
        return None
    return dict(latest_revocation)


def revocation_reason(entry: dict[str, Any]) -> str:
    when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(entry.get("recorded_at") or 0)))
    return f"revoked by operator instruction {entry.get('id')} at {when} ({entry.get('excerpt')})"


def instruction_verdict(
    repo: str,
    pr: str | int,
    *,
    path: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """``find_instruction`` plus the reason a reader can print."""
    stamp = time.time() if now is None else now
    entry = find_instruction(repo, pr, path=path, now=stamp)
    if entry is not None:
        return {"authorized": True, "instruction": entry, "reason": "live operator instruction"}
    number = str(pr).strip()
    revoked = revocation_for(repo, pr, path=path, now=stamp) if number.isdigit() else None
    if revoked is not None:
        return {"authorized": False, "instruction": None, "reason": revocation_reason(revoked)}
    reasons: list[str] = []
    for entry in load_instructions(path):
        if str(entry.get("repo") or "").casefold() != (repo or "").casefold():
            continue
        if entry.get("kind") == KIND_REVOKE:
            continue
        if not is_live(entry, stamp):
            reasons.append("an instruction for this repository has expired or is malformed")
            continue
        if number.isdigit():
            _, why = _covers(entry, repo, int(number))
            reasons.append(why)
    fallback = "no operator merge instruction recorded for this repository"
    reason = reasons[-1] if reasons else fallback
    return {"authorized": False, "instruction": None, "reason": reason}


# --- host transcript corroboration ------------------------------------------------


def _record_text(record: dict[str, Any]) -> str:
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def _record_is_human_turn(record: dict[str, Any]) -> bool | None:
    """True for a typed prompt, False for a relayed one, None when unmarked."""
    turn = record.get("turnOrigin")
    origin = record.get("origin")
    kind = origin.get("kind") if isinstance(origin, dict) else None
    if turn is None and kind is None:
        return None
    verdicts = [value in HUMAN_TURN_ORIGINS for value in (turn, kind) if value is not None]
    return all(verdicts)


def transcript_corroborates(
    entry: dict[str, Any], *, transcript_path: str | Path | None = None
) -> tuple[bool, str]:
    """Whether a human turn of the receipt's session, in the host-written
    transcript, carries the receipt's prompt (same digest) or its excerpt."""
    provenance = entry.get("provenance") if isinstance(entry.get("provenance"), dict) else {}
    path_text = str(transcript_path or provenance.get("transcript_path") or "").strip()
    if not path_text:
        return False, "receipt names no host transcript"
    path = Path(path_text).expanduser()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return False, f"host transcript unreadable ({exc.__class__.__name__})"
    session = str(entry.get("session_id") or "")
    digest = str(entry.get("prompt_sha256") or "")
    excerpt = _normalized(str(entry.get("excerpt") or ""))
    matched_non_human = False
    unmarked = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("type") != "user":
            continue
        if "toolUseResult" in record or record.get("isMeta") or record.get("isSidechain"):
            continue
        message = record.get("message")
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        if str(record.get("sessionId") or "") != session:
            continue
        text = _record_text(record)
        if not text:
            continue
        hit = (digest and prompt_digest(text) == digest) or (
            bool(excerpt) and excerpt in _normalized(text)
        )
        if not hit:
            continue
        human = _record_is_human_turn(record)
        if human is True:
            return True, f"human turn of session {session} in the host transcript"
        if human is None:
            unmarked = True
        else:
            matched_non_human = True
    if matched_non_human:
        return False, "the transcript carries this text only as a relayed (non-human) turn"
    if unmarked:
        return False, "the transcript carries this text without a host origin marker"
    return False, "no human turn of this session in the host transcript carries this text"


def receipt_verdict(
    entry: dict[str, Any],
    *,
    now: float | None = None,
    session_id: str | None = None,
    transcript_path: str | None = None,
) -> dict[str, Any]:
    """Whether ``entry`` may become authority: live, grantable host, bound to the
    live session and transcript when those are known, and corroborated."""
    stamp = time.time() if now is None else now
    if not is_live(entry, stamp):
        return {"ok": False, "reason": "receipt is expired, malformed, or lacks hook provenance"}
    host = str(entry.get("host") or "")
    if host not in GRANTABLE_HOSTS:
        return {
            "ok": False,
            "reason": (
                f"{BLOCKED_HOST_ORIGIN}: host {host!r} exposes no gate-side session binding or "
                "readable host transcript, so a receipt from it cannot be verified; the GitHub "
                "record remains the authorization channel there"
            ),
        }
    provenance = entry.get("provenance") or {}
    if session_id is not None and str(entry.get("session_id")) != str(session_id):
        return {
            "ok": False,
            "reason": (
                f"receipt belongs to session {entry.get('session_id')}, the live session is "
                f"{session_id}"
            ),
        }
    if transcript_path is not None and str(provenance.get("transcript_path")) != str(
        transcript_path
    ):
        return {"ok": False, "reason": "receipt names a different transcript than the live session"}
    ok, reason = transcript_corroborates(entry)
    if not ok:
        return {"ok": False, "reason": f"not corroborated by the host transcript: {reason}"}
    return {"ok": True, "reason": reason}


# --- hook entrypoint -----------------------------------------------------------


def _payload_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_message", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _describe(entry: dict[str, Any]) -> str:
    target = f"{entry.get('repo') or '<repository unresolved>'}"
    if entry.get("scope") == "pr":
        target += f"#{entry.get('pr')}"
    elif entry.get("kind") == KIND_REVOKE:
        target += " (every pull request)"
    else:
        members = entry.get("members")
        shown = ", ".join(f"#{n}" for n in members) if isinstance(members, list) else "unavailable"
        target += f" (open pull requests at the time: {shown})"
    return f"{entry.get('kind')} {target} [id {entry['id']}]"


def record_from_payload(payload: dict[str, Any], host: str) -> list[dict[str, Any]]:
    provenance = host_provenance(host, payload)
    if provenance is None:
        return []
    prompt = _payload_prompt(payload)
    if not prompt:
        return []
    cwd = provenance.get("cwd")
    if cwd is None:
        roots = provenance.get("workspace_roots")
        cwd = roots[0] if isinstance(roots, list) and roots else None
    return record_instructions(
        prompt,
        host=host,
        session_id=str(provenance["session_id"]),
        cwd=cwd,
        provenance=provenance,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record", help="host prompt hook: read the hook payload on stdin")
    record.add_argument("--host", choices=HOSTS, required=True)
    show = sub.add_parser("show", help="print the live receipts (read-only)")
    show.add_argument("--repo", default="")
    show.add_argument("--pr", default="")
    args = parser.parse_args(argv)

    if args.command == "show":
        now = time.time()
        entries = [e for e in load_instructions() if is_live(e, now)]
        if args.repo and args.pr:
            verdict = instruction_verdict(args.repo, args.pr)
            print(json.dumps(verdict, indent=2, sort_keys=True))
            return 0 if verdict["authorized"] else 3
        print(json.dumps({"schema": SCHEMA, "instructions": entries}, indent=2, sort_keys=True))
        return 0

    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    recorded: list[dict[str, Any]] = []
    try:
        recorded = record_from_payload(payload, args.host)
    except Exception as exc:  # noqa: BLE001 - observer: never block a prompt
        print(f"WARN: operator merge instruction recorder degraded: {exc}", file=sys.stderr)
    if args.host == "cursor":
        print(json.dumps({"continue": True}))
        return 0
    if recorded:
        listed = "; ".join(_describe(entry) for entry in recorded)
        unresolved = [e for e in recorded if not e.get("repo")]
        note = (
            " An instruction without a resolvable repository binds nothing; name the "
            "repository as owner/name."
            if unresolved
            else ""
        )
        context = (
            f"L9 operator merge instruction recorded: {listed}. Once the pull request is green, "
            "mergeable and thread-clean, the agent may transcribe an authorization with "
            '"$HOME/.cursor-governance/.venv/bin/python" '
            '"$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" --operator-instruction '
            "--repo <owner/name> --pr <n> --head-sha <live 40-hex> and then merge with "
            "stack_safe_merge.py --run (CANONICAL_LAW §6.2.13). A cancellation withdraws "
            "earlier authority for that pull request. L9-ORG-007 protected changes still need "
            "an independent human GitHub authorization." + note
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": context,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
