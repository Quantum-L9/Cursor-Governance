#!/usr/bin/env python3
"""Operator merge instructions, recorded by the host's prompt-submission hook.

CANONICAL_LAW §6.2.13 (operator-prompt channel). The human who types a prompt is
the authorizer of the merges that prompt explicitly orders; the agent records
and executes that authority. This module is the recorder and the reader:

* ``record`` runs **only** inside a host prompt hook — Claude Code
  ``UserPromptSubmit`` or Cursor ``beforeSubmitPrompt`` — on the prompt the host
  delivered. It parses explicit merge instructions and appends one receipt per
  instruction to ``~/.l9/autonomy/operator-merge-instructions.json``. An agent
  tool call that writes that file is denied by ``merge_gate.py`` exactly like a
  write of ``merge-authorization.json``.
* ``find_instruction`` answers whether a live receipt covers one repository and
  one pull request. ``authorize_merge.py --operator-instruction`` turns that into
  a head-bound grant after rechecking the live pull request;
  ``merge_gate.py`` consults the same receipt before letting that run proceed.

What is recognised (imperative, not interrogative, not negated):

    merge PR #735 after the checks pass
    fix and merge Quantum-L9/Cursor-Governance#735
    the eventual merge of PR #735
    remediate and merge all currently open PRs in Quantum-L9/Cursor-Governance

What is not: a question ("should we merge #735?"), a negation ("do not merge
#735"), a merge verb with no pull-request object ("merge main into the
branch"), text inside fenced code, block quotes or ``<pasted_content>``, and any
prompt carrying a host relay marker (a scheduled task firing, a subagent
reporting back, a cross-session message, a webhook payload). The last rule
exists because Claude Code fires ``UserPromptSubmit`` for those turns too.

A cohort instruction ("all currently open PRs in <owner/name>") must name the
repository. It is resolved into individual grants later, and only for pull
requests that already existed when the instruction was recorded: it is a
snapshot, never standing repository-wide authority.

Assurance, stated plainly: a receipt proves that the host delivered this text
as a user turn of this session and that no agent tool call wrote it. It is not
cryptographic proof of who typed it, and it does not establish a GitHub
identity, which is why L9-ORG-007 protected changes still require the GitHub
record (``authorize_merge.py`` refuses an operator-prompt grant for them).

Metadata:
  layer: ops
  role: merge_authorization
  version: 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA = "l9.operator-merge-instruction.v1"
INSTRUCTION_FILE_NAME = "operator-merge-instructions.json"
#: An instruction outlives the grants it backs (grants expire within four
#: hours) so authorized remediation can re-issue a head-specific grant without
#: a repeated approval. After this the operator must say it again.
DEFAULT_TTL_SECONDS = 8 * 60 * 60
MAX_RECORDS = 64
EXCERPT_CHARS = 300
HOSTS = ("claude-code", "cursor")
RECORDER = "host_prompt_hook"

#: ``owner/name``; neither part may start or end with a dot, so a sentence's
#: trailing period is never read as part of the repository name.
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
#: The same reference without group names, so a run of them can repeat.
_PR_REF_ANON = re.sub(r"\(\?P<\w+>", "(?:", _PR_REF.pattern)
_REF_RUN = re.compile(
    rf"(?:{_PR_REF_ANON})(?:{_REF_SEPARATOR}(?:{_PR_REF_ANON}))*",
    re.I,
)
_MERGE_VERB = re.compile(r"\bmerg(?:e|es|ing)\b", re.I)
#: Words that may sit between the verb and its object: "merge of PR #1",
#: "merge the PRs #1 and #2", "merge and close PR #3" is deliberately NOT glue.
_GLUE = re.compile(
    r"^(?:\s*(?:of|the|both|all|these|those|them\s*:|then|also|now|please|,|&|and\s+(?:then|also)))*\s*",
    re.I,
)
_COHORT = re.compile(
    r"\bmerg(?:e|es|ing)\b"
    r"(?:\s*(?:of|the|then|also|now|please|,|and\s+(?:then|also)))*"
    r"\s+(?:all\s+)?(?:of\s+)?(?:the\s+)?(?:currently\s+|now\s+|still\s+)?open\s+"
    r"(?:pull[\s-]*requests|prs?)\s+(?:in|of|on|for|from|under|across)\s+"
    rf"(?:the\s+)?(?:repo(?:sitory)?\s+)?(?P<repo>{_SLUG})",
    re.I,
)
_NEGATION = re.compile(
    r"\b(?:don'?t|do\s+not|never|not|without|no|instead\s+of|rather\s+than|stop|"
    r"avoid|refrain\s+from|cannot|can'?t|won'?t|will\s+not|must\s+not|should\s+not|"
    r"shouldn'?t|forbid(?:den)?|prohibit(?:ed)?)\b(?:\s+\S+){0,2}\s+merg",
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
_BLOCKQUOTE = re.compile(r"^[ \t]*>.*$", re.M)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


# --- prompt parsing ----------------------------------------------------------


def sanitize_prompt(text: str) -> str | None:
    """Prompt text that may carry an operator instruction, or None when relayed.

    Pasted blocks, system reminders, fenced code and block quotes are removed:
    text copied from a repository file, a PR comment or a tool result is not an
    instruction even when the operator pasted it.
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


