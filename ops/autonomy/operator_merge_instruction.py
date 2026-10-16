#!/usr/bin/env python3
"""Operator merge instructions, recorded by the host's prompt-submission hook.

CANONICAL_LAW §6.2.13, §6.2.14 (operator-prompt channel). The human who types a prompt is
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

What is recognised (§6.2.14): an **affirmative merge instruction directed at
the agent**, in the imperative or first person, in ordinary language. Its
objects may be named or established by the conversation:

    merge PR #735 after the checks pass
    fix and merge #96 through #99 when green
    I need you to merge all open PR’s in https://github.com/Quantum-L9/l9-graphiti-memory
    merge these PRs                          (the PRs the agent just reported)
    go ahead and merge everything we just fixed

and an **explicit cancellation**, which revokes the authority above:

    do not merge PR #735 after all
    don’t merge them
    stop — do not merge anything

Typographic apostrophes and quotes are folded before parsing, a repository may
be written as ``owner/name`` or as a github.com URL, and ranges ("#96 through
#99") expand to each pull request. A pull request named without its repository
resolves from the sentence, the prompt, the conversation (a qualified reference
to that number, or the one repository it discusses), then the workspace
remote. A contextual object ("these PRs", "them", "everything we just fixed")
resolves, at recording time, to the pull requests named in the agent's latest
reply in the host transcript (else in the last few exchanges); the receipt
stores each resolved pull request, so the authority is frozen when spoken.

What is not an instruction: a question, a verb with no pull-request object,
text inside quotation marks, code fences, block quotes or ``<pasted_content>``,
material introduced by a colon ("the report says: …"), a third-person report
("the reviewer recommends that we merge …"), and any prompt carrying a host
relay marker (a scheduled task firing, a subagent reporting back, a
cross-session message, a webhook payload). Clauses are read independently, so
"don't merge #735, but merge #736" revokes one and authorizes the other. A
cancellation with no resolvable object ("stop, don't merge yet") revokes every
operator authority recorded before it; a cancellation never expires on its
own, so its lapse can never revive an older authorization. A merge of a branch
("don't merge main into it") is not a cancellation of a pull request.

A cohort instruction ("all open PRs in <owner/name>") snapshots the
repository's open pull requests through the GitHub REST path at recording time;
a pull request not in the snapshot — opened later, or closed at the time and
reopened since — is outside the cohort, and a snapshot that could not be taken
covers nothing. It is never standing repository-wide authority.

Capture is observable. Whenever a prompt carries merge intent the hook tells
the agent, in ``additionalContext``, exactly what was recorded or exactly why
nothing was, and a recorder failure is reported as a failure — never as a
capture.

Assurance, stated plainly. A receipt proves two things the agent cannot
produce through a gated tool call: the host prompt hook wrote it with the
hook's own provenance, and a human turn of the same session in the host-written
transcript carries the same text (Claude Code records ``turnOrigin: "human"``
on a typed prompt and ``task_notification`` on a relayed one; observed on
2026-10-15 and again on 2026-10-16 on a ``remote_mobile`` session, not a
documented contract, and its absence fails closed). It is not cryptographic
proof of who typed it; ``authorize_merge.py`` binds it to the session's
authenticated GitHub principal and that principal's repository permission. A
worker that runs arbitrary code as the same OS account could forge the store
and the transcript alike — the §6.2.12 item 7 gap. Cursor exposes no PreToolUse
merge gate and no transcript this module can read, so a Cursor receipt is
recorded for audit but never becomes a grant: BLOCKED_HOST_ORIGIN.

Metadata:
  layer: ops
  role: merge_authorization
  version: 3.0.0
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

#: Scopes. ``all`` is a cancellation only: it covers every repository and PR.
SCOPE_PR = "pr"
SCOPE_COHORT = "open_cohort"
SCOPE_ALL = "all"
#: A range ("#96 through #99") expands to at most this many pull requests.
MAX_RANGE = 50
#: Pull requests a contextual object ("these PRs") may resolve to.
MAX_CONTEXT_MEMBERS = 25
#: Exchanges (a human turn and the agent's replies) read for conversation context.
CONTEXT_EXCHANGES = 3
#: Only the tail of a long host transcript is read for context.
TRANSCRIPT_TAIL_BYTES = 8 * 1024 * 1024
#: Cancellations kept in the store. A cancellation a later authorization has
#: superseded is dropped first; one still in force is dropped only past this cap.
MAX_REVOCATIONS = 1024
#: Agent reply text read per turn for conversation context.
MAX_AGENT_TURN_CHARS = 16 * 1024
#: Clause text the directed-instruction patterns examine.
MAX_CLAUSE_CHARS = 400

_SLUG = r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*/\.?[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"
_SLUG_RE = re.compile(rf"(?<![\w/.@-])(?P<slug>{_SLUG})(?![\w/-])")
_GITHUB_URL_RE = re.compile(rf"https?://(?:www\.)?github\.com/(?P<slug>{_SLUG})(?:/|\b)", re.I)
_GITHUB_REPO_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+)",
    re.I,
)
#: Typographic apostrophes and spaces a phone keyboard produces. Folded before
#: parsing (after quoted spans are stripped), so "PR’s" and "don’t" read as
#: "PR's" and "don't".
_FOLD = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "ʼ": "'",
        "′": "'",
        "＇": "'",
        " ": " ",
        " ": " ",
        " ": " ",
    }
)
#: "PR", "PRs", "PR's", "pull requests".
_PR_NOUN = r"(?:pull[\s-]*requests?|prs?)(?:'s|s')?"
#: One pull-request reference: ``owner/name#12``, ``#12``, ``PR 12``,
#: ``pull request #12`` or a github.com pull URL.
_PR_REF = re.compile(
    rf"(?:(?<![\w.@/-])(?P<qualified>{_SLUG})#"
    rf"|https?://(?:www\.)?github\.com/(?P<url>{_SLUG})/pulls?/"
    rf"|\b{_PR_NOUN}(?:\s*#)?\s*"
    r"|#)"
    r"(?P<num>[1-9]\d*)\b",
    re.I,
)
#: "#96 through #99", "#96-#99", "96–99", "PRs 96 to 99". A spaced hyphen
#: counts only before another "#" ("#5 - 10 minutes" is not a range).
_RANGE_TAIL = (
    r"(?:\s+(?:through|thru|to)\s+|\s*\.\.\s*|[-–—]|\s+[-–—]\s+(?=#))"
    r"(?:#|(?:prs?|pull[\s-]*requests?)\s*#?)?"
    r"(?P<end>[1-9]\d*)\b"
)
_PR_REF_RANGE = re.compile(rf"{_PR_REF.pattern}(?:{_RANGE_TAIL})?", re.I)
_REF_SEPARATOR = r"(?:\s*,\s*(?:and\s+)?|\s+(?:and/or|and|&|then|plus)\s+)"
#: Bare numbers continuing a run that opened with a plural PR noun ("PRs 96, 97").
_BARE_CONTINUATION = re.compile(rf"(?:{_REF_SEPARATOR}#?([1-9]\d*)\b)+", re.I)
_BARE_NUMBER = re.compile(r"([1-9]\d*)\b")
_PLURAL_PR_LEAD = re.compile(r"^\s*(?:pull[\s-]*requests|prs)\b", re.I)
_PR_REF_ANON = re.sub(r"\(\?P<\w+>", "(?:", _PR_REF_RANGE.pattern)
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
    r"(?:please|now|then|also|next|finally|just|kindly|and|&|ok|okay|yes|sure|"
    r"lgtm|approved|looks\s+good(?:\s+to\s+me)?|sounds\s+good|great|perfect|thanks|"
    r"thank\s+you|cool|alright|nice|ship\s+it|"
    r"let'?s|let\s+us|go\s+ahead\s+and|"
    r"(?:can|could|would|will)\s+you(?:\s+please)?|"
    r"you\s+(?:may|can|should|must|are\s+(?:authori[sz]ed|cleared|free)\s+to)|"
    r"i\s+(?:want|need|would\s+like)\s+you\s+to|i'?d\s+like\s+you\s+to)"
)
#: First-person authorization; only these may introduce the noun form
#: ("I authorize the merge of #96").
_AUTHORIZING = (
    r"(?:i\s+(?:authori[sz]e|approve|am\s+authori[sz]ing)(?:\s+you)?(?:\s+to)?|"
    r"(?:authori[sz]ation|approval|go-ahead)\s+(?:granted|given)\s*:?)"
)
_VERB_WORD = r"\b[a-z][a-z-]*\b"
_VERB_CHAIN = (
    rf"(?:{_VERB_WORD}(?:(?:\s*,\s*|\s+(?:and|then|&)\s+){_VERB_WORD})*"
    r"\s*,?\s+(?:and|then|&)\s+)"
)
_MERGE_ADJ = r"(?:(?:eventual|final|actual|subsequent|full|clean|safe)\s+|(?:squash|rebase)[\s-]+)"
#: The imperative verb is "merge"; "merging #96 broke the build" and "the merge
#: of #96 failed" are reports, not orders.
_DIRECTED = re.compile(
    rf"^\s*(?:{_LEAD_IN}\s*[,!:]?\s+)*(?:"
    rf"{_AUTHORIZING}\s+(?:(?:the|a|an)\s+)?{_MERGE_ADJ}?merg(?:e|es|ing)"
    rf"|(?:{_VERB_CHAIN})?{_MERGE_ADJ}?merge"
    r")\b",
    re.I,
)
#: "Fix the CI on #96 and merge it": an imperative clause, coordinated into the
#: merge. Accepted only when it does not open with a subject ("the reviewer
#: … and merge") and carries no reporting verb ("they asked to fix and merge").
_LOOSE_DIRECTED = re.compile(
    rf"^\s*(?:{_LEAD_IN}\s*[,!:]?\s+)*(?P<pre>(?:\S+\s+){{0,12}}?)(?:and|then|&)\s+"
    rf"(?:then\s+)?(?:just\s+|please\s+)?{_MERGE_ADJ}?merge\b",
    re.I,
)
_SUBJECT_START = re.compile(
    r"^\s*(?:the|a|an|i|they|he|she|we|you|someone|somebody|everyone|nobody|reviewers?|"
    r"it|this|that|these|those|there|here|our|their|his|her|its|my|your|copilot|codex|"
    r"bots?|ci|who|which|to|in\s+order|if|when|once|before|after|unless|how|why|whether)\b",
    re.I,
)
#: A leading condition before an imperative: "Once CI is green, merge #96".
_CONDITION_LEAD = re.compile(
    r"^\s*(?:once|when|whenever|after|if|as\s+soon\s+as|provided(?:\s+that)?)\b"
    r"[^,;:?]{1,100},\s*",
    re.I,
)
_REPORTING = re.compile(
    r"\b(?:said|says|say|asked|asks|recommend(?:s|ed)?|suggest(?:s|ed)?|wants?|wanted|"
    r"wrote|writes|comment(?:s|ed)|request(?:s|ed)|propos(?:es|ed)|claim(?:s|ed)?|"
    r"thinks?|thought|would|could|might|whether|if)\b|[?\"]",
    re.I,
)
#: "Ship it: merge #96" — a colon after an interjection does not present material.
_INTERJECTION = re.compile(
    r"^\s*(?:ship\s+it|go|ok|okay|lgtm|approved|yes|sure|decision|instruction|final\s+answer)\s*$",
    re.I,
)
#: "Can you merge #96?" is a request; "can you merge #96 or should we wait?" and
#: "could you check whether #96 should merge?" are questions.
_POLITE_REQUEST = re.compile(
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:go\s+ahead\s+and\s+)?"
    r"(?:\w+\s+(?:and|then)\s+)?merge\b",
    re.I,
)
_QUESTION_WORDS = re.compile(r"\b(?:or|whether|if|should|shall)\b", re.I)
#: "Can you please not merge #96?" / "Could you hold off on merging it?" is a
#: cancellation phrased politely, never a question to skip: a dropped
#: cancellation would leave the earlier authority standing.
_POLITE_CANCEL = re.compile(
    r"^\s*(?:please\s+)?(?:can|could|would|will)\s+you\s+(?:please\s+)?"
    r"(?:not|stop|hold(?:\s+off)?|avoid|refrain|cancel|pause|freeze)\b",
    re.I,
)
#: A deictic object followed by these merges something else into something:
#: "merge them into a single file", "merge it with the helper".
_DEICTIC_OTHER_TARGET = re.compile(
    r"^\s*(?:into|onto|inside|with|together|in\s+(?!order\b)|and\s+(?!then\b))", re.I
)
#: What may follow a bare "these" / "them" / "it" / "both" / "all" when it means
#: pull requests: the end, punctuation, a relative clause, an adverb.
_DEICTIC_CONTINUATION = re.compile(
    rf"^\s*(?:$|[.!?,;:)\]—–-]|{_PR_NOUN}\b|(?:we|you|i|that|which|now|please|too|then|when|"
    r"once|after|if|as|all|both|safely|bottom-?up|first|today|asap|for\s+me|in\s+order|but|so|"
    r"ok|thanks|one\s+by\s+one|in\s+sequence|oldest|again|also|already|just|right|"
    r"whenever|provided|immediately|together\s+now)\b)",
    re.I,
)
#: "all open PRs in <repo>", "every open pull request", "all PRs in <repo>",
#: "all open PR's in https://github.com/<owner>/<name>". The repository is
#: optional; without one the cohort resolves its repository like a bare "#12".
_COHORT_TAIL = re.compile(
    r"^(?:\s*(?:of|the|then|also|now|please|,|and\s+(?:then|also)))*\s*"
    r"(?:(?:all|any|every|each)\s+(?:of\s+)?(?:the\s+)?(?:currently\s+|now\s+|still\s+|remaining\s+)?"
    r"(?P<open1>open\s+)?"
    r"|(?:the\s+)?(?:currently\s+|now\s+|still\s+|remaining\s+)?(?P<open2>open)\s+)"
    rf"{_PR_NOUN}(?![\w#])"
    r"(?:\s+(?:that\s+are\s+)?(?P<open3>open))?"
    r"(?:\s+(?:in|of|on|for|from|under|across|at)\s+(?:the\s+)?(?:repo(?:sitory)?\s+)?"
    r"(?P<repo>[^\s,;]+)(?:\s+(?P<repo_word>repo(?:sitory)?)\b)?)?",
    re.I,
)
#: "cancel all merges in owner/name" — a repository-wide cancellation.
_COHORT_REVOKE_SHORT = re.compile(
    r"^\s*(?:in|for|on|across|of)\s+(?:the\s+)?(?:repo(?:sitory)?\s+)?(?P<repo>[^\s,;]+)",
    re.I,
)
#: An object the conversation established: "these PRs", "them", "it",
#: "everything we just fixed", "all of the green ones".
_DEICTIC = re.compile(
    r"^(?:\s*(?:of|then|also|now|please|,|&|and\s+(?:then|also))\b)*\s*"
    r"(?:(?:all|both|each|every\s+one)\s+(?:of\s+)?)?"
    r"(?:"
    r"(?P<single>it|this\s+one|that\s+one|(?:the|this|that)\s+(?:one|pr|pull[\s-]*request))"
    r"|them|these|those|everything|all|both|the\s+rest|the\s+lot"
    rf"|(?:the|these|those|our|my|your|their|all)\s+(?:[a-z0-9'-]+\s+){{0,3}}?"
    rf"(?:{_PR_NOUN}|ones|changes|fixes|branches|stack|train)"
    r")(?![\w#])",
    re.I,
)
#: A merge verb whose remaining clause names nothing else: "don't merge yet",
#: "no merge.", "without merging". "don't merge main into it" is not bare: it
#: merges a branch, so it cancels no pull request.
_BARE_TAIL = re.compile(
    r"^\s*(?:(?:it|them|this|that|these|those|anything|everything|any|yet|now|today|anymore|"
    r"again|automatically|ever|until|before|after|without|unless|while|once|when|please|"
    r"either|so\s+far|at\s+all|for\s+now|just\s+yet|after\s+all|any\s+more)\b|[.!?,;)\]]|$)",
    re.I,
)
_EVERYTHING = re.compile(
    r"\b(?:anything|everything|any\s+(?:more\s+)?(?:of\s+)?(?:them|prs?|pull[\s-]*requests?)|"
    r"all\s+(?:of\s+)?(?:them|merges))\b",
    re.I,
)
#: "don't merge anything else" limits scope; it cancels nothing.
_SCOPE_LIMIT = re.compile(r"\b(?:else|other|others|besides)\b", re.I)
#: "don't merge until CI is green" is a condition on the merge, not a cancellation.
_CONDITIONAL = re.compile(r"\b(?:until|till|before|unless)\b", re.I)
#: Tail words that make an unresolved directed merge worth reporting.
_PR_ISH = re.compile(
    rf"(?:\b(?:{_PR_NOUN}|them|these|those|it|everything|all|open|ones)\b|#\d|github\.com/)",
    re.I,
)
#: A negation that governs the merge verb: only auxiliaries and adverbs may
#: sit between ("don't ever merge", "do not yet merge"). "Don't forget to
#: merge", "no problem, merge" and "not a regular merge" are not cancellations.
_NEGATION = re.compile(
    r"\b(?:don'?t|do\s+not|never|not|without|no|instead\s+of|rather\s+than|"
    r"avoid|refrain\s+from|cannot|can'?t|won'?t|will\s+not|must\s+not|should\s+not|"
    r"shouldn'?t|no\s+longer)"
    r"(?:\s+(?:yet|ever|actually|just|really|please|you|we|i|anyone|it|be|to|even|"
    r"automatically|go\s+ahead\s+and)){0,2}"
    r"\s+(?:(?:squash|rebase)[\s-]+)?merg",
    re.I,
)
#: A cancelling verb whose object is the merge ("cancel the merge of #96",
#: "stop merging"), not a coordinated other object ("cancel the CI run and merge").
_REVOKE_VERB = re.compile(
    r"\b(?:cancel|revoke|withdraw|rescind|retract|abort|halt|stop|hold(?:\s+off)?(?:\s+on)?|"
    r"pause|freeze|suspend|undo|call\s+off)"
    r"(?:\s+(?:the|my|your|our|this|that|these|those|any|all|every|pending|planned|"
    r"scheduled|earlier|previous|auto)){0,2}\s+merg",
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
    re.compile(r"‘[^’\n]*’(?!\w)"),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"(?:^|(?<=[\s:(\[,]))'[^'\n]*'(?=$|[\s.,;:!?)\]])", re.M),
)
_BLOCKQUOTE = re.compile(r"^[ \t]*>.*$", re.M)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
#: Clause boundaries inside a sentence. A colon marks presented material: what
#: follows "the report says:" is quoted, whatever its mood.
_CLAUSE_SPLIT = re.compile(
    r"\s*;\s*|:\s+|,?\s+(?:but|however|whereas|while|instead|although|except|yet)\s+"
    r"|,\s+(?=(?:do\s+not|don'?t|never)\b)"
    r"|,\s+(?=(?:(?:please|then|just|instead|now)\s+)?merge\b)"
    r"|\s+[—–]\s+|\s+--\s+",
    re.I,
)
#: Agent-text sentences whose references are not put forward as ready: a
#: negation, a red or draft state, an unrelated or excluded PR.
_CONTEXT_EXCLUDE = re.compile(
    r"\b(?:not|never|no|don'?t|isn'?t|aren'?t|won'?t|red|fail(?:s|ed|ing)?|draft|blocked|"
    r"blocking|broken|excluded?|skip(?:ped)?|unrelated|closed|external|pending|wait(?:ing)?)\b",
    re.I,
)
#: GitHub issue-closing keywords: "Closes #45" names an issue.
_CLOSING_KEYWORD = re.compile(r"\b(?:close[sd]?|fix|fixes|resolve[sd]?)\s*:?\s*$", re.I)
_CONTEXT_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
#: A bare "#12" after these words numbers something other than a pull request.
_NOT_A_PR_BEFORE = re.compile(
    r"(?:issues?|steps?|items?|phases?|lines?|options?|todos?|rows?|no\.|number|finding|f)\s*$",
    re.I,
)


# --- prompt parsing ----------------------------------------------------------


def fold_text(text: str) -> str:
    """Typographic apostrophes and spaces folded to ASCII."""
    return text.translate(_FOLD)


def sanitize_prompt(text: str) -> str | None:
    """Prompt text that may carry an operator instruction, or None when relayed.

    Pasted blocks, system reminders, fenced code, block quotes and quoted spans
    are removed: text copied from a repository file, a PR comment, a report or a
    tool result is not an instruction even when the operator pasted or quoted it.
    Typographic apostrophes are folded only after quoted spans are gone, so a
    curly-quoted phrase is still stripped and "PR’s" / "don’t" still parse.
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
    return fold_text(cleaned)


