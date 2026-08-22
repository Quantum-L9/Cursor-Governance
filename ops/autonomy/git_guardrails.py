#!/usr/bin/env python3
"""Context-sensitive git / filesystem guardrails.

Contract: ``l9-context-sensitive-git-guardrails`` v1.0.0 (mode ``strict``,
default ``guard_then_allow``).

The old model decided from the *subcommand name*: ``git`` was blanket-exempt
from execution denial (``git_execution_exemption``), while a handful of names
(``revert``, ``clean -f``, ``reset`` on a dirty tree) were blanket-denied. Both
halves are wrong in the same way — a name is not a risk. ``git reset --hard``
on a clean tree destroys nothing; ``git clean -fd`` over ``build/`` destroys
nothing; ``git restore`` over a file with no local changes destroys nothing.
The same commands over unrecoverable foreign edits destroy work permanently.

This module decides from four dimensions instead (contract ``risk_dimensions``):

    effect          what the command actually does to state
    sensitivity     whose state, and how replaceable it is
    recoverability  whether the state can be brought back afterwards
    blast_radius    how much state is in scope

and returns one of three outcomes:

    ALLOW                 run it
    GUARD_THEN_ALLOW      run observational guards / capture recovery, then run it
    DENY_REQUIRES_HUMAN   a human must authorize via L9_GIT_DESTRUCTIVE_AUTHORIZED

Invariants this module is the enforcement point for (contract ``invariants``):

    I001  a command name alone never determines destructive risk
    I003  read-only repository observation is unconditionally allowed
    I011  diagnostic probes are observational — never ``git stash`` as a probe
    I012  a guardrail never mutates the state it is protecting
    I013  compound commands are classified by effects, not by the loudest token
    I015  parser uncertainty never upgrades a sensitive mutation to ALLOW
    I016  policy-evaluator failure never blocks read-only git
    I017  policy-evaluator failure never allows unrecoverable sensitive mutation

Brain lives under ops/ per CANONICAL_LAW §2.1. Consumed by
``local_execution_gate`` (Claude PreToolUse + Cursor beforeShellExecution) and
by ``worktree_isolation_gate`` for the ``git clean`` classification.

Human authorization (human / ops only — never agent self-issued):
  L9_GIT_DESTRUCTIVE_AUTHORIZED=<reason>
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path, PurePosixPath

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    segment_head,
    segment_words,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)

CONTRACT_ID = "l9-context-sensitive-git-guardrails"
CONTRACT_VERSION = "1.0.0"

HUMAN_AUTHORIZATION_ENV = "L9_GIT_DESTRUCTIVE_AUTHORIZED"

#: Values that are a rubber stamp rather than the contract's "explicit reason".
_EMPTY_AUTHORIZATION_REASONS = frozenset({"1", "0", "y", "yes", "no", "true", "false", "ok"})


class Outcome(Enum):
    """Contract ``execution_outcomes``, ordered least → most restrictive."""

    ALLOW = "ALLOW"
    GUARD_THEN_ALLOW = "GUARD_THEN_ALLOW"
    DENY_REQUIRES_HUMAN = "DENY_REQUIRES_HUMAN"

    @property
    def rank(self) -> int:
        return _OUTCOME_RANK[self]


_OUTCOME_RANK = {
    Outcome.ALLOW: 0,
    Outcome.GUARD_THEN_ALLOW: 1,
    Outcome.DENY_REQUIRES_HUMAN: 2,
}


class Effect(Enum):
    """Contract ``risk_dimensions.effect``."""

    OBSERVE_ONLY = "observe_only"
    INDEX_MUTATION = "index_mutation"
    WORKTREE_OVERWRITE = "worktree_overwrite"
    UNTRACKED_DELETION = "untracked_deletion"
    LOCAL_REF_MOVE = "local_ref_move"
    LOCAL_REF_DELETE = "local_ref_delete"
    HISTORY_REWRITE = "history_rewrite"
    REMOTE_REF_UPDATE = "remote_ref_update"
    REMOTE_REF_REWRITE = "remote_ref_rewrite"
    REMOTE_REF_DELETE = "remote_ref_delete"
    RECOVERY_OBJECT_DELETE = "recovery_object_delete"
    FILESYSTEM_DELETE = "filesystem_delete"


class Sensitivity(Enum):
    """Contract ``risk_dimensions.sensitivity``."""

    EPHEMERAL_SCRATCH = "ephemeral_scratch"
    GENERATED = "generated"
    AGENT_OWNED = "agent_owned"
    CLEAN_REPOSITORY_STATE = "clean_repository_state"
    USER_UNCOMMITTED = "user_uncommitted"
    FOREIGN_UNCOMMITTED = "foreign_uncommitted"
    PRIVATE_LOCAL_BRANCH = "private_local_branch"
    PRIVATE_REMOTE_BRANCH = "private_remote_branch"
    SHARED_BRANCH = "shared_branch"
    PROTECTED_BRANCH = "protected_branch"
    REPOSITORY_RECOVERY_STATE = "repository_recovery_state"
    UNKNOWN = "unknown"


class Recoverability(Enum):
    """Contract ``risk_dimensions.recoverability``."""

    NO_STATE_AT_RISK = "no_state_at_risk"
    DETERMINISTIC_REGENERATION = "deterministic_regeneration"
    PRE_OPERATION_PATCH = "pre_operation_patch"
    BACKUP_REF = "backup_ref"
    SAFETY_COMMIT = "safety_commit"
    EXPLICIT_REMOTE_LEASE = "explicit_remote_lease"
    UNCERTAIN = "uncertain"
    NONE = "none"


class BlastRadius(Enum):
    """Contract ``risk_dimensions.blast_radius``."""

    NONE = "none"
    SINGLE_KNOWN_PATH = "single_known_path"
    BOUNDED_KNOWN_PATH_SET = "bounded_known_path_set"
    DISPOSABLE_DIRECTORY = "disposable_directory"
    ENTIRE_WORKTREE = "entire_worktree"
    LOCAL_BRANCH = "local_branch"
    REMOTE_BRANCH = "remote_branch"
    REPOSITORY_OBJECT_DATABASE = "repository_object_database"
    UNKNOWN = "unknown"


class Purpose(Enum):
    """Why the agent is running the operation (contract ``diagnostic_policy``)."""

    TASK_OPERATION = "explicit_task_operation"
    DIAGNOSTIC_PROBE = "diagnostic_probe"


class Ownership(Enum):
    """Contract ``ownership`` — who a changed path belongs to."""

    EPHEMERAL = "ephemeral_scratch"
    GENERATED = "generated"
    AGENT_OWNED = "agent_owned"
    USER_OR_FOREIGN = "user_or_foreign"


@dataclass(frozen=True)
class Finding:
    """One classified effect of one command segment."""

    outcome: Outcome
    effect: Effect
    operation: str
    reason: str
    sensitivity: Sensitivity = Sensitivity.UNKNOWN
    recoverability: Recoverability = Recoverability.UNCERTAIN
    blast_radius: BlastRadius = BlastRadius.UNKNOWN
    #: True when GUARD_THEN_ALLOW must capture recovery evidence before running.
    needs_recovery_capture: bool = False


@dataclass(frozen=True)
class Decision:
    """Effective outcome for a whole (possibly compound) command."""

    outcome: Outcome
    findings: tuple[Finding, ...]
    reason: str = ""

    @property
    def needs_recovery_capture(self) -> bool:
        return any(item.needs_recovery_capture for item in self.findings)

    @property
    def deciding(self) -> Finding | None:
        """The finding that set the effective outcome."""
        ranked = [item for item in self.findings if item.outcome is self.outcome]
        return ranked[0] if ranked else None


# ---------------------------------------------------------------------------
# Path classification — regenerable / ephemeral / governance-generated
# ---------------------------------------------------------------------------

#: Paths a build or generator reproduces deterministically. Deleting one costs
#: a rebuild, never work (contract ``recoverability.deterministic_regeneration``).
REGENERABLE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"^build/",
        r"^dist/",
        r"^target/",
        r"^out/",
        r"^node_modules/",
        r"(^|/)__pycache__/",
        r"(^|/)\.pytest_cache/",
        r"(^|/)\.mypy_cache/",
        r"(^|/)\.ruff_cache/",
        r"(^|/)\.tox/",
        r"(^|/)\.coverage($|\.)",
        r"(^|/)htmlcov/",
        r"(^|/)\.venv/",
        r"[^/]+\.egg-info/",
        r"(^|/)\.DS_Store$",
        r"\.pyc$",
        r"\.pyo$",
    )
)

#: Governance artifacts regenerated by ops/scripts/sync_generated_artifacts.py.
#: Kept in sync with GENERATED_PATH_PREFIXES there; duplicated rather than
#: imported so a hook never pays that module's import cost. The copy is a
#: strict subset: see DELIBERATELY_NOT_GENERATED for the entries this gate
#: refuses to treat as disposable, and test_generated_prefixes_have_not_drifted
#: for the drift check that keeps the two lists honest.
GENERATED_PATH_PREFIXES: tuple[str, ...] = (
    "rules/RULES-MANIFEST.",
    "environment/generated/llm-rules/",
    "ops/generated/skill-registry.json",
    "environment/agents/adapters/claude-code/generated/skill-registry.json",
    "environment/agents/adapters/claude-code/settings.template.json",
    "commands/COMMANDS_MANIFEST.yaml",
    "environment/program-execution/core/MANIFEST.yaml",
    "environment/program-execution/core/program-execution-blueprint-template/MANIFEST.yaml",
    "environment/program-execution/core/program-execution-controller-template/MANIFEST.yaml",
)

#: Paths the sync script regenerates but this gate must NOT call disposable.
#: ``skills/AUTONOMY_MANIFEST.yaml`` is the hand-authored routing SSOT (rule 53
#: keeps it off the generated merge driver for the same reason), and the PE
#: manifest is advisory and never auto-synced (TODO.md), so neither is produced
#: by a gate-run generator. Destroying a local edit to either would lose work.
DELIBERATELY_NOT_GENERATED: tuple[str, ...] = (
    "skills/AUTONOMY_MANIFEST.yaml",
    "environment/program-execution/MANIFEST.json",
)

#: Machine-local, never-tracked agent state.
EPHEMERAL_PREFIXES: tuple[str, ...] = (".l9/", ".cursor/plans/", ".cursor/governance/")

#: Environment variables that name a session scratch root.
SCRATCH_ROOT_ENV: tuple[str, ...] = (
    "L9_SCRATCH_ROOT",
    "CLAUDE_SCRATCHPAD",
    "CLAUDE_SCRATCHPAD_DIR",
)

#: Filesystem roots that must never be the target of a recursive delete.
_NEVER_DELETE_NAMES = frozenset({"/", "/home", "/root", "/usr", "/etc", "/var", "/opt"})


def _normalize_rel(rel: str) -> str:
    """Strip a leading ``./`` and a trailing ``/`` — nothing else.

    A character-set strip of the two characters dot and slash eats the leading
    dot of ``.pytest_cache/`` and turns a known cache directory into an unknown
    path, which then reads as user content the clean gate must deny.
    """
    while rel.startswith("./"):
        rel = rel[2:]
    return rel.rstrip("/")


def is_generated_path(rel: str) -> bool:
    """True for a governance artifact a generator rewrites deterministically.

    The carve-out is checked first and on purpose. Today no entry in
    GENERATED_PATH_PREFIXES would match a carved-out path, so the guard changes
    nothing — but a later broad prefix (``skills/``, ``environment/
    program-execution/``) would silently reclassify a hand-authored SSOT as
    disposable, and this gate decides whether work can be destroyed.
    """
    rel = _normalize_rel(rel)
    if any(rel == carve or rel.startswith(f"{carve}/") for carve in DELIBERATELY_NOT_GENERATED):
        return False
    if any(
        rel.startswith(prefix) or rel == prefix.rstrip(".") for prefix in GENERATED_PATH_PREFIXES
    ):
        return True
    return bool(re.match(r"^skills/[^/]+/SKILL\.md$", rel))


def is_regenerable_path(rel: str) -> bool:
    """True for build output / caches — deterministic regeneration, no work lost.

    ``git clean -nd`` reports directories with a trailing slash and the oracle
    normalizes it away, so both spellings are tested: ``build`` and ``build/``
    must classify identically or a preflight-proven safe target reads as unknown.
    """
    rel = _normalize_rel(rel)
    return any(pattern.search(rel) or pattern.search(f"{rel}/") for pattern in REGENERABLE_PATTERNS)


def is_ephemeral_path(rel: str) -> bool:
    rel = _normalize_rel(rel)
    return any(rel.startswith(prefix) for prefix in EPHEMERAL_PREFIXES)


# ---------------------------------------------------------------------------
# Probes — observational only (contract I011 / guard_actions.observational_preflight)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirtyPath:
    """One path with uncommitted state, and who it belongs to."""

    path: str
    ownership: Ownership


class ProbeError(RuntimeError):
    """A probe could not determine repository state.

    Callers turn this into DENY for a potentially destructive effect and into
    ALLOW for a provably observational one (contract ``failure_policy``).
    """


class Probe:
    """Read-only view of repository state.

    Every method is observational. Nothing here writes, stages, stashes, or
    resets — a guardrail must not mutate the state it is protecting (I012).
    """

    def dirty_paths(self) -> tuple[DirtyPath, ...]:
        raise ProbeError("dirty_paths unavailable")

    def clean_preview(self, flags: Sequence[str], paths: Sequence[str]) -> tuple[str, ...]:
        raise ProbeError("clean preview unavailable")

    def current_branch(self) -> str | None:
        raise ProbeError("current_branch unavailable")

    def head_is_published(self) -> bool:
        raise ProbeError("head publication state unavailable")

    def branch_has_unique_commits(self, branch: str) -> bool:
        raise ProbeError("branch uniqueness unavailable")

    def remote_lease_known(self, remote: str, branch: str) -> bool:
        """True when the expected remote SHA is known locally (a real lease)."""
        raise ProbeError("remote lease state unavailable")

    def can_capture_patch(self) -> bool:
        """True when a pre-operation binary patch can be written and verified."""
        return False


@dataclass(frozen=True)
class StaticProbe(Probe):
    """Probe backed by supplied facts. Used by tests and by callers that know."""

    dirty: tuple[DirtyPath, ...] = ()
    clean_targets: tuple[str, ...] = ()
    branch: str | None = None
    published_head: bool | None = None
    unique_commits: bool | None = None
    lease_known: bool | None = None
    capture_capable: bool = False

    def dirty_paths(self) -> tuple[DirtyPath, ...]:
        return self.dirty

    def clean_preview(self, flags: Sequence[str], paths: Sequence[str]) -> tuple[str, ...]:
        return self.clean_targets

    def current_branch(self) -> str | None:
        return self.branch

    def head_is_published(self) -> bool:
        if self.published_head is None:
            raise ProbeError("head publication state unavailable")
        return self.published_head

    def branch_has_unique_commits(self, branch: str) -> bool:
        if self.unique_commits is None:
            raise ProbeError("branch uniqueness unavailable")
        return self.unique_commits

    def remote_lease_known(self, remote: str, branch: str) -> bool:
        if self.lease_known is None:
            raise ProbeError("remote lease state unavailable")
        return self.lease_known

    def can_capture_patch(self) -> bool:
        return self.capture_capable


class LiveProbe(Probe):
    """Probe that reads a real repository with read-only git commands."""

    def __init__(self, root: Path, *, ownership: OwnershipOracle | None = None) -> None:
        self.root = root
        self.ownership = ownership or OwnershipOracle()

    def _git(self, *args: str, timeout: int = 10) -> str:
        try:
            proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                ["git", "-C", str(self.root), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ProbeError(f"git {' '.join(args)} failed: {exc}") from exc
        if proc.returncode != 0:
            raise ProbeError(f"git {' '.join(args)} exited {proc.returncode}")
        return proc.stdout

    def dirty_paths(self) -> tuple[DirtyPath, ...]:
        out = self._git("status", "--porcelain")
        found: list[DirtyPath] = []
        for line in out.splitlines():
            if len(line) < 4:
                continue
            path = line[3:].strip()
            if " -> " in path:  # rename: the destination is what is at risk
                path = path.split(" -> ", 1)[1]
            path = path.strip('"')
            found.append(DirtyPath(path, self.ownership.classify(path)))
        return tuple(found)

    def clean_preview(self, flags: Sequence[str], paths: Sequence[str]) -> tuple[str, ...]:
        args = ["clean", "-n", *flags, *(["--", *paths] if paths else [])]
        out = self._git(*args)
        targets: list[str] = []
        for line in out.splitlines():
            if line.startswith("Would remove "):
                targets.append(line[len("Would remove ") :].strip())
            elif line.startswith("Would skip "):
                continue
        return tuple(targets)

    def current_branch(self) -> str | None:
        branch = self._git("branch", "--show-current").strip()
        return branch or None

    def head_is_published(self) -> bool:
        return bool(self._git("branch", "-r", "--contains", "HEAD").strip())

    def branch_has_unique_commits(self, branch: str) -> bool:
        out = self._git(
            "rev-list",
            "--count",
            branch,
            "--not",
            "--remotes",
            f"--exclude=refs/heads/{branch}",
            "--branches",
        )
        try:
            return int(out.strip()) > 0
        except ValueError as exc:
            raise ProbeError("unreadable rev-list count") from exc

    def remote_lease_known(self, remote: str, branch: str) -> bool:
        ref = f"refs/remotes/{remote}/{branch}"
        return bool(self._git("rev-parse", "--verify", "--quiet", ref).strip())

    def can_capture_patch(self) -> bool:
        try:
            self._git("rev-parse", "HEAD")
        except ProbeError:
            return False
        return True


# ---------------------------------------------------------------------------
# Ownership (contract ``ownership``)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OwnershipOracle:
    """Classifies a changed path's owner.

    Fail-closed by construction: anything not *proven* agent-owned, generated,
    or ephemeral is ``USER_OR_FOREIGN`` — the contract's default sensitivity.
    Ownership is never inferred from cwd, branch name, or mtime.
    """

    session_owned: frozenset[str] = frozenset()
    generated: frozenset[str] = frozenset()
    ephemeral: frozenset[str] = frozenset()

    def classify(self, rel: str) -> Ownership:
        rel = _normalize_rel(rel)
        if rel in self.ephemeral or is_ephemeral_path(rel):
            return Ownership.EPHEMERAL
        if rel in self.generated or is_generated_path(rel) or is_regenerable_path(rel):
            return Ownership.GENERATED
        if rel in self.session_owned:
            return Ownership.AGENT_OWNED
        return Ownership.USER_OR_FOREIGN


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GuardContext:
    """Everything the decision matrix needs beyond the command text itself."""

    root: Path | None = None
    env: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    probe: Probe = field(default_factory=Probe)
    purpose: Purpose = Purpose.TASK_OPERATION
    ownership: OwnershipOracle = field(default_factory=OwnershipOracle)
    #: Recovery evidence that already exists for this operation.
    recovery_available: frozenset[Recoverability] = frozenset()
    #: Verified session-scratch roots; a recursive delete inside one is safe.
    scratch_roots: tuple[Path, ...] = ()
    #: The whole checkout is throwaway (a disposable clone / export).
    disposable_repo: bool = False
    #: Branches proven to belong to this agent alone.
    private_branches: frozenset[str] = frozenset()
    protected_branches: frozenset[str] = frozenset({"main", "master"})
    protected_branch_prefixes: tuple[str, ...] = ("release/", "campaign/")
    private_branch_prefixes: tuple[str, ...] = ()
    #: Remote refs proven disposable (throwaway test refs).
    disposable_remote_refs: frozenset[str] = frozenset()

    def branch_sensitivity(self, branch: str | None) -> Sensitivity:
        """Classify a branch. Unknown is never treated as private (I015)."""
        if not branch:
            return Sensitivity.UNKNOWN
        name = branch.split(":")[-1].removeprefix("refs/heads/").lstrip("+")
        if name in self.protected_branches or name.startswith(self.protected_branch_prefixes):
            return Sensitivity.PROTECTED_BRANCH
        if name in self.private_branches or (
            self.private_branch_prefixes and name.startswith(self.private_branch_prefixes)
        ):
            return Sensitivity.PRIVATE_REMOTE_BRANCH
        return Sensitivity.SHARED_BRANCH


def live_context(root: Path | None, **overrides: object) -> GuardContext:
    """Context wired to a real checkout, for the execution gates."""
    env = dict(os.environ)
    oracle = OwnershipOracle()
    probe: Probe = LiveProbe(root, ownership=oracle) if root is not None else Probe()
    scratch = _scratch_roots_from_env(env)
    base = GuardContext(
        root=root,
        env=env,
        probe=probe,
        ownership=oracle,
        scratch_roots=scratch,
        private_branch_prefixes=_private_prefixes_from_env(env),
    )
    return replace(base, **overrides) if overrides else base  # type: ignore[arg-type]


def _scratch_roots_from_env(env: Mapping[str, str]) -> tuple[Path, ...]:
    roots: list[Path] = []
    for key in SCRATCH_ROOT_ENV:
        value = env.get(key, "").strip()
        if not value:
            continue
        try:
            roots.append(Path(value).resolve())
        except OSError:
            continue
    return tuple(roots)


def _private_prefixes_from_env(env: Mapping[str, str]) -> tuple[str, ...]:
    raw = env.get("L9_PRIVATE_BRANCH_PREFIXES", "agent/,claude/,codex/,gemini/")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def human_authorized(env: Mapping[str, str]) -> bool:
    """True when a human supplied an explicit reason for destructive work.

    A bare truthy flag is not a reason: the contract requires the authorization
    to be non-empty *and* explicit, and forbids agent self-authorization.
    """
    reason = env.get(HUMAN_AUTHORIZATION_ENV, "").strip()
    if not reason or reason.lower() in _EMPTY_AUTHORIZATION_REASONS:
        return False
    return len(reason) >= 8


# ---------------------------------------------------------------------------
# Read-only git (contract ``read_only_git``)
# ---------------------------------------------------------------------------

#: Subcommands with no mutating form at all.
READ_ONLY_SUBCOMMANDS = frozenset(
    {
        "status",
        "diff",
        "log",
        "show",
        "grep",
        "blame",
        "rev-parse",
        "rev-list",
        "merge-base",
        "ls-files",
        "ls-tree",
        "ls-remote",
        "describe",
        "cat-file",
        "shortlog",
        "whatchanged",
        "archive",
        "fetch",
        "version",
        "help",
        "check-ignore",
        "check-attr",
        "count-objects",
        "verify-commit",
        "name-rev",
        "for-each-ref",
        "merge-tree",
        "diff-tree",
        "diff-index",
        "symbolic-ref",
    }
)

#: Subcommands read-only only in some argument forms.
_CONDITIONAL_READ_ONLY: dict[str, tuple[frozenset[str], bool]] = {
    # subcommand -> (read-only flags/args, read-only when no args at all)
    "branch": (
        frozenset(
            {
                "--show-current",
                "--list",
                "-l",
                "-a",
                "-r",
                "-v",
                "-vv",
                "--contains",
                "--merged",
                "--no-merged",
            }
        ),
        True,
    ),
    "tag": (frozenset({"--list", "-l", "-n", "--contains", "--points-at"}), True),
    "reflog": (frozenset({"show"}), True),
    "config": (frozenset({"--get", "--get-all", "--get-regexp", "--list", "-l"}), False),
    "remote": (frozenset({"-v", "--verbose", "show", "get-url"}), True),
    "stash": (frozenset({"list", "show"}), False),
    "worktree": (frozenset({"list"}), False),
    "notes": (frozenset({"list", "show"}), True),
    "bisect": (frozenset({"log", "view"}), False),
    "submodule": (frozenset({"status", "summary"}), False),
}


def _is_read_only_git(words: Sequence[str]) -> bool:
    """True when this git invocation only observes state (I003).

    Purely textual: it must stay correct with every governance dependency down
    (T029), so it never consults a probe, Graphiti, or the filesystem.
    """
    sub, args = _git_subcommand(words)
    if sub is None:
        return False
    if sub in READ_ONLY_SUBCOMMANDS:
        return True
    conditional = _CONDITIONAL_READ_ONLY.get(sub)
    if conditional is None:
        return False
    allowed, empty_is_read_only = conditional
    positional = [arg for arg in args if not arg.startswith("-")]
    flags = [arg.split("=", 1)[0] for arg in args if arg.startswith("-")]
    if not args:
        return empty_is_read_only
    if positional and positional[0] in allowed:
        return True
    # A read-only flag set stays read-only whatever it is asked about:
    # `config --get user.email` names a key, `branch --contains HEAD` a commit.
    return bool(flags) and all(flag in allowed for flag in flags)


#: Narrow last-resort match for the failure policy: a bare read-only git call
#: with no separator, quote, substitution, or redirection.
_PLAIN_READ_ONLY_RE = re.compile(
    r"^\s*git\s+(?P<sub>[a-z-]+)(?:\s+[^\s'\"`$;&|<>()]+)*\s*$",
)


def _looks_provably_read_only(command: str) -> bool:
    match = _PLAIN_READ_ONLY_RE.match(command)
    if not match:
        return False
    return match.group("sub") in READ_ONLY_SUBCOMMANDS


# ---------------------------------------------------------------------------
# git argument helpers
# ---------------------------------------------------------------------------

_GIT_GLOBAL_WITH_ARG = frozenset({"-C", "--git-dir", "--work-tree", "--namespace", "-c"})


def _git_subcommand(words: Sequence[str]) -> tuple[str | None, list[str]]:
    """Return ``(subcommand, args)`` skipping env prefixes and global options."""
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    if index >= len(words) or PurePosixPath(words[index]).name != "git":
        return None, []
    index += 1
    while index < len(words):
        word = words[index]
        if word in _GIT_GLOBAL_WITH_ARG:
            index += 2
            continue
        if word.startswith("--") and "=" in word:
            index += 1
            continue
        if word.startswith("-"):
            index += 1
            continue
        break
    if index >= len(words):
        return None, []
    return words[index], list(words[index + 1 :])


def _has_flag(args: Sequence[str], *names: str) -> bool:
    for arg in args:
        base = arg.split("=", 1)[0]
        if base in names:
            return True
        # bundled short flags: -fd contains -f and -d
        if arg.startswith("-") and not arg.startswith("--"):
            for name in names:
                if len(name) == 2 and name.startswith("-") and name[1] in arg[1:]:
                    return True
    return False


def _pathspec(args: Sequence[str]) -> list[str]:
    """Paths after ``--``, else trailing non-flag args."""
    if "--" in args:
        return [arg for arg in args[args.index("--") + 1 :] if arg]
    return [arg for arg in args if not arg.startswith("-")]


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _allow(effect: Effect, operation: str, reason: str, **kwargs: object) -> Finding:
    return Finding(Outcome.ALLOW, effect, operation, reason, **kwargs)  # type: ignore[arg-type]


def _guard(effect: Effect, operation: str, reason: str, **kwargs: object) -> Finding:
    return Finding(Outcome.GUARD_THEN_ALLOW, effect, operation, reason, **kwargs)  # type: ignore[arg-type]


def _deny(effect: Effect, operation: str, reason: str, **kwargs: object) -> Finding:
    return Finding(Outcome.DENY_REQUIRES_HUMAN, effect, operation, reason, **kwargs)  # type: ignore[arg-type]


def _dirty_at_risk(ctx: GuardContext, paths: Sequence[str] | None = None) -> tuple[DirtyPath, ...]:
    """Uncommitted state a worktree-overwriting op would destroy.

    Raises ``ProbeError`` when the answer cannot be determined — the caller
    turns that into DENY for a destructive effect (I017).
    """
    dirty = ctx.probe.dirty_paths()
    if paths is None:
        return dirty
    wanted = {_normalize_rel(path) for path in paths}
    if not wanted:
        return dirty
    selected: list[DirtyPath] = []
    for item in dirty:
        rel = _normalize_rel(item.path)
        if rel in wanted or any(rel.startswith(f"{path}/") for path in wanted):
            selected.append(item)
    return tuple(selected)


def _sensitive(entries: Iterable[DirtyPath]) -> tuple[DirtyPath, ...]:
    return tuple(item for item in entries if item.ownership is Ownership.USER_OR_FOREIGN)


def _worktree_recoverability(ctx: GuardContext) -> Recoverability:
    """Best recovery available for tracked worktree content."""
    for kind in (
        Recoverability.PRE_OPERATION_PATCH,
        Recoverability.SAFETY_COMMIT,
        Recoverability.BACKUP_REF,
    ):
        if kind in ctx.recovery_available:
            return kind
    if ctx.probe.can_capture_patch():
        # The gate will capture and verify a binary patch before the command
        # runs; that is the contract's provable pre-operation recovery.
        return Recoverability.PRE_OPERATION_PATCH
    return Recoverability.NONE


def _overwrite_finding(
    ctx: GuardContext,
    operation: str,
    *,
    paths: Sequence[str] | None,
    blast: BlastRadius,
    effect: Effect = Effect.WORKTREE_OVERWRITE,
) -> Finding:
    """Decision matrix for an effect that overwrites tracked worktree content."""
    at_risk = _dirty_at_risk(ctx, paths)
    if not at_risk:
        return _allow(
            effect,
            operation,
            f"{operation}: no uncommitted state at the target — nothing to lose",
            sensitivity=Sensitivity.CLEAN_REPOSITORY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    if all(item.ownership in (Ownership.GENERATED, Ownership.EPHEMERAL) for item in at_risk):
        return _allow(
            effect,
            operation,
            f"{operation}: every affected path is generated or ephemeral — "
            "deterministic regeneration",
            sensitivity=Sensitivity.GENERATED,
            recoverability=Recoverability.DETERMINISTIC_REGENERATION,
            blast_radius=blast,
        )
    sensitive = _sensitive(at_risk)
    sensitivity = Sensitivity.USER_UNCOMMITTED if sensitive else Sensitivity.AGENT_OWNED
    recovery = _worktree_recoverability(ctx)
    if recovery is Recoverability.NONE:
        names = ", ".join(item.path for item in (sensitive or at_risk)[:5])
        return _deny(
            effect,
            operation,
            f"{operation}: would overwrite uncommitted work with no provable "
            f"recovery ({names}). Capture a pre-operation patch or a safety "
            f"commit first, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=sensitivity,
            recoverability=Recoverability.NONE,
            blast_radius=blast,
        )
    return _guard(
        effect,
        operation,
        f"{operation}: uncommitted work affected; recovery is provable "
        f"({recovery.value}) — capture it, then proceed",
        sensitivity=sensitivity,
        recoverability=recovery,
        blast_radius=blast,
        needs_recovery_capture=recovery is Recoverability.PRE_OPERATION_PATCH,
    )


# ---------------------------------------------------------------------------
# Per-operation classifiers
# ---------------------------------------------------------------------------


def _classify_stash(ctx: GuardContext, args: Sequence[str]) -> Finding:
    action = next((arg for arg in args if not arg.startswith("-")), "push")
    operation = f"git stash {action}"
    if action in {"list", "show"}:
        return _allow(Effect.OBSERVE_ONLY, operation, "stash inspection is read-only")
    if ctx.purpose is Purpose.DIAGNOSTIC_PROBE:
        return _deny(
            Effect.WORKTREE_OVERWRITE,
            operation,
            "diagnostic probes must be observational (I011): stash is a "
            "mutating probe that removes worktree state to measure it. Use "
            "git status --porcelain / git diff instead.",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.UNCERTAIN,
            blast_radius=BlastRadius.ENTIRE_WORKTREE,
        )
    if action == "clear":
        return _deny(
            Effect.RECOVERY_OBJECT_DELETE,
            operation,
            "git stash clear destroys every stash entry — recovery state whose "
            f"value cannot be proven zero (I010). Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
        )
    if action == "drop":
        return _guard(
            Effect.RECOVERY_OBJECT_DELETE,
            operation,
            "dropping a stash entry removes recovery state; record the stash commit sha first",
            sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
            recoverability=Recoverability.BACKUP_REF,
            blast_radius=BlastRadius.SINGLE_KNOWN_PATH,
        )
    if action == "create":
        return _allow(
            Effect.INDEX_MUTATION,
            operation,
            "git stash create only writes an object; the worktree is untouched",
            sensitivity=Sensitivity.CLEAN_REPOSITORY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    finding = _overwrite_finding(ctx, operation, paths=None, blast=BlastRadius.ENTIRE_WORKTREE)
    if finding.outcome is Outcome.DENY_REQUIRES_HUMAN:
        return finding
    # An explicit stash push is itself a recovery-preserving move: the content
    # survives in the stash. Guard so the entry's sha is recorded.
    return _guard(
        finding.effect,
        operation,
        "explicit stash of known worktree state — record the stash reference "
        "so the content stays recoverable",
        sensitivity=finding.sensitivity,
        recoverability=Recoverability.BACKUP_REF,
        blast_radius=BlastRadius.ENTIRE_WORKTREE,
    )


def _classify_reset(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if _has_flag(args, "--hard"):
        return _overwrite_finding(
            ctx,
            "git reset --hard",
            paths=None,
            blast=BlastRadius.ENTIRE_WORKTREE,
        )
    if _has_flag(args, "--keep"):
        mode = "--keep"
    elif _has_flag(args, "--merge"):
        mode = "--merge"
    else:
        mode = "index"
    return _guard(
        Effect.INDEX_MUTATION,
        f"git reset {mode}",
        "reset without --hard moves refs and the index; worktree content is "
        "preserved by git itself",
        sensitivity=Sensitivity.AGENT_OWNED,
        recoverability=Recoverability.NO_STATE_AT_RISK,
        blast_radius=BlastRadius.LOCAL_BRANCH,
    )


def _classify_restore(ctx: GuardContext, operation: str, args: Sequence[str]) -> Finding:
    paths = _pathspec(args)
    if _has_flag(args, "--staged", "-S") and not _has_flag(args, "--worktree", "-W"):
        return _guard(
            Effect.INDEX_MUTATION,
            operation,
            "unstaging leaves worktree content intact",
            sensitivity=Sensitivity.AGENT_OWNED,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.BOUNDED_KNOWN_PATH_SET,
        )
    blast = (
        BlastRadius.SINGLE_KNOWN_PATH
        if len(paths) == 1
        else BlastRadius.BOUNDED_KNOWN_PATH_SET
        if paths
        else BlastRadius.ENTIRE_WORKTREE
    )
    return _overwrite_finding(ctx, operation, paths=paths or None, blast=blast)


def _classify_checkout(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if _has_flag(args, "-b", "-B", "--orphan"):
        return _allow(
            Effect.LOCAL_REF_MOVE,
            "git checkout -b",
            "creating a branch destroys nothing",
            sensitivity=Sensitivity.CLEAN_REPOSITORY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    if "--" in args:
        return _classify_restore(ctx, "git checkout -- <paths>", args)
    at_risk = _dirty_at_risk(ctx)
    if not at_risk:
        return _allow(
            Effect.LOCAL_REF_MOVE,
            "git checkout <branch>",
            "clean worktree — a branch switch overwrites nothing",
            sensitivity=Sensitivity.CLEAN_REPOSITORY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    return _guard(
        Effect.WORKTREE_OVERWRITE,
        "git checkout <branch>",
        "branch switch with a dirty worktree — git carries local changes over "
        "and can collide; capture a pre-operation patch first",
        sensitivity=Sensitivity.USER_UNCOMMITTED
        if _sensitive(at_risk)
        else Sensitivity.AGENT_OWNED,
        recoverability=_worktree_recoverability(ctx),
        blast_radius=BlastRadius.ENTIRE_WORKTREE,
        needs_recovery_capture=True,
    )


def _classify_clean(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if _has_flag(args, "-n", "--dry-run"):
        return _allow(Effect.OBSERVE_ONLY, "git clean -n", "dry run only")
    if not _has_flag(args, "-f", "--force"):
        return _allow(
            Effect.OBSERVE_ONLY,
            "git clean",
            "git refuses to clean without --force",
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    removes_ignored = _has_flag(args, "-x", "-X")
    flags = [arg for arg in args if arg.startswith("-")]
    paths = _pathspec(args)
    operation = "git clean " + " ".join(flags) if flags else "git clean -f"
    if ctx.disposable_repo:
        return _allow(
            Effect.UNTRACKED_DELETION,
            operation,
            "verified disposable checkout — the whole worktree is throwaway",
            sensitivity=Sensitivity.EPHEMERAL_SCRATCH,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.DISPOSABLE_DIRECTORY,
        )
    if removes_ignored:
        return _deny(
            Effect.UNTRACKED_DELETION,
            operation,
            "git clean -x/-X also deletes ignored files — local env, caches and "
            "machine-local state that no commit can restore. Allowed only in a "
            f"verified disposable checkout, or with {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.ENTIRE_WORKTREE,
        )
    # Mandatory observational preflight (contract clean.mandatory_preflight).
    targets = ctx.probe.clean_preview(flags, paths)
    if not targets:
        return _allow(
            Effect.UNTRACKED_DELETION,
            operation,
            "clean preflight lists no targets — nothing at risk",
            sensitivity=Sensitivity.CLEAN_REPOSITORY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    classified = [(target, ctx.ownership.classify(target)) for target in targets]
    unknown = [target for target, owner in classified if owner is Ownership.USER_OR_FOREIGN]
    if unknown:
        return _deny(
            Effect.UNTRACKED_DELETION,
            operation,
            "clean preflight (git clean -nd) lists untracked files that are not "
            f"provably disposable: {', '.join(unknown[:5])}. Untracked content has "
            "no git recovery path. Delete the named paths explicitly, or set "
            f"{HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.UNKNOWN,
        )
    return _allow(
        Effect.UNTRACKED_DELETION,
        operation,
        "clean preflight proves the target set safe — every target is "
        f"generated, cached, or ephemeral ({len(targets)} path(s))",
        sensitivity=Sensitivity.GENERATED,
        recoverability=Recoverability.DETERMINISTIC_REGENERATION,
        blast_radius=BlastRadius.BOUNDED_KNOWN_PATH_SET,
    )


def _classify_rebase(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if _has_flag(args, "--abort", "--quit"):
        return _guard(
            Effect.WORKTREE_OVERWRITE,
            "git rebase --abort",
            "aborting restores the pre-rebase head",
            sensitivity=Sensitivity.AGENT_OWNED,
            recoverability=Recoverability.BACKUP_REF,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    if _has_flag(args, "--continue", "--skip"):
        return _guard(
            Effect.HISTORY_REWRITE,
            "git rebase --continue",
            "continuing an in-progress rebase",
            sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
            recoverability=Recoverability.BACKUP_REF,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    branch = _current_branch_or_none(ctx)
    sensitivity = ctx.branch_sensitivity(branch)
    if sensitivity in (Sensitivity.SHARED_BRANCH, Sensitivity.PROTECTED_BRANCH):
        return _deny(
            Effect.HISTORY_REWRITE,
            "git rebase",
            f"rebasing {branch or '<unknown branch>'} rewrites history on a "
            f"{sensitivity.value}; dependent branches and open PRs break. "
            f"Set {HUMAN_AUTHORIZATION_ENV}=<reason> after confirming nothing depends on it.",
            sensitivity=sensitivity,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REMOTE_BRANCH,
        )
    at_risk = _dirty_at_risk(ctx)
    if at_risk and _sensitive(at_risk) and _worktree_recoverability(ctx) is Recoverability.NONE:
        return _deny(
            Effect.HISTORY_REWRITE,
            "git rebase",
            "rebase with unprotected uncommitted work in the tree and no provable recovery",
            sensitivity=Sensitivity.USER_UNCOMMITTED,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.ENTIRE_WORKTREE,
        )
    return _guard(
        Effect.HISTORY_REWRITE,
        "git rebase",
        "private branch rebase — record the pre-rebase sha as a backup ref",
        sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
        recoverability=Recoverability.BACKUP_REF,
        blast_radius=BlastRadius.LOCAL_BRANCH,
    )


def _classify_commit(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if not _has_flag(args, "--amend"):
        return _allow(
            Effect.INDEX_MUTATION,
            "git commit",
            "a new commit adds history; nothing is destroyed",
            sensitivity=Sensitivity.AGENT_OWNED,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    published = ctx.probe.head_is_published()
    branch = _current_branch_or_none(ctx)
    sensitivity = ctx.branch_sensitivity(branch)
    if published and sensitivity is not Sensitivity.PRIVATE_REMOTE_BRANCH:
        return _deny(
            Effect.HISTORY_REWRITE,
            "git commit --amend",
            f"HEAD is already published on a {sensitivity.value}; amending "
            "rewrites a commit others may have. Push a follow-up commit "
            f"instead, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=sensitivity,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REMOTE_BRANCH,
        )
    return _guard(
        Effect.HISTORY_REWRITE,
        "git commit --amend",
        "amending an unpublished HEAD on a private branch — record the original sha first",
        sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
        recoverability=Recoverability.BACKUP_REF,
        blast_radius=BlastRadius.LOCAL_BRANCH,
    )


def _classify_branch(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if not _has_flag(args, "-D", "-d", "--delete"):
        return _allow(
            Effect.LOCAL_REF_MOVE,
            "git branch",
            "branch creation/listing destroys nothing",
            sensitivity=Sensitivity.CLEAN_REPOSITORY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    targets = [arg for arg in _pathspec(args) if arg]
    target = targets[0] if targets else None
    sensitivity = ctx.branch_sensitivity(target)
    if sensitivity is Sensitivity.PROTECTED_BRANCH:
        return _deny(
            Effect.LOCAL_REF_DELETE,
            "git branch -D",
            f"{target} is a protected branch",
            sensitivity=sensitivity,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    if target is None:
        return _deny(
            Effect.LOCAL_REF_DELETE,
            "git branch -D",
            "branch delete with no resolvable target (I015)",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.UNCERTAIN,
            blast_radius=BlastRadius.UNKNOWN,
        )
    unique = ctx.probe.branch_has_unique_commits(target)
    if not unique:
        return _allow(
            Effect.LOCAL_REF_DELETE,
            "git branch -D",
            f"{target} holds no commits that are not reachable elsewhere — "
            "deleting the ref loses no history",
            sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    if Recoverability.BACKUP_REF in ctx.recovery_available:
        return _guard(
            Effect.LOCAL_REF_DELETE,
            "git branch -D",
            f"{target} has unique commits but a backup ref exists",
            sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
            recoverability=Recoverability.BACKUP_REF,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    return _deny(
        Effect.LOCAL_REF_DELETE,
        "git branch -D",
        f"{target} carries commits reachable from no other ref and no backup "
        "ref exists; the commits become unreachable. Create a backup ref "
        f"first, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
        sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
        recoverability=Recoverability.NONE,
        blast_radius=BlastRadius.LOCAL_BRANCH,
    )


def _classify_tag(ctx: GuardContext, args: Sequence[str]) -> Finding:
    if not _has_flag(args, "-d", "--delete", "-f", "--force"):
        return _allow(
            Effect.LOCAL_REF_MOVE,
            "git tag",
            "creating or listing tags destroys nothing",
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.NONE,
        )
    targets = _pathspec(args)
    if not targets:
        return _deny(
            Effect.LOCAL_REF_DELETE,
            "git tag -d",
            "tag delete/force with no resolvable target (I015)",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.UNCERTAIN,
            blast_radius=BlastRadius.UNKNOWN,
        )
    return _guard(
        Effect.LOCAL_REF_DELETE,
        "git tag -d/-f",
        f"record the tag's current sha before moving or deleting {targets[0]}",
        sensitivity=Sensitivity.PRIVATE_LOCAL_BRANCH,
        recoverability=Recoverability.BACKUP_REF,
        blast_radius=BlastRadius.LOCAL_BRANCH,
    )


@dataclass(frozen=True)
class _PushSpec:
    remote: str
    branch: str | None
    force: bool
    lease: bool
    delete: bool


def _parse_push(args: Sequence[str]) -> _PushSpec:
    force = False
    lease = False
    delete = False
    positional: list[str] = []
    for arg in args:
        base = arg.split("=", 1)[0]
        if base in {"--force-with-lease"}:
            lease = True
            continue
        if base in {"--force-if-includes"}:
            continue
        if base in {"--force", "-f", "--mirror"}:
            force = True
            continue
        if base in {"--delete", "-d"}:
            delete = True
            continue
        if arg.startswith("-"):
            continue
        positional.append(arg)
    remote = positional[0] if positional else "origin"
    refspec = positional[1] if len(positional) > 1 else None
    if refspec and refspec.startswith("+"):
        force = True
        refspec = refspec[1:]
    if refspec and refspec.startswith(":"):
        delete = True
        refspec = refspec[1:]
    branch = refspec.split(":")[-1] if refspec else None
    return _PushSpec(remote, branch, force, lease, delete)


def _classify_push(ctx: GuardContext, args: Sequence[str]) -> Finding:
    spec = _parse_push(args)
    branch = spec.branch or _current_branch_or_none(ctx)
    sensitivity = ctx.branch_sensitivity(branch)
    ref_id = f"{spec.remote}/{branch}" if branch else spec.remote
    if spec.delete:
        if sensitivity in (Sensitivity.PROTECTED_BRANCH, Sensitivity.SHARED_BRANCH):
            return _deny(
                Effect.REMOTE_REF_DELETE,
                "git push --delete",
                f"deleting {ref_id} removes a {sensitivity.value} others and "
                f"open PRs may depend on. Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
                sensitivity=sensitivity,
                recoverability=Recoverability.NONE,
                blast_radius=BlastRadius.REMOTE_BRANCH,
            )
        if branch is None:
            return _deny(
                Effect.REMOTE_REF_DELETE,
                "git push --delete",
                "remote branch delete with no precisely identified target (I015)",
                sensitivity=Sensitivity.UNKNOWN,
                recoverability=Recoverability.UNCERTAIN,
                blast_radius=BlastRadius.UNKNOWN,
            )
        return _guard(
            Effect.REMOTE_REF_DELETE,
            "git push --delete",
            f"deleting private remote branch {ref_id} — record its sha first",
            sensitivity=sensitivity,
            recoverability=Recoverability.BACKUP_REF,
            blast_radius=BlastRadius.REMOTE_BRANCH,
        )
    if spec.force and not spec.lease:
        if ref_id in ctx.disposable_remote_refs:
            return _allow(
                Effect.REMOTE_REF_REWRITE,
                "git push --force",
                f"{ref_id} is a verified disposable test ref",
                sensitivity=Sensitivity.EPHEMERAL_SCRATCH,
                recoverability=Recoverability.NO_STATE_AT_RISK,
                blast_radius=BlastRadius.REMOTE_BRANCH,
            )
        return _deny(
            Effect.REMOTE_REF_REWRITE,
            "git push --force",
            f"unleased force push to {ref_id} overwrites whatever the remote "
            "holds now, including commits this checkout has never seen. Use "
            f"--force-with-lease, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=sensitivity,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REMOTE_BRANCH,
        )
    if spec.lease:
        if sensitivity in (Sensitivity.PROTECTED_BRANCH, Sensitivity.SHARED_BRANCH):
            return _deny(
                Effect.REMOTE_REF_REWRITE,
                "git push --force-with-lease",
                f"{ref_id} is a {sensitivity.value}; a lease proves nobody "
                "pushed since your fetch, not that rewriting shared history is "
                f"safe. Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
                sensitivity=sensitivity,
                recoverability=Recoverability.NONE,
                blast_radius=BlastRadius.REMOTE_BRANCH,
            )
        if branch is None or not ctx.probe.remote_lease_known(spec.remote, branch):
            return _deny(
                Effect.REMOTE_REF_REWRITE,
                "git push --force-with-lease",
                f"the expected remote sha for {ref_id} is unknown, so the lease "
                "cannot be checked before the rewrite. Fetch the remote ref "
                f"first, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
                sensitivity=sensitivity,
                recoverability=Recoverability.UNCERTAIN,
                blast_radius=BlastRadius.REMOTE_BRANCH,
            )
        return _guard(
            Effect.REMOTE_REF_REWRITE,
            "git push --force-with-lease",
            f"private branch {ref_id} with a known expected remote sha — the "
            "lease is the recovery evidence",
            sensitivity=Sensitivity.PRIVATE_REMOTE_BRANCH,
            recoverability=Recoverability.EXPLICIT_REMOTE_LEASE,
            blast_radius=BlastRadius.REMOTE_BRANCH,
        )
    return _guard(
        Effect.REMOTE_REF_UPDATE,
        "git push",
        f"fast-forward publication to {ref_id}",
        sensitivity=sensitivity,
        recoverability=Recoverability.NO_STATE_AT_RISK,
        blast_radius=BlastRadius.REMOTE_BRANCH,
    )


def _classify_maintenance(ctx: GuardContext, sub: str, args: Sequence[str]) -> Finding:
    if sub == "gc":
        aggressive = any(
            arg.startswith("--prune=") and arg.split("=", 1)[1] not in {"", "never"} for arg in args
        ) or _has_flag(args, "--aggressive")
        if aggressive:
            return _deny(
                Effect.RECOVERY_OBJECT_DELETE,
                "git gc --prune=<now>",
                "pruning past the default retention destroys unreachable "
                "objects — precisely the objects a botched reset or rebase is "
                f"recovered from (I010). Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
                sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
                recoverability=Recoverability.NONE,
                blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
            )
        return _guard(
            Effect.RECOVERY_OBJECT_DELETE,
            "git gc",
            "default retention keeps recovery objects; repack only",
            sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
        )
    if sub == "repack":
        return _guard(
            Effect.RECOVERY_OBJECT_DELETE,
            "git repack",
            "repacking keeps reachable history; avoid -d with pruning",
            sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
        )
    label = "git prune" if sub == "prune" else "git reflog expire"
    return _deny(
        Effect.RECOVERY_OBJECT_DELETE,
        label,
        f"{label} destroys the repository's recovery surface (unreachable "
        "objects / reflog entries) while their recovery value is still "
        f"possible (I010). Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
        sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
        recoverability=Recoverability.NONE,
        blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
    )


def _classify_update_ref(ctx: GuardContext, args: Sequence[str]) -> Finding:
    targets = [arg for arg in args if not arg.startswith("-")]
    ref = targets[0] if targets else None
    harness_prefixes = ("refs/l9/", "refs/backup/", "refs/original/")
    harness_owned = ref is not None and ref.startswith(harness_prefixes)
    if harness_owned:
        return _allow(
            Effect.LOCAL_REF_MOVE,
            "git update-ref",
            f"{ref} is a harness-owned recovery/temporary ref",
            sensitivity=Sensitivity.AGENT_OWNED,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.LOCAL_BRANCH,
        )
    return _deny(
        Effect.LOCAL_REF_MOVE,
        "git update-ref",
        "git update-ref moves refs behind git's own safety checks — no reflog "
        "protection contract, no merge check. Use the porcelain command for "
        f"what you mean, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
        sensitivity=Sensitivity.UNKNOWN,
        recoverability=Recoverability.UNCERTAIN,
        blast_radius=BlastRadius.UNKNOWN,
    )


def _current_branch_or_none(ctx: GuardContext) -> str | None:
    try:
        return ctx.probe.current_branch()
    except ProbeError:
        return None


#: Mutating subcommands that git itself refuses rather than overwrites:
#: they abort on conflict instead of destroying local state.
_NON_DESTRUCTIVE_MUTATIONS = frozenset(
    {
        "add",
        "merge",
        "pull",
        "cherry-pick",
        "revert",
        "apply",
        "am",
        "mv",
        "init",
        "clone",
        "switch",
        "worktree",
        "notes",
        "bisect",
        "submodule",
        "sparse-checkout",
        "update-index",
        "write-tree",
        "commit-tree",
        "hash-object",
        "gpg-sign",
        "maintenance",
    }
)


def _classify_git(ctx: GuardContext, words: Sequence[str]) -> Finding:
    sub, args = _git_subcommand(words)
    if sub is None:
        return _guard(
            Effect.INDEX_MUTATION,
            "git",
            "unparsed git invocation — guarded, never blanket-allowed (I015)",
        )
    if _is_read_only_git(words):
        return _allow(Effect.OBSERVE_ONLY, f"git {sub}", "read-only observation (I003)")
    if sub == "stash":
        return _classify_stash(ctx, args)
    if sub == "reset":
        return _classify_reset(ctx, args)
    if sub == "restore":
        return _classify_restore(ctx, "git restore", args)
    if sub == "checkout":
        return _classify_checkout(ctx, args)
    if sub == "clean":
        return _classify_clean(ctx, args)
    if sub == "rebase":
        return _classify_rebase(ctx, args)
    if sub == "commit":
        return _classify_commit(ctx, args)
    if sub == "branch":
        return _classify_branch(ctx, args)
    if sub == "tag":
        return _classify_tag(ctx, args)
    if sub == "push":
        return _classify_push(ctx, args)
    if sub in {"gc", "prune", "repack"}:
        return _classify_maintenance(ctx, sub, args)
    if sub == "reflog":
        if _has_flag(args, "--expire") or (args and args[0] in {"expire", "delete"}):
            return _classify_maintenance(ctx, "reflog", args)
        return _allow(Effect.OBSERVE_ONLY, "git reflog", "reflog inspection is read-only")
    if sub == "update-ref":
        return _classify_update_ref(ctx, args)
    if sub == "filter-branch":
        return _deny(
            Effect.HISTORY_REWRITE,
            "git filter-branch",
            "wholesale history rewrite of every reachable commit. Set "
            f"{HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
        )
    if sub in _NON_DESTRUCTIVE_MUTATIONS:
        return _allow(
            Effect.INDEX_MUTATION,
            f"git {sub}",
            f"git {sub} aborts rather than overwriting local state",
            sensitivity=Sensitivity.AGENT_OWNED,
            recoverability=Recoverability.NO_STATE_AT_RISK,
            blast_radius=BlastRadius.BOUNDED_KNOWN_PATH_SET,
        )
    return _guard(
        Effect.INDEX_MUTATION,
        f"git {sub}",
        f"git {sub} is not a classified destructive form; guarded by default",
    )


# ---------------------------------------------------------------------------
# gh (contract ``gh_policy``)
# ---------------------------------------------------------------------------

_GH_READ_ONLY: dict[str, frozenset[str]] = {
    "pr": frozenset({"list", "view", "checks", "diff", "status"}),
    "run": frozenset({"list", "view", "watch", "download"}),
    "repo": frozenset({"view", "list"}),
    "issue": frozenset({"list", "view", "status"}),
    "release": frozenset({"list", "view", "download"}),
    "workflow": frozenset({"list", "view"}),
    "api": frozenset(),
    "search": frozenset(),
    "auth": frozenset({"status"}),
    "browse": frozenset(),
    "label": frozenset({"list"}),
    "cache": frozenset({"list"}),
    "gist": frozenset({"list", "view"}),
}

_GH_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _classify_gh(ctx: GuardContext, words: Sequence[str]) -> Finding:
    args = [word for word in words[1:] if word]
    positional = [arg for arg in args if not arg.startswith("-")]
    group = positional[0] if positional else None
    action = positional[1] if len(positional) > 1 else None
    if group is None:
        return _allow(Effect.OBSERVE_ONLY, "gh", "no subcommand")
    if group == "api":
        method = _gh_api_method(args)
        if method == "DELETE":
            return _deny(
                Effect.REMOTE_REF_DELETE,
                "gh api DELETE",
                "an authenticated DELETE against the GitHub API is an "
                "irreversible remote deletion with no local recovery. Set "
                f"{HUMAN_AUTHORIZATION_ENV}=<reason>.",
                sensitivity=Sensitivity.SHARED_BRANCH,
                recoverability=Recoverability.NONE,
                blast_radius=BlastRadius.UNKNOWN,
            )
        if "graphql" in positional and _gh_graphql_is_mutation(args):
            return _deny(
                Effect.REMOTE_REF_UPDATE,
                "gh api graphql mutation",
                "a GraphQL mutation's remote effect cannot be classified from "
                f"the command text. Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
                sensitivity=Sensitivity.UNKNOWN,
                recoverability=Recoverability.UNCERTAIN,
                blast_radius=BlastRadius.UNKNOWN,
            )
        if method in _GH_WRITE_METHODS:
            return _guard(
                Effect.REMOTE_REF_UPDATE,
                f"gh api {method}",
                "authenticated remote write",
                sensitivity=Sensitivity.SHARED_BRANCH,
                recoverability=Recoverability.UNCERTAIN,
                blast_radius=BlastRadius.UNKNOWN,
            )
        return _allow(Effect.OBSERVE_ONLY, "gh api GET", "read-only API request")
    if group == "pr" and action == "merge" and _has_flag(args, "--admin"):
        return _deny(
            Effect.REMOTE_REF_UPDATE,
            "gh pr merge --admin",
            "--admin bypasses branch protection and required checks. Set "
            f"{HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.PROTECTED_BRANCH,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REMOTE_BRANCH,
        )
    if group in {"repo", "release", "cache", "secret", "gist"} and action == "delete":
        return _deny(
            Effect.REMOTE_REF_DELETE,
            f"gh {group} delete",
            f"deleting a remote {group} is irreversible from this checkout. "
            f"Set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.SHARED_BRANCH,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.UNKNOWN,
        )
    read_only = _GH_READ_ONLY.get(group)
    if read_only is not None and action in read_only:
        return _allow(Effect.OBSERVE_ONLY, f"gh {group} {action}", "read-only gh query")
    if group in {"search", "browse", "status", "version"}:
        return _allow(Effect.OBSERVE_ONLY, f"gh {group}", "read-only gh query")
    return _guard(
        Effect.REMOTE_REF_UPDATE,
        f"gh {group} {action or ''}".strip(),
        "gh mutation — classified by remote effect, not by the executable",
        sensitivity=Sensitivity.SHARED_BRANCH,
        recoverability=Recoverability.UNCERTAIN,
        blast_radius=BlastRadius.UNKNOWN,
    )


def _gh_api_method(args: Sequence[str]) -> str:
    for index, arg in enumerate(args):
        base, _, inline = arg.partition("=")
        if base in {"-X", "--method"}:
            if inline:
                return inline.upper()
            if index + 1 < len(args):
                return args[index + 1].upper()
    body_flags = {"-f", "--field", "-F", "--raw-field", "--input"}
    if any(arg.split("=", 1)[0] in body_flags for arg in args):
        return "POST"
    return "GET"


def _gh_graphql_is_mutation(args: Sequence[str]) -> bool:
    return any("mutation" in arg.lower() for arg in args)


# ---------------------------------------------------------------------------
# Filesystem deletes (contract ``filesystem_guardrails``)
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


def _resolve_token(token: str, env: Mapping[str, str]) -> str | None:
    """Expand ``$VAR`` / ``${VAR}`` from ``env``; None when any is unresolved.

    Unresolved is never treated as harmless: an empty expansion is exactly how
    ``rm -rf "$SP/base-export"`` becomes ``rm -rf /base-export``.
    """
    if "`" in token or "$(" in token:
        return None
    missing = False

    def _sub(match: re.Match[str]) -> str:
        nonlocal missing
        value = env.get(match.group(1), "")
        if not value.strip():
            missing = True
        return value

    resolved = _VAR_RE.sub(_sub, token)
    if missing or not resolved.strip():
        return None
    return resolved


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_mountpoint(path: Path) -> bool:
    try:
        return path.is_mount()
    except OSError:
        return True


def _classify_rm(ctx: GuardContext, words: Sequence[str]) -> Finding:
    args = list(words[1:])
    recursive = _has_flag(args, "-r", "-R", "--recursive")
    force = _has_flag(args, "-f", "--force")
    if not (recursive or force):
        return _guard(
            Effect.FILESYSTEM_DELETE,
            "rm",
            "non-recursive delete of named files",
            blast_radius=BlastRadius.BOUNDED_KNOWN_PATH_SET,
        )
    targets = [arg for arg in args if not arg.startswith("-")]
    if not targets:
        return _deny(
            Effect.FILESYSTEM_DELETE,
            "rm -rf",
            "recursive delete with no resolvable target (I015)",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.UNCERTAIN,
            blast_radius=BlastRadius.UNKNOWN,
        )
    worst = _allow(
        Effect.FILESYSTEM_DELETE,
        "rm -rf",
        "verified ephemeral cleanup (I014)",
        sensitivity=Sensitivity.EPHEMERAL_SCRATCH,
        recoverability=Recoverability.NO_STATE_AT_RISK,
        blast_radius=BlastRadius.DISPOSABLE_DIRECTORY,
    )
    for token in targets:
        finding = _classify_rm_target(ctx, token)
        if finding.outcome.rank > worst.outcome.rank:
            worst = finding
    return worst


def _classify_rm_target(ctx: GuardContext, token: str) -> Finding:
    raw = _resolve_token(token, ctx.env)
    if raw is None:
        return _deny(
            Effect.FILESYSTEM_DELETE,
            "rm -rf",
            f"target {token!r} contains an unresolved or empty expansion — an "
            "empty variable turns a scoped delete into a delete of its parent. "
            f"Resolve it, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.UNKNOWN,
        )
    if any(ch in raw for ch in "*?[") and raw.count("/") <= 1:
        return _deny(
            Effect.FILESYSTEM_DELETE,
            "rm -rf",
            f"wildcard target {raw!r} has unbounded scope",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.UNKNOWN,
        )
    try:
        path = Path(os.path.realpath(os.path.expanduser(raw)))
    except OSError:
        path = Path(raw)
    home = Path(os.path.expanduser("~")).resolve()
    if str(path) in _NEVER_DELETE_NAMES or path == home or path.parent == path:
        return _deny(
            Effect.FILESYSTEM_DELETE,
            "rm -rf",
            f"{path} is a filesystem or home root",
            sensitivity=Sensitivity.UNKNOWN,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.UNKNOWN,
        )
    if path.name == ".git" or (path / ".git").exists():
        return _deny(
            Effect.FILESYSTEM_DELETE,
            "rm -rf",
            f"{path} is a git repository or its .git directory",
            sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
            recoverability=Recoverability.NONE,
            blast_radius=BlastRadius.REPOSITORY_OBJECT_DATABASE,
        )
    if ctx.root is not None:
        try:
            root = ctx.root.resolve()
        except OSError:
            root = ctx.root
        if path == root:
            return _deny(
                Effect.FILESYSTEM_DELETE,
                "rm -rf",
                f"{path} is the repository root",
                sensitivity=Sensitivity.REPOSITORY_RECOVERY_STATE,
                recoverability=Recoverability.NONE,
                blast_radius=BlastRadius.ENTIRE_WORKTREE,
            )
    for scratch in ctx.scratch_roots:
        if path == scratch:
            break
        if _inside(path, scratch):
            if _is_mountpoint(path):
                break
            return _allow(
                Effect.FILESYSTEM_DELETE,
                "rm -rf",
                f"{path} is inside the verified session scratch root {scratch} "
                "— verified ephemeral cleanup is safe mutation (I014)",
                sensitivity=Sensitivity.EPHEMERAL_SCRATCH,
                recoverability=Recoverability.NO_STATE_AT_RISK,
                blast_radius=BlastRadius.DISPOSABLE_DIRECTORY,
            )
    return _guard(
        Effect.FILESYSTEM_DELETE,
        "rm -rf",
        f"{path} is a resolved path outside any verified scratch root — "
        "confirm it holds no unique state before deleting",
        sensitivity=Sensitivity.UNKNOWN,
        recoverability=Recoverability.UNCERTAIN,
        blast_radius=BlastRadius.UNKNOWN,
    )


# ---------------------------------------------------------------------------
# Segment + compound classification (contract ``compound_commands``)
# ---------------------------------------------------------------------------

#: Command heads this plane governs. Everything else is out of scope here and
#: continues through the rest of the governance machinery unchanged.
_GOVERNED_HEADS = frozenset({"git", "gh", "rm"})

#: Compound shapes that reveal a mutating command being used as a probe.
_PROBE_RESTORE_RE = re.compile(r"\bgit\s+stash\s+(?:pop|apply)\b", re.I)


def _segments(command: str) -> list[str]:
    """Every executable segment, wrappers descended, heredoc bodies dropped."""
    found: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        found.append(segment)
        found.extend(wrapper_subcommands(segment))
    return found


def _infer_purpose(command: str, segments: Sequence[str], ctx: GuardContext) -> Purpose:
    """Detect the ``stash … <read-only> … stash pop`` safety-probe shape.

    An explicitly declared purpose always wins; this only catches the shape the
    contract names as prohibited when nobody declared anything.
    """
    declared = ctx.env.get("L9_GIT_OP_PURPOSE", "").strip().lower()
    if declared in {"probe", "diagnostic", "diagnostic_probe"}:
        return Purpose.DIAGNOSTIC_PROBE
    if declared in {"task", "task_operation", "explicit_task_operation"}:
        return Purpose.TASK_OPERATION
    if ctx.purpose is Purpose.DIAGNOSTIC_PROBE:
        return Purpose.DIAGNOSTIC_PROBE
    if not _PROBE_RESTORE_RE.search(command):
        return ctx.purpose
    # stash + restore in one command, with nothing but observation between them.
    others = [
        segment for segment in segments if segment_head(segment) == "git" and "stash" not in segment
    ]
    if others and all(_is_read_only_git(segment_words(segment)) for segment in others):
        return Purpose.DIAGNOSTIC_PROBE
    return ctx.purpose


def _strip_env_prefix(words: Sequence[str]) -> list[str]:
    """Drop leading ``VAR=value`` assignments so the executable leads."""
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    return list(words[index:])


def classify_segment(ctx: GuardContext, segment: str) -> Finding | None:
    """Classify one segment, or None when this plane does not govern it."""
    head = segment_head(segment)
    if head is None:
        return None
    name = PurePosixPath(head).name
    if name not in _GOVERNED_HEADS:
        return None
    words = _strip_env_prefix(segment_words(segment))
    if not words:
        return None
    if name == "git":
        return _classify_git(ctx, words)
    if name == "gh":
        return _classify_gh(ctx, words)
    return _classify_rm(ctx, words)


def evaluate_command(command: str, ctx: GuardContext | None = None) -> Decision:
    """Effective outcome for a whole command (contract ``algorithm``).

    Never raises. A fault while classifying a *potentially destructive* effect
    becomes DENY_REQUIRES_HUMAN (I017); a command that is provably read-only
    stays ALLOW even with every governance dependency down (I016).
    """
    ctx = ctx or GuardContext()
    if not command or not command.strip():
        return Decision(Outcome.ALLOW, (), "empty command")
    try:
        segments = _segments(command)
    except Exception as exc:  # noqa: BLE001 - parser fault must not fail open
        if _looks_provably_read_only(command):
            return Decision(Outcome.ALLOW, (), "provably read-only despite parser fault")
        return Decision(
            Outcome.DENY_REQUIRES_HUMAN,
            (),
            f"command could not be parsed ({type(exc).__name__}); a sensitive "
            "mutation cannot be ruled out (I015)",
        )
    ctx = replace(ctx, purpose=_infer_purpose(command, segments, ctx))
    findings: list[Finding] = []
    for segment in segments:
        try:
            finding = classify_segment(ctx, segment)
        except ProbeError as exc:
            finding = _fault_finding(segment, str(exc))
        except Exception as exc:  # noqa: BLE001 - classifier fault: fail closed
            finding = _fault_finding(segment, f"{type(exc).__name__}: {exc}")
        if finding is not None:
            findings.append(finding)
    if not findings:
        return Decision(Outcome.ALLOW, (), "no governed effect")
    if ctx.purpose is Purpose.DIAGNOSTIC_PROBE:
        findings = [_probe_escalated(item) for item in findings]
    effective = max(findings, key=lambda item: item.outcome.rank)
    if effective.outcome is Outcome.DENY_REQUIRES_HUMAN and human_authorized(ctx.env):
        return Decision(
            Outcome.ALLOW,
            tuple(findings),
            f"human authorization present ({HUMAN_AUTHORIZATION_ENV})",
        )
    return Decision(effective.outcome, tuple(findings), effective.reason)


def _probe_escalated(finding: Finding) -> Finding:
    """Contract ``diagnostic_policy``: probes are observational only (I011).

    A mutating command run to *measure* state is denied even when the same
    command would be allowed as an explicit task action — measuring must never
    change what is being measured.
    """
    if finding.effect is Effect.OBSERVE_ONLY:
        return finding
    if finding.outcome is Outcome.DENY_REQUIRES_HUMAN:
        return finding
    return _deny(
        finding.effect,
        finding.operation,
        f"{finding.operation}: diagnostic probes must be observational (I011) — "
        "this command mutates state to measure it. Use git status --porcelain, "
        "git diff, or git clean -nd instead.",
        sensitivity=finding.sensitivity,
        recoverability=finding.recoverability,
        blast_radius=finding.blast_radius,
    )


def _fault_finding(segment: str, detail: str) -> Finding:
    """Fail-closed finding for a segment whose evaluation faulted."""
    words = segment_words(segment)
    if _is_read_only_git(words):
        return _allow(
            Effect.OBSERVE_ONLY,
            "git",
            "read-only observation allowed despite evaluator fault (I016)",
        )
    return _deny(
        Effect.OBSERVE_ONLY if not words else Effect.WORKTREE_OVERWRITE,
        words[0] if words else "?",
        f"policy evaluation failed ({detail}); a sensitive mutation cannot be "
        f"ruled out, so this fails closed (I017). Set {HUMAN_AUTHORIZATION_ENV}=<reason> "
        "if a human has confirmed the effect.",
        sensitivity=Sensitivity.UNKNOWN,
        recoverability=Recoverability.UNCERTAIN,
        blast_radius=BlastRadius.UNKNOWN,
    )


# ---------------------------------------------------------------------------
# Guard execution (contract ``guard_actions.recovery_capture``)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str
    receipt: Path | None = None


def _recovery_dir(ctx: GuardContext) -> Path:
    configured = ctx.env.get("L9_GUARDRAIL_RECOVERY_DIR", "").strip()
    if configured:
        return Path(configured)
    home = Path(os.path.expanduser("~"))
    return home / ".cursor" / "l9-git-guardrails"


def capture_recovery(ctx: GuardContext, label: str) -> Path | None:
    """Write a pre-operation binary patch + HEAD receipt outside the repo.

    Observational by construction: it runs ``git diff --binary`` and
    ``git rev-parse HEAD`` and writes to a machine-local directory. It never
    stashes, resets, or stages — a guardrail must not mutate the state it is
    protecting (I012), and ``git stash`` as a safety probe is prohibited.
    """
    if ctx.root is None:
        return None
    target = _recovery_dir(ctx)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    stamp = f"{os.getpid()}-{abs(hash(label)) % 10**8}"
    patch = target / f"{stamp}.patch"
    try:
        head = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(ctx.root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        diff = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(ctx.root), "diff", "--binary", "HEAD"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if diff.returncode != 0:
        return None
    body = (
        f"# l9-git-guardrails pre-operation recovery\n"
        f"# contract: {CONTRACT_ID} v{CONTRACT_VERSION}\n"
        f"# operation: {label}\n"
        f"# repo: {ctx.root}\n"
        f"# head: {head.stdout.strip()}\n"
        f"{diff.stdout}"
    )
    try:
        patch.write_text(body, encoding="utf-8")
    except OSError:
        return None
    # Verify (contract: recovery must be verified, not assumed).
    try:
        if not patch.is_file() or patch.stat().st_size == 0:
            return None
    except OSError:
        return None
    return patch


def run_guards(decision: Decision, ctx: GuardContext) -> GuardResult:
    """Apply GUARD_THEN_ALLOW: observe, capture recovery if needed, then allow."""
    if decision.outcome is Outcome.ALLOW:
        return GuardResult(True, decision.reason)
    if decision.outcome is Outcome.DENY_REQUIRES_HUMAN:
        return GuardResult(False, decision.reason)
    if not decision.needs_recovery_capture:
        return GuardResult(True, f"guards proved the effect safe: {decision.reason}")
    label = decision.deciding.operation if decision.deciding else "git"
    receipt = capture_recovery(ctx, label)
    if receipt is None:
        return GuardResult(
            False,
            f"{decision.reason}\nRecovery capture failed, so the mutation is "
            "not provably recoverable and fails closed. Commit or copy the "
            f"work first, or set {HUMAN_AUTHORIZATION_ENV}=<reason>.",
        )
    return GuardResult(True, f"pre-operation recovery captured at {receipt}", receipt)


# ---------------------------------------------------------------------------
# Gate entry point
# ---------------------------------------------------------------------------


def command_requires_human(command: str, *, root: Path | None = None) -> str | None:
    """Deny reason for a command, or None when it may run.

    This is the execution gates' entry point. GUARD_THEN_ALLOW is resolved
    here: observational guards run, recovery is captured when the effect needs
    it, and only an unprovable sensitive mutation is denied.
    """
    try:
        ctx = live_context(root)
        decision = evaluate_command(command, ctx)
        result = run_guards(decision, ctx)
    except Exception as exc:  # noqa: BLE001 - gate boundary: never fail open
        if _looks_provably_read_only(command):
            return None
        return (
            f"git guardrails: evaluation faulted ({type(exc).__name__}: {exc}); "
            "a sensitive mutation cannot be ruled out, so it fails closed (I017)."
        )
    if result.allowed:
        if result.receipt is not None:
            print(f"git guardrails: {result.reason}", file=sys.stderr)
        return None
    return f"git guardrails ({CONTRACT_ID}): {result.reason}"


__all__ = [
    "CONTRACT_ID",
    "CONTRACT_VERSION",
    "HUMAN_AUTHORIZATION_ENV",
    "BlastRadius",
    "Decision",
    "DirtyPath",
    "Effect",
    "Finding",
    "GuardContext",
    "GuardResult",
    "LiveProbe",
    "Outcome",
    "Ownership",
    "OwnershipOracle",
    "Probe",
    "ProbeError",
    "Purpose",
    "Recoverability",
    "Sensitivity",
    "StaticProbe",
    "capture_recovery",
    "classify_segment",
    "command_requires_human",
    "evaluate_command",
    "human_authorized",
    "is_generated_path",
    "is_regenerable_path",
    "live_context",
    "run_guards",
]