def _is_question(sentence: str) -> bool:
    stripped = sentence.strip()
    return stripped.endswith("?") or bool(_QUESTION_LEAD.match(stripped))


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


def parse_instructions(prompt: str, *, cwd_repo: str | None = None) -> list[dict[str, Any]]:
    """Explicit merge instructions in ``prompt``.

    Each item: ``{"scope": "pr", "repo": str|None, "pr": int, "excerpt": str}``
    or ``{"scope": "open_cohort", "repo": str, "pr": None, "excerpt": str}``.
    A PR instruction whose repository cannot be resolved is still returned
    with ``repo: None``; it can never bind a grant, and the reader says so.
    """
    cleaned = sanitize_prompt(prompt)
    if cleaned is None:
        return []
    prompt_slugs = _slug_candidates(cleaned)
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, int | None]] = set()

    def _add(scope: str, repo: str | None, pr: int | None, sentence: str) -> None:
        key = (scope, repo.casefold() if repo else None, pr)
        if key in seen:
            return
        seen.add(key)
        found.append(
            {"scope": scope, "repo": repo, "pr": pr, "excerpt": sentence.strip()[:EXCERPT_CHARS]}
        )

    for sentence in _sentences(cleaned):
        if _is_question(sentence) or _NEGATION.search(sentence):
            continue
        sentence_slugs = _slug_candidates(sentence)
        for cohort in _COHORT.finditer(sentence):
            _add("open_cohort", cohort.group("repo"), None, sentence)
        for verb in _MERGE_VERB.finditer(sentence):
            tail = sentence[verb.end() :]
            glue = _GLUE.match(tail)
            tail = tail[glue.end() :] if glue else tail
            run = _REF_RUN.match(tail)
            if not run:
                continue
            for explicit, number in _refs_in_run(run.group(0)):
                repo = _resolve_repo(explicit, sentence_slugs, prompt_slugs, cwd_repo)
                _add("pr", repo, number, sentence)
    return found


# --- receipt store -----------------------------------------------------------


def default_store_path() -> Path:
    return Path.home() / ".l9" / "autonomy" / INSTRUCTION_FILE_NAME


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()


def _instruction_id(host: str, session_id: str, digest: str, item: dict[str, Any]) -> str:
    seed = "|".join(
        [host, session_id, digest, item["scope"], str(item.get("repo")), str(item.get("pr"))]
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
    expires = entry.get("expires_at")
    recorded = entry.get("recorded_at")
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        return False
    if not isinstance(recorded, (int, float)) or isinstance(recorded, bool):
        return False
    if entry.get("recorder") != RECORDER or entry.get("host") not in HOSTS:
        return False
    return recorded <= now < expires


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
) -> list[dict[str, Any]]:
    """Append one receipt per explicit instruction in ``prompt``; return them.

    Called by the host prompt hooks only. Expired receipts are pruned on every
    write and the store is capped so a long-lived machine never accumulates
    stale authority.
    """
    if host not in HOSTS:
        raise ValueError(f"host must be one of {HOSTS}")
    if ttl_seconds <= 0 or ttl_seconds > DEFAULT_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be in 1..{DEFAULT_TTL_SECONDS}")
    stamp = int(now if now is not None else time.time())
    resolved_cwd_repo = cwd_repo if cwd_repo is not None else repo_from_cwd(cwd)
    parsed = parse_instructions(prompt, cwd_repo=resolved_cwd_repo)
    if not parsed:
        return []
    digest = prompt_digest(prompt)
    target = path or default_store_path()
    kept = [entry for entry in load_instructions(target) if is_live(entry, stamp)]
    written: list[dict[str, Any]] = []
    for item in parsed:
        entry = {
            "id": _instruction_id(host, session_id, digest, item),
            "schema": SCHEMA,
            "recorder": RECORDER,
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
        }
        kept = [k for k in kept if k.get("id") != entry["id"]]
        kept.append(entry)
        written.append(entry)
    _write_store(target, kept[-MAX_RECORDS:])
    return written