def repo_from_token(token: str | None) -> str | None:
    """``owner/name`` from ``owner/name`` or a github.com URL, else None."""
    if not token:
        return None
    text = token.strip().strip("<>()[]{}\"'").rstrip(".,;:!?)]}>")
    match = _GITHUB_REPO_URL.match(text)
    if match:
        owner, name = match.group("owner"), match.group("name")
    elif re.fullmatch(_SLUG, text):
        owner, _, name = text.partition("/")
    else:
        return None
    name = name.removesuffix(".git").rstrip(".")
    slug = f"{owner}/{name}"
    return slug if re.fullmatch(_SLUG, slug) else None


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


def plausible_repo(slug: str, known_owners: frozenset[str] = frozenset()) -> bool:
    """A bare ``owner/name`` that reads as a repository, not prose or a path.

    "CI/CD", "and/or" and "ops/autonomy" are not repositories. A slug counts when
    its owner is already known (the workspace remote, a URL, a qualified
    reference) or its name looks like a repository name (a hyphen, dot or digit).
    """
    owner, _, name = slug.partition("/")
    if not owner or not name:
        return False
    if owner.casefold() in known_owners:
        return True
    return bool(re.search(r"[-.\d]", name))


def _slug_candidates(text: str, known_owners: frozenset[str] = frozenset()) -> list[str]:
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
        if not plausible_repo(slug, known_owners):
            continue
        found.append(slug)
    unique: list[str] = []
    for slug in found:
        if slug.casefold() not in {item.casefold() for item in unique}:
            unique.append(slug)
    return unique


def _known_owners(text: str, *repos: str | None) -> frozenset[str]:
    owners = {slug.partition("/")[0].casefold() for slug in _github_url_slugs(text)}
    owners.update(repo.partition("/")[0].casefold() for repo in repos if repo)
    return frozenset(owners)


def _github_url_slugs(text: str) -> list[str]:
    return [match.group("slug") for match in _GITHUB_URL_RE.finditer(text)]


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
        presented = match.group(0).strip().startswith(":") and not _INTERJECTION.match(chunk)
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
    stripped = sentence.strip()[:MAX_CLAUSE_CHARS]
    if _POLITE_CANCEL.match(stripped) and _is_negative(stripped):
        return False
    if _POLITE_REQUEST.match(stripped) and not _QUESTION_WORDS.search(stripped):
        return False
    if stripped.endswith("?"):
        return True
    # "When the checks pass, merge #96": a leading condition is not a question.
    for _ in range(3):
        condition = _CONDITION_LEAD.match(stripped)
        if not condition:
            break
        stripped = stripped[condition.end() :]
    lead = _QUESTION_LEAD.match(stripped)
    if not lead:
        return False
    return not _NEGATED_LEAD.match(stripped[lead.end() :])


def _is_negative(clause: str) -> bool:
    head = clause[:MAX_CLAUSE_CHARS]
    return bool(_NEGATION.search(head) or _REVOKE_VERB.search(head))