def _covers(
    entry: dict[str, Any], repo: str, pr: int, pr_created_at: float | None
) -> tuple[bool, str]:
    entry_repo = str(entry.get("repo") or "")
    if not entry_repo or entry_repo.casefold() != repo.casefold():
        return False, "other repository"
    scope = entry.get("scope")
    if scope == "pr":
        if entry.get("pr") == pr:
            return True, "explicit instruction names this pull request"
        return False, "other pull request"
    if scope == "open_cohort":
        if pr_created_at is None:
            return (
                False,
                "cohort instruction needs the pull request's creation time to prove membership",
            )
        if pr_created_at <= float(entry.get("recorded_at") or 0):
            return True, "pull request was open when the cohort was authorized"
        return False, "pull request was opened after the cohort instruction"
    return False, "unknown scope"


def find_instruction(
    repo: str,
    pr: str | int,
    *,
    path: Path | None = None,
    now: float | None = None,
    pr_created_at: float | None = None,
    allow_cohort_without_membership: bool = False,
) -> dict[str, Any] | None:
    """The live receipt covering ``repo#pr``, else None.

    ``allow_cohort_without_membership`` lets a hook that has no network accept a
    cohort instruction for the repository; the grant writer, which does have
    the pull request's creation time, must not pass it.
    """
    number = str(pr).strip()
    if not repo or not number.isdigit():
        return None
    stamp = time.time() if now is None else now
    for entry in reversed(load_instructions(path)):
        if not is_live(entry, stamp):
            continue
        covered, _ = _covers(entry, repo, int(number), pr_created_at)
        if covered:
            return dict(entry)
        if (
            allow_cohort_without_membership
            and entry.get("scope") == "open_cohort"
            and str(entry.get("repo") or "").casefold() == repo.casefold()
        ):
            return dict(entry)
    return None


def instruction_verdict(
    repo: str,
    pr: str | int,
    *,
    path: Path | None = None,
    now: float | None = None,
    pr_created_at: float | None = None,
) -> dict[str, Any]:
    """``find_instruction`` plus the reason a reader can print."""
    entry = find_instruction(repo, pr, path=path, now=now, pr_created_at=pr_created_at)
    if entry is not None:
        return {"authorized": True, "instruction": entry, "reason": "live operator instruction"}
    stamp = time.time() if now is None else now
    number = str(pr).strip()
    reasons: list[str] = []
    for entry in load_instructions(path):
        if str(entry.get("repo") or "").casefold() != (repo or "").casefold():
            continue
        if not is_live(entry, stamp):
            reasons.append("an instruction for this repository has expired")
            continue
        if number.isdigit():
            _, why = _covers(entry, repo, int(number), pr_created_at)
            reasons.append(why)
    fallback = "no operator merge instruction recorded for this repository"
    reason = reasons[-1] if reasons else fallback
    return {"authorized": False, "instruction": None, "reason": reason}


# --- hook entrypoint -----------------------------------------------------------


def _payload_fields(payload: dict[str, Any], host: str) -> tuple[str, str, str | None]:
    prompt = ""
    for key in ("prompt", "user_message", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            prompt = value
            break
    if host == "cursor":
        session = str(payload.get("conversation_id") or "")
        roots = payload.get("workspace_roots")
        cwd = None
        if isinstance(roots, list) and roots and isinstance(roots[0], str):
            cwd = roots[0]
        elif isinstance(roots, str):
            cwd = roots
    else:
        session = str(payload.get("session_id") or "")
        cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    return prompt, session, cwd


def _describe(entry: dict[str, Any]) -> str:
    target = f"{entry.get('repo') or '<repository unresolved>'}"
    if entry.get("scope") == "pr":
        target += f"#{entry.get('pr')}"
    else:
        target += " (open pull requests at the time of the instruction)"
    return f"{target} [id {entry['id']}]"


def record_from_payload(payload: dict[str, Any], host: str) -> list[dict[str, Any]]:
    prompt, session, cwd = _payload_fields(payload, host)
    if not prompt or not session:
        return []
    return record_instructions(prompt, host=host, session_id=session, cwd=cwd)


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
            "mergeable and thread-clean, the agent may transcribe it with "
            '"$HOME/.cursor-governance/.venv/bin/python" '
            '"$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" --operator-instruction '
            "--repo <owner/name> --pr <n> --head-sha <live 40-hex> and then merge with "
            "stack_safe_merge.py --run (CANONICAL_LAW §6.2.13). L9-ORG-007 protected changes "
            "still need an independent human GitHub authorization." + note
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