def _ref_repo(match: re.Match[str], known_owners: frozenset[str]) -> str | None:
    """The repository a reference carries; an implausible "and/or#96" carries none."""
    if match.group("url"):
        return match.group("url")
    qualified = match.group("qualified")
    if qualified and plausible_repo(qualified, known_owners):
        return qualified
    return None


def _refs_in_run(
    run: str, known_owners: frozenset[str] = frozenset()
) -> list[tuple[str | None, int]]:
    """Every reference in ``run``; a range ("#96 through #99") yields each member."""
    refs: list[tuple[str | None, int]] = []
    for match in _PR_REF_RANGE.finditer(run):
        repo = _ref_repo(match, known_owners)
        start = int(match.group("num"))
        refs.append((repo, start))
        end = match.group("end")
        if end and start < int(end) <= start + MAX_RANGE:
            refs.extend((repo, number) for number in range(start + 1, int(end) + 1))
    return refs


def _context_refs(texts: list[str]) -> list[tuple[str | None, int]]:
    """Pull-request references the conversation put forward, in order, deduplicated.

    Only what a sentence offers as ready counts: a sentence carrying a negation
    or a red, draft, blocked, closed, unrelated or external state contributes
    nothing ("#99 is a draft - do NOT merge"), and an issue-closing keyword
    ("Closes #45") names an issue. A bare ``#12`` after "issue", "step", "item"
    … numbers something else. A bare reference takes the repository of its
    message when that message names exactly one. Each turn is read up to
    ``MAX_AGENT_TURN_CHARS``.
    """
    found: list[tuple[str | None, int]] = []
    for raw in texts:
        text = fold_text(raw[:MAX_AGENT_TURN_CHARS])
        slugs = _repo_mentions(text)
        own = slugs[0] if len(slugs) == 1 else None
        known = frozenset(slug.partition("/")[0].casefold() for slug in slugs)
        for sentence in _CONTEXT_SENTENCE.split(text):
            if not sentence or _CONTEXT_EXCLUDE.search(sentence):
                continue
            found.extend(_sentence_refs(sentence, own, known))
    return _dedupe_refs(found)


def _sentence_refs(
    sentence: str, own: str | None, known: frozenset[str]
) -> list[tuple[str | None, int]]:
    found: list[tuple[str | None, int]] = []
    for match in _PR_REF_RANGE.finditer(sentence):
        before = sentence[max(0, match.start() - 16) : match.start()]
        if _CLOSING_KEYWORD.search(before):
            continue
        carried = _ref_repo(match, known)
        if not carried and match.group(0).startswith("#") and _NOT_A_PR_BEFORE.search(before):
            continue
        repo = repo_from_token(carried) or own
        start = int(match.group("num"))
        numbers = [start]
        end = match.group("end")
        if end and start < int(end) <= start + MAX_RANGE:
            numbers.extend(range(start + 1, int(end) + 1))
        found.extend((repo, number) for number in numbers)
    return found


def _dedupe_refs(found: list[tuple[str | None, int]]) -> list[tuple[str | None, int]]:
    unique: list[tuple[str | None, int]] = []
    keys: set[tuple[str | None, int]] = set()
    for repo, number in found:
        key = (repo.casefold() if repo else None, number)
        if key in keys:
            continue
        # A bare "#12" already known with its repository adds nothing.
        if repo is None and any(n == number for _, n in unique):
            continue
        keys.add(key)
        unique.append((repo, number))
    return unique[:MAX_CONTEXT_MEMBERS]


def _repo_mentions(text: str) -> list[str]:
    """Repositories a conversation turn names: URLs, qualified refs, and slugs
    that read as a repository rather than prose or a directory path."""
    found: list[str] = list(_github_url_slugs(text))
    for match in _PR_REF.finditer(text):
        qualified = match.group("qualified")
        if qualified and plausible_repo(qualified):
            found.append(qualified)
    anchored = frozenset(slug.partition("/")[0].casefold() for slug in found)
    found.extend(_slug_candidates(text, anchored))
    unique: list[str] = []
    for slug in found:
        repo = repo_from_token(slug)
        if repo and repo.casefold() not in {item.casefold() for item in unique}:
            unique.append(repo)
    return unique


class ConversationContext:
    """Pull requests and repositories the conversation has established.

    ``latest_refs`` are the references the agent put forward in its replies to
    the last human turn — what "these PRs" points at. ``recent_refs`` and
    ``repos`` span the last few exchanges; ``human_repos`` are the repositories
    the operator's own turns named. Read from the host-written transcript at
    recording time.
    """

    def __init__(
        self,
        latest_refs: list[tuple[str | None, int]] | None = None,
        recent_refs: list[tuple[str | None, int]] | None = None,
        repos: list[str] | None = None,
        human_repos: list[str] | None = None,
    ) -> None:
        self.latest_refs = list(latest_refs or [])
        self.recent_refs = list(recent_refs or [])
        self.repos = list(repos or [])
        self.human_repos = list(human_repos or [])

    def members(self) -> list[tuple[str | None, int]]:
        return self.latest_refs or self.recent_refs


def _single(repos: list[str]) -> str | None:
    unique = {repo.casefold(): repo for repo in repos}
    return next(iter(unique.values())) if len(unique) == 1 else None


def _resolve_repo(
    explicit: str | None,
    sentence_slugs: list[str],
    prompt_slugs: list[str],
    cwd_repo: str | None,
    *,
    context: ConversationContext | None = None,
    number: int | None = None,
    cohort: bool = False,
) -> tuple[str | None, str | None]:
    """``(repository, where it came from)``; ``(None, None)`` when unresolvable.

    The operator's words first (the reference, its sentence, the prompt), then
    a qualified reference to that exact number in the conversation, then the
    workspace remote, then the one repository the operator's own turns named.
    Only for a single pull request does the one repository the whole
    conversation discusses decide; agent text never names a cohort's repository.
    """
    if explicit:
        return repo_from_token(explicit) or explicit, "prompt"
    if len(sentence_slugs) == 1:
        return repo_from_token(sentence_slugs[0]) or sentence_slugs[0], "prompt"
    if len(prompt_slugs) == 1:
        return repo_from_token(prompt_slugs[0]) or prompt_slugs[0], "prompt"
    if context is not None and number is not None and not cohort:
        qualified = _single([repo for repo, n in context.recent_refs if n == number and repo])
        if qualified:
            return qualified, "conversation"
    if cwd_repo:
        return cwd_repo, "workspace"
    if context is None:
        return None, None
    named = _single(context.human_repos)
    if named:
        return named, "conversation"
    if not cohort:
        discussed = _single(context.repos)
        if discussed:
            return discussed, "conversation"
    return None, None


def _repo_by_name(
    word: str | None, prompt_slugs: list[str], context: ConversationContext | None, cwd: str | None
) -> str | None:
    """A repository written by name only ("in the l9-graphiti-memory repo")."""
    if not word:
        return None
    wanted = word.strip().strip(".,;:!?").casefold()
    if not wanted:
        return None
    candidates = (
        list(prompt_slugs) + list(context.repos if context else []) + ([cwd] if cwd else [])
    )
    exact = {c.casefold(): c for c in candidates if c.partition("/")[2].casefold() == wanted}
    if len(exact) == 1:
        return next(iter(exact.values()))
    partial = {c.casefold(): c for c in candidates if wanted in c.partition("/")[2].casefold()}
    return next(iter(partial.values())) if len(partial) == 1 else None


def _cohort_repo(match: re.Match[str]) -> tuple[str | None, str | None]:
    """(slug-or-url repository, name-only word) of a cohort match's repository slot."""
    token = match.group("repo")
    if not token:
        return None, None
    repo = repo_from_token(token)
    if repo:
        return repo, None
    return None, token


def _objects_after(
    tail: str, *, glue: re.Pattern[str], known_owners: frozenset[str] = frozenset()
) -> tuple[re.Match[str] | None, list[tuple[str | None, int]]]:
    """(cohort match, PR refs) named right after a merge verb; both empty when none.

    A cohort match counts only when it says "open" or names a repository;
    "merge all the PRs" is a contextual object, not a cohort. A run that opens
    with a plural PR noun carries bare numbers ("PRs 96, 97 and 98").
    """
    cohort = _COHORT_TAIL.match(tail)
    if cohort and (
        cohort.group("open1")
        or cohort.group("open2")
        or cohort.group("open3")
        or cohort.group("repo")
    ):
        return cohort, []
    stripped = glue.match(tail)
    rest = tail[stripped.end() :] if stripped else tail
    run = _REF_RUN.match(rest)
    if not run:
        return None, []
    refs = _refs_in_run(run.group(0), known_owners)
    if refs and _PLURAL_PR_LEAD.match(run.group(0)):
        more = _BARE_CONTINUATION.match(rest, run.end())
        if more:
            repo = refs[-1][0]
            refs.extend((repo, int(n)) for n in _BARE_NUMBER.findall(more.group(0)))
    return None, refs


def _directed_end(clause: str) -> int | None:
    """Offset just past the merge verb of a clause directed at the agent, else None.

    A leading condition ("once CI is green, merge #96") is looked through; the
    condition is the operator's, and the agent honours it before merging.
    """
    offset = 0
    text = clause[:MAX_CLAUSE_CHARS]
    for _ in range(3):
        condition = _CONDITION_LEAD.match(text)
        if not condition:
            break
        offset += condition.end()
        text = text[condition.end() :]
    strict = _DIRECTED.match(text)
    if strict:
        return offset + strict.end()
    loose = _LOOSE_DIRECTED.match(text)
    if not loose:
        return None
    pre = loose.group("pre")
    if _SUBJECT_START.match(pre) or _REPORTING.search(pre) or _MERGE_VERB.search(pre):
        return None
    return offset + loose.end()


def _deictic_object(tail: str) -> re.Match[str] | None:
    """A contextual object that names pull requests, not code being merged.

    "merge them into a single file", "merge it with the helper", "merge both
    dictionaries" and "merge these two functions" merge something else.
    """
    deictic = _DEICTIC.match(tail)
    if not deictic:
        return None
    after = tail[deictic.end() :]
    if _DEICTIC_OTHER_TARGET.match(after):
        return None
    names_prs = re.search(
        rf"(?:{_PR_NOUN}|ones|changes|fixes|branches|stack|train)$", deictic.group(0), re.I
    )
    if not names_prs and not _DEICTIC_CONTINUATION.match(after):
        return None
    return deictic


_MERGE_MENTION = re.compile(r"\bmerge\b[^.!?]{0,40}?(?:#\d|\bprs?\b|pull\s+request)", re.I)


def parse_prompt(
    prompt: str,
    *,
    cwd_repo: str | None = None,
    context: ConversationContext | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """``(instructions, notes)`` for ``prompt``.

    Each instruction: ``{"kind": "authorize"|"revoke", "scope": "pr"|"open_cohort"|"all",
    "repo": str|None, "pr": int|None, "excerpt": str, "source": str,
    "repo_source": str|None}``. ``source`` says where the pull request came
    from (``prompt``, ``range``, ``cohort``, ``conversation``, ``all``).

    An authorization is returned only for a clause directed at the agent
    (imperative or first person) that is not presented material. A revocation is
    returned for a clause whose negation governs merging a pull request.
    ``notes`` explain merge intent that resolved to nothing, so the hook can say
    so instead of staying silent.
    """
    cleaned = sanitize_prompt(prompt)
    if cleaned is None:
        return [], []
    known = _known_owners(cleaned, cwd_repo, *(context.repos if context else []))
    prompt_slugs = _slug_candidates(cleaned, known)
    #: References the operator named before the clause being read: the only
    #: antecedents a bare "don't merge it" may take ("Don't merge it, merge #97
    #: instead" never cancels #97).
    preceding: list[tuple[str | None, int]] = []
    found: list[dict[str, Any]] = []
    notes: list[str] = []
    seen: set[tuple[str, str, str | None, int | None]] = set()

    def _add(
        kind: str,
        scope: str,
        repo: str | None,
        pr: int | None,
        text: str,
        source: str,
        repo_source: str | None,
    ) -> None:
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
                "source": source,
                "repo_source": repo_source,
            }
        )

    def _refs(
        kind: str,
        refs: list[tuple[str | None, int]],
        text: str,
        source: str,
        sentence_slugs: list[str],
    ) -> None:
        for explicit, number in refs:
            repo, where = _resolve_repo(
                explicit,
                sentence_slugs,
                prompt_slugs,
                cwd_repo,
                context=context,
                number=number,
            )
            if repo is None and kind == KIND_AUTHORIZE:
                notes.append(
                    f"#{number}: the repository could not be resolved (name it as owner/name "
                    "or a github.com URL)"
                )
            _add(kind, SCOPE_PR, repo, number, text, source, where)

    def _cohort(kind: str, match: re.Match[str], text: str, sentence_slugs: list[str]) -> None:
        repo, word = _cohort_repo(match)
        where: str | None = "prompt" if repo else None
        if repo is None and word:
            repo = _repo_by_name(word, prompt_slugs, context, cwd_repo)
            where = "prompt" if repo else None
        if repo is None and not word:
            repo, where = _resolve_repo(
                None, sentence_slugs, prompt_slugs, cwd_repo, context=context, cohort=True
            )
        if repo is None:
            if kind == KIND_AUTHORIZE:
                notes.append(
                    "an open-pull-request cohort was named, but its repository could not be "
                    "resolved (name it as owner/name or a github.com URL)"
                )
            return
        _add(kind, SCOPE_COHORT, repo, None, text, "cohort", where)

    def _context_members(single: bool) -> list[tuple[str | None, int]] | None:
        members = context.members() if context is not None else []
        if not members:
            return None
        if single and len({(r or "").casefold() + f"#{n}" for r, n in members}) != 1:
            return None
        return members

    for sentence in _sentences(cleaned):
        if _is_question(sentence):
            continue
        before = len(found)
        sentence_slugs = _slug_candidates(sentence, known)
        sentence_preceding: list[tuple[str | None, int]] = []
        for clause, presented in _clauses(sentence):
            clause_refs = _refs_in_run(clause, known)
            negative = _is_negative(clause)
            if negative:
                _parse_cancellation(
                    clause,
                    sentence_refs=list(sentence_preceding),
                    prompt_refs=list(preceding),
                    sentence_slugs=sentence_slugs,
                    known_owners=known,
                    add=_add,
                    refs=_refs,
                    cohort=_cohort,
                    context_members=_context_members,
                )
            sentence_preceding.extend(clause_refs)
            preceding.extend(clause_refs)
            if negative or presented:
                continue
            end = _directed_end(clause)
            if end is None:
                continue
            tail = clause[end:]
            cohort, refs = _objects_after(tail, glue=_GLUE, known_owners=known)
            if cohort is not None:
                _cohort(KIND_AUTHORIZE, cohort, clause, sentence_slugs)
                continue
            if refs:
                source = "range" if len(refs) > len(_PR_REF.findall(tail)) else "prompt"
                _refs(KIND_AUTHORIZE, refs, clause, source, sentence_slugs)
                continue
            deictic = _deictic_object(tail)
            if deictic:
                single = bool(deictic.group("single"))
                # "Fix the CI on #96 and merge it": the clause itself names its object.
                named_before = _refs_in_run(clause[:end], known)
                if named_before and (not single or len(named_before) == 1):
                    _refs(KIND_AUTHORIZE, named_before, clause, "prompt", sentence_slugs)
                    continue
                members = _context_members(single)
                if members is None:
                    notes.append(
                        f"'{clause.strip()[:80]}' refers to pull requests from the conversation, "
                        + (
                            "but more than one is under discussion"
                            if single and context is not None and context.members()
                            else "but no pull request could be found in the recent conversation"
                        )
                    )
                    continue
                _refs(KIND_AUTHORIZE, members, clause, "conversation", sentence_slugs)
                continue
            if _PR_ISH.search(tail) and not _DEICTIC.match(tail):
                notes.append(
                    f"'{clause.strip()[:80]}' reads as a merge instruction, but no pull request "
                    "or repository could be resolved from it"
                )
        if len(found) == before and _MERGE_MENTION.search(sentence):
            notes.append(
                f"'{sentence.strip()[:80]}' mentions merging a pull request but was not read as "
                "a merge instruction; if the operator meant one, nothing was recorded"
            )
    return found, notes


def _parse_cancellation(
    clause: str,
    *,
    sentence_refs: list[tuple[str | None, int]],
    prompt_refs: list[tuple[str | None, int]],
    sentence_slugs: list[str],
    known_owners: frozenset[str],
    add: Callable[..., None],
    refs: Callable[..., None],
    cohort: Callable[..., None],
    context_members: Callable[[bool], list[tuple[str | None, int]] | None],
) -> None:
    """Record a negative clause as the narrowest cancellation that still covers it.

    Named objects first; then, for a bare cancellation ("don't merge it yet"),
    the pull requests the clause names, else those named before it in its
    sentence, else before it in the prompt; then, for a
    contextual object ("don't merge them"), the conversation's; then the one
    repository the clause names; then everything ("stop, don't merge yet").
    Not a cancellation: a merge whose object is something else ("don't merge
    main into it"), a scope limit ("don't merge anything else"), and a bare
    condition ("don't merge until CI is green", "do not merge before that").
    """
    named = False
    bare = False
    contextual = False
    for verb in _MERGE_VERB.finditer(clause[:MAX_CLAUSE_CHARS]):
        tail = clause[verb.end() : MAX_CLAUSE_CHARS]
        match, found = _objects_after(tail, glue=_REVOKE_GLUE, known_owners=known_owners)
        if match is not None:
            cohort(KIND_REVOKE, match, clause, sentence_slugs)
            named = True
            continue
        if found:
            refs(KIND_REVOKE, found, clause, "prompt", sentence_slugs)
            named = True
            continue
        short = _COHORT_REVOKE_SHORT.match(tail)
        if short and verb.group(0).lower() in {"merges", "merging", "merge"}:
            repo = repo_from_token(short.group("repo"))
            if repo:
                add(KIND_REVOKE, SCOPE_COHORT, repo, None, clause, "cohort", "prompt")
                named = True
                continue
        deictic = _DEICTIC.match(tail)
        if deictic and not re.match(r"\s*all\b", tail, re.I):
            contextual = True
        if _BARE_TAIL.match(tail) or deictic or _EVERYTHING.search(tail):
            bare = True
    if named or not bare:
        return
    if _SCOPE_LIMIT.search(clause) or _CONDITIONAL.search(clause):
        return
    if _EVERYTHING.search(clause):
        add(KIND_REVOKE, SCOPE_ALL, None, None, clause, "all", None)
        return
    for candidates in (_refs_in_run(clause, known_owners), sentence_refs, prompt_refs):
        if candidates:
            refs(KIND_REVOKE, candidates, clause, "prompt", sentence_slugs)
            return
    members = context_members(False) if contextual else None
    if members:
        refs(KIND_REVOKE, members, clause, "conversation", sentence_slugs)
        return
    slugs = _slug_candidates(clause, known_owners)
    if len(slugs) == 1 and repo_from_token(slugs[0]):
        add(KIND_REVOKE, SCOPE_COHORT, repo_from_token(slugs[0]), None, clause, "cohort", "prompt")
        return
    add(KIND_REVOKE, SCOPE_ALL, None, None, clause, "all", None)


def parse_instructions(
    prompt: str,
    *,
    cwd_repo: str | None = None,
    context: ConversationContext | None = None,
) -> list[dict[str, Any]]:
    """Explicit merge instructions in ``prompt``, authorizations and revocations.

    The instruction half of :func:`parse_prompt`. A PR instruction whose
    repository cannot be resolved is still returned with ``repo: None``; it
    binds nothing.
    """
    return parse_prompt(prompt, cwd_repo=cwd_repo, context=context)[0]


# --- conversation context ------------------------------------------------------


def _is_typed_human_record(record: dict[str, Any]) -> bool:
    if record.get("type") != "user" or "toolUseResult" in record:
        return False
    if record.get("isMeta") or record.get("isSidechain"):
        return False
    message = record.get("message")
    if not isinstance(message, dict) or message.get("role") != "user":
        return False
    return _record_is_human_turn(record) is True


def _is_relayed_record(record: dict[str, Any]) -> bool:
    """A user-role turn the host relayed (marked non-human), not a tool result."""
    if record.get("type") != "user" or "toolUseResult" in record:
        return False
    if record.get("isMeta") or record.get("isSidechain"):
        return False
    return _record_is_human_turn(record) is False


def _assistant_text(record: dict[str, Any]) -> str:
    if record.get("type") != "assistant" or record.get("isSidechain"):
        return ""
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


def _read_tail(path: Path) -> list[str] | None:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - TRANSCRIPT_TAIL_BYTES)
            handle.seek(start)
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    lines = raw.splitlines()
    return lines[1:] if start > 0 else lines


def conversation_context(
    transcript_path: str | Path | None,
    session_id: str,
    *,
    current_prompt: str | None = None,
    exchanges: int = CONTEXT_EXCHANGES,
) -> ConversationContext | None:
    """What the session's conversation has established, from the host transcript.

    Only typed human turns and the agent's visible replies count: tool results,
    relayed turns, meta records and sidechains are not conversation. The current
    prompt, if the host already wrote it, is not its own context. None when the
    transcript cannot be read.
    """
    if not transcript_path or not session_id:
        return None
    lines = _read_tail(Path(str(transcript_path)).expanduser())
    if lines is None:
        return None
    turns: list[tuple[str, str]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or str(record.get("sessionId") or "") != session_id:
            continue
        if _is_typed_human_record(record):
            text = _record_text(record)
            if text:
                turns.append(("human", text))
            continue
        if _is_relayed_record(record):
            # A webhook, task notification or cross-session message closes the
            # exchange: the agent's reply to it is not what "these PRs" means.
            turns.append(("relay", ""))
            continue
        text = _assistant_text(record)
        if text:
            turns.append(("agent", text))
    if current_prompt:
        digest = prompt_digest(current_prompt)
        current = _normalized(current_prompt)
        while (
            turns
            and turns[-1][0] == "human"
            and (prompt_digest(turns[-1][1]) == digest or _normalized(turns[-1][1]) == current)
        ):
            turns.pop()
    grouped: list[list[tuple[str, str]]] = []
    for role, text in turns:
        if role in {"human", "relay"} or not grouped:
            grouped.append([])
        grouped[-1].append((role, text))
    # Exchanges a relayed turn opened are not conversation with the operator.
    conversational = [group for group in grouped if group[0][0] != "relay"]
    recent = conversational[-exchanges:] if exchanges > 0 else []
    latest_agent = [text for role, text in (recent[-1] if recent else []) if role == "agent"]
    recent_texts = [text for exchange in recent for role, text in exchange if text]
    human_texts = [text for exchange in recent for role, text in exchange if role == "human"]
    return ConversationContext(
        latest_refs=_context_refs(latest_agent),
        recent_refs=_context_refs(recent_texts),
        repos=_mentioned_repos(recent_texts),
        human_repos=_mentioned_repos(human_texts),
    )


def _mentioned_repos(texts: list[str]) -> list[str]:
    """Repositories named in ``texts``, most recent first."""
    repos: list[str] = []
    for text in reversed(texts):
        for repo in _repo_mentions(fold_text(text[:MAX_AGENT_TURN_CHARS])):
            if repo.casefold() not in {item.casefold() for item in repos}:
                repos.append(repo)
    return repos


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
    return " ".join(fold_text(text).split()).casefold()


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
    """A well-formed receipt carrying the host hook's provenance, still in force.

    An authorization is in force until it expires. A cancellation is in force
    until a later authorization supersedes it: it has no expiry of its own,
    because its lapse would revive the authority it withdrew (§6.2.14).
    """
    expires = entry.get("expires_at")
    recorded = entry.get("recorded_at")
    if not isinstance(recorded, (int, float)) or isinstance(recorded, bool):
        return False
    if entry.get("recorder") != RECORDER or entry.get("kind") not in KINDS:
        return False
    host = str(entry.get("host") or "")
    if not _valid_provenance(host, entry.get("provenance"), str(entry.get("session_id") or "")):
        return False
    if entry.get("kind") == KIND_REVOKE:
        return recorded <= now
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        return False
    return recorded <= now < expires


def _retained(entries: list[dict[str, Any]], now: float) -> list[dict[str, Any]]:
    """Entries still in force, capped: authorizations and cancellations separately,
    so a burst of authorizations can never push a cancellation out of the store."""
    live = [entry for entry in entries if is_live(entry, now)]
    authorizations = [e for e in live if e.get("kind") == KIND_AUTHORIZE][-MAX_RECORDS:]
    revocations = [e for e in live if e.get("kind") == KIND_REVOKE]
    if len(revocations) > MAX_REVOCATIONS:
        # Drop cancellations a later grantable authorization has superseded
        # first; one still in force goes only when the cap leaves no choice.
        spent = [e for e in revocations if _superseded(e, live)]
        excess = len(revocations) - MAX_REVOCATIONS
        drop = {id(e) for e in spent[:excess]}
        revocations = [e for e in revocations if id(e) not in drop][-MAX_REVOCATIONS:]
    keep = {id(entry) for entry in authorizations + revocations}
    return [entry for entry in live if id(entry) in keep]


def _superseded(revocation: dict[str, Any], entries: list[dict[str, Any]]) -> bool:
    """A later grantable authorization with the same scope and target spent it."""
    if revocation.get("scope") == SCOPE_ALL:
        return False
    key = (
        revocation.get("scope"),
        str(revocation.get("repo") or "").casefold(),
        revocation.get("pr"),
    )
    return any(
        entry.get("kind") == KIND_AUTHORIZE
        and entry.get("host") in GRANTABLE_HOSTS
        and (entry.get("scope"), str(entry.get("repo") or "").casefold(), entry.get("pr")) == key
        and float(entry.get("recorded_at") or 0) > float(revocation.get("recorded_at") or 0)
        for entry in entries
    )


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


def capture_instructions(
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
    context: ConversationContext | None = None,
) -> dict[str, Any]:
    """Record every instruction in ``prompt``; return ``{"recorded", "notes"}``.

    Called by the host prompt hooks only, with the payload's provenance from
    :func:`host_provenance`; a missing or inconsistent provenance is a
    ``ValueError``, never a receipt. Cohort instructions snapshot the
    repository's open pull requests through ``open_pull_requests`` (GitHub REST
    by default); a snapshot that fails is stored as ``members: None`` and covers
    nothing. ``context`` is the conversation the host transcript established;
    contextual objects resolve against it here, once, and the resolved pull
    requests are what the receipts store. ``notes`` name merge intent that
    resolved to nothing. Lapsed receipts are pruned on every write.
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
    stamp = float(now) if now is not None else time.time()
    resolved_cwd_repo = cwd_repo if cwd_repo is not None else repo_from_cwd(cwd)
    parsed, notes = parse_prompt(prompt, cwd_repo=resolved_cwd_repo, context=context)
    if not parsed:
        return {"recorded": [], "notes": notes}
    lister = open_pull_requests or list_open_pull_requests
    digest = prompt_digest(prompt)
    target = path or default_store_path()
    kept = _retained(load_instructions(target), stamp)
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
            "expires_at": (stamp + int(ttl_seconds) if item["kind"] == KIND_AUTHORIZE else None),
            "scope": item["scope"],
            "repo": item.get("repo"),
            "pr": item.get("pr"),
            "source": item.get("source"),
            "repo_source": item.get("repo_source"),
            "excerpt": item["excerpt"],
            "prompt_sha256": digest,
            "provenance": dict(provenance),
        }
        if item["scope"] == SCOPE_COHORT and item["kind"] == KIND_AUTHORIZE and item.get("repo"):
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
    _write_store(target, _retained(kept, stamp))
    return {"recorded": written, "notes": notes}


def record_instructions(prompt: str, **kwargs: Any) -> list[dict[str, Any]]:
    """Append one receipt per instruction in ``prompt``; return them.

    :func:`capture_instructions` without the notes.
    """
    return capture_instructions(prompt, **kwargs)["recorded"]


def _covers(entry: dict[str, Any], repo: str, pr: int) -> tuple[bool, str]:
    if entry.get("scope") == SCOPE_ALL:
        if entry.get("kind") == KIND_REVOKE:
            return True, "cancellation of every pending merge"
        return False, "unknown scope"
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
    # Only an authorization that can itself become a grant spends a cancellation:
    # an unverifiable host's receipt (Cursor) must not revive an older grant.
    newer = [
        a
        for a in authorizations
        if float(a["recorded_at"]) > revoked_at and a.get("host") in GRANTABLE_HOSTS
    ]
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
    if entry.get("scope") == SCOPE_ALL:
        return f"{entry.get('kind')} every pending merge [id {entry['id']}]"
    target = f"{entry.get('repo') or '<repository unresolved: binds nothing>'}"
    if entry.get("scope") == SCOPE_PR:
        target += f"#{entry.get('pr')}"
        if entry.get("source") == "conversation":
            target += " (resolved from the conversation)"
    elif entry.get("kind") == KIND_REVOKE:
        target += " (every pull request)"
    else:
        members = entry.get("members")
        shown = (
            ", ".join(f"#{n}" for n in members)
            if isinstance(members, list)
            else "UNAVAILABLE — this cohort covers nothing"
        )
        target += f" (open pull requests at the time: {shown or 'none'})"
    return f"{entry.get('kind')} {target} [id {entry['id']}]"


def capture_from_payload(payload: dict[str, Any], host: str) -> dict[str, Any]:
    """``{"recorded", "notes", "provenance"}`` for one host prompt payload.

    On Claude Code the conversation context comes from the host transcript the
    payload names, read here in the hook process — never from anything the
    agent supplies.
    """
    provenance = host_provenance(host, payload)
    if provenance is None:
        return {"recorded": [], "notes": [], "provenance": None}
    prompt = _payload_prompt(payload)
    if not prompt:
        return {"recorded": [], "notes": [], "provenance": provenance}
    cwd = provenance.get("cwd")
    if cwd is None:
        roots = provenance.get("workspace_roots")
        cwd = roots[0] if isinstance(roots, list) and roots else None
    context = None
    if host in GRANTABLE_HOSTS:
        context = conversation_context(
            provenance.get("transcript_path"),
            str(provenance["session_id"]),
            current_prompt=prompt,
        )
    result = capture_instructions(
        prompt,
        host=host,
        session_id=str(provenance["session_id"]),
        cwd=cwd,
        provenance=provenance,
        context=context,
    )
    return {**result, "provenance": provenance}


def record_from_payload(payload: dict[str, Any], host: str) -> list[dict[str, Any]]:
    return capture_from_payload(payload, host)["recorded"]


def hook_context(recorded: list[dict[str, Any]], notes: list[str], failure: str | None) -> str:
    """The ``additionalContext`` the agent sees. Empty when the prompt had no merge intent.

    It never claims a capture that did not happen: a failure or an unresolved
    instruction says that nothing was authorized by it.
    """
    parts: list[str] = []
    if failure:
        parts.append(
            "L9 operator merge instruction recorder FAILED on this prompt "
            f"({failure}). NO merge authorization was captured from it; do not report one. "
            "Tell the operator the recorder failed and why."
        )
    authorized = [e for e in recorded if e.get("kind") == KIND_AUTHORIZE and e.get("repo")]
    unbound = [e for e in recorded if e.get("kind") == KIND_AUTHORIZE and not e.get("repo")]
    revoked = [e for e in recorded if e.get("kind") == KIND_REVOKE]
    empty_cohorts = [
        e
        for e in authorized
        if e.get("scope") == SCOPE_COHORT and not isinstance(e.get("members"), list)
    ]
    if authorized:
        listed = "; ".join(_describe(entry) for entry in authorized)
        parts.append(
            f"L9 operator merge instruction recorded (CANONICAL_LAW §6.2.13, §6.2.14): {listed}. "
            "This chat instruction IS the operator's merge authorization — including for a pull "
            "request the operator authored and for governance-protected paths. Do not ask the "
            "operator to repeat it, to post a GitHub comment or approval, or for any other "
            "confirmation. For each covered pull request: verify CI, mergeability, review "
            "threads and the stack at its live head; then run "
            '"$HOME/.cursor-governance/.venv/bin/python" '
            '"$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" --operator-instruction '
            "--repo <owner/name> --pr <n> --head-sha <live 40-hex> and "
            '"$HOME/.cursor-governance/.venv/bin/python" '
            '"$HOME/.cursor-governance/ops/autonomy/stack_safe_merge.py" --repo <owner/name> '
            "--pr <n> --head-sha <same sha> --run, stack parents bottom-up, and report GitHub's "
            'merge result. A conditional instruction ("when green") waits for its condition; '
            "a head moved by authorized remediation needs fresh technical checks, not a fresh "
            "instruction. A later cancellation withdraws this authority."
        )
    if empty_cohorts:
        parts.append(
            "The open-pull-request snapshot for "
            + ", ".join(str(e.get("repo")) for e in empty_cohorts)
            + " could not be taken, so that cohort authorizes NOTHING: "
            + "; ".join(str(e.get("membership_error") or "unavailable") for e in empty_cohorts)
            + ". Tell the operator; do not merge on it."
        )
    if unbound:
        parts.append(
            "Recorded but binding NOTHING (repository unresolved): "
            + ", ".join(f"#{e.get('pr')}" for e in unbound)
            + "."
        )
    if revoked:
        parts.append(
            "L9 operator merge CANCELLATION recorded: "
            + "; ".join(_describe(entry) for entry in revoked)
            + ". Every earlier operator authority it covers is withdrawn until the operator "
            "authorizes again; do not merge those pull requests."
        )
    if notes:
        parts.append(
            "Merge intent in this prompt that was NOT recorded, so it authorizes nothing: "
            + "; ".join(notes)
            + ". Ask the operator the one question that resolves it (which repository or which "
            "pull requests); do not claim authorization and do not ask for special wording."
        )
    return " ".join(parts)


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
    captured: dict[str, Any] = {"recorded": [], "notes": []}
    failure: str | None = None
    try:
        captured = capture_from_payload(payload, args.host)
    except Exception as exc:  # noqa: BLE001 - observer: never block a prompt, never hide it
        failure = f"{type(exc).__name__}: {exc}"[:300]
        print(f"WARN: operator merge instruction recorder degraded: {failure}", file=sys.stderr)
        prompt = _payload_prompt(payload) if host_provenance(args.host, payload) else ""
        if not (prompt and _MERGE_VERB.search(prompt)):
            failure = None
    if args.host == "cursor":
        print(json.dumps({"continue": True}))
        return 0
    context = hook_context(captured["recorded"], captured["notes"], failure)
    if context:
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
