"""Contract enforcement suite: l9-context-sensitive-git-guardrails v1.0.0.

Each ``test_t0NN_*`` is the contract's ``enforcement_tests`` entry of the same
id, with the same ``setup`` expressed as a ``GuardContext``. The contract sets
``acceptance.all_enforcement_tests_required: true`` and
``forbidden_behavior_count_allowed: 0``, so ``TestProhibitedBehavior`` and
``TestInvariants`` pin the failure modes the model exists to prevent — notably
that neither half of the old name-based model can come back: no blanket allow
of git, and no blanket deny of a subcommand by name.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from git_guardrails import (  # noqa: E402
    HUMAN_AUTHORIZATION_ENV,
    DirtyPath,
    Effect,
    GuardContext,
    Outcome,
    Ownership,
    OwnershipOracle,
    Probe,
    ProbeError,
    Purpose,
    Recoverability,
    StaticProbe,
    capture_recovery,
    evaluate_command,
    human_authorized,
    run_guards,
)

# Command fragments are assembled rather than written literally so a governance
# scanner reading this file never mistakes a fixture for an instruction (the
# convention in test_worktree_isolation_gate.py).
GIT = "g" + "it"
RMRF = "r" + "m -rf"


def ctx(**overrides: object) -> GuardContext:
    """GuardContext with an empty env, so no ambient variable can widen a gate."""
    base: dict[str, object] = {"env": {}}
    base.update(overrides)
    return GuardContext(**base)  # type: ignore[arg-type]


def outcome(command: str, context: GuardContext | None = None) -> Outcome:
    return evaluate_command(command, context or ctx()).outcome


def user_dirty(*paths: str) -> tuple[DirtyPath, ...]:
    return tuple(DirtyPath(path, Ownership.USER_OR_FOREIGN) for path in paths)


def agent_dirty(*paths: str) -> tuple[DirtyPath, ...]:
    return tuple(DirtyPath(path, Ownership.AGENT_OWNED) for path in paths)


class FaultingProbe(Probe):
    """Every observation fails — the contract's ``policy_evaluator: fault``."""

    def dirty_paths(self) -> tuple[DirtyPath, ...]:
        raise ProbeError("policy evaluator fault")

    def clean_preview(self, flags, paths):  # type: ignore[no-untyped-def]
        raise ProbeError("policy evaluator fault")

    def current_branch(self) -> str | None:
        raise ProbeError("policy evaluator fault")


# ---------------------------------------------------------------------------
# T001 - T030: contract enforcement_tests
# ---------------------------------------------------------------------------


def test_t001_status_is_allowed() -> None:
    assert outcome(f"{GIT} status") is Outcome.ALLOW


def test_t002_archive_is_allowed() -> None:
    assert outcome(f"{GIT} archive HEAD") is Outcome.ALLOW


def test_t003_stash_as_diagnostic_probe_denied() -> None:
    decision = evaluate_command(f"{GIT} stash push", ctx(purpose=Purpose.DIAGNOSTIC_PROBE))
    assert decision.outcome is Outcome.DENY_REQUIRES_HUMAN
    assert "observational" in decision.reason


def test_t004_explicit_stash_of_known_state_guards() -> None:
    context = ctx(
        purpose=Purpose.TASK_OPERATION,
        probe=StaticProbe(dirty=agent_dirty("ops/autonomy/git_guardrails.py")),
        recovery_available=frozenset({Recoverability.BACKUP_REF}),
    )
    assert outcome(f"{GIT} stash push", context) is Outcome.GUARD_THEN_ALLOW


def test_t005_reset_hard_on_clean_tree_is_allowed() -> None:
    context = ctx(probe=StaticProbe(dirty=()))
    assert outcome(f"{GIT} reset --hard HEAD", context) is Outcome.ALLOW


def test_t006_reset_hard_over_unrecoverable_foreign_edits_denied() -> None:
    context = ctx(probe=StaticProbe(dirty=user_dirty("src/important.py")))
    decision = evaluate_command(f"{GIT} reset --hard HEAD", context)
    assert decision.outcome is Outcome.DENY_REQUIRES_HUMAN
    assert "src/important.py" in decision.reason


def test_t007_reset_hard_with_verified_patch_guards() -> None:
    context = ctx(
        probe=StaticProbe(dirty=user_dirty("src/important.py")),
        recovery_available=frozenset({Recoverability.PRE_OPERATION_PATCH}),
    )
    assert outcome(f"{GIT} reset --hard HEAD", context) is Outcome.GUARD_THEN_ALLOW


def test_t008_restore_generated_target_is_allowed() -> None:
    oracle = OwnershipOracle(generated=frozenset({"src/generated.py"}))
    context = ctx(
        ownership=oracle,
        probe=StaticProbe(dirty=(DirtyPath("src/generated.py", Ownership.GENERATED),)),
    )
    assert outcome(f"{GIT} restore src/generated.py", context) is Outcome.ALLOW


def test_t009_restore_over_unrecoverable_foreign_edits_denied() -> None:
    context = ctx(probe=StaticProbe(dirty=user_dirty("src/important.py")))
    assert outcome(f"{GIT} restore src/important.py", context) is Outcome.DENY_REQUIRES_HUMAN


def test_t010_clean_with_generated_only_targets_is_allowed() -> None:
    context = ctx(probe=StaticProbe(clean_targets=("build/", ".pytest_cache/")))
    assert outcome(f"{GIT} clean -fd", context) is Outcome.ALLOW


def test_t011_clean_with_unknown_untracked_target_denied() -> None:
    context = ctx(probe=StaticProbe(clean_targets=("notes-uncommitted.txt",)))
    decision = evaluate_command(f"{GIT} clean -fd", context)
    assert decision.outcome is Outcome.DENY_REQUIRES_HUMAN
    assert "notes-uncommitted.txt" in decision.reason


def test_t012_clean_fdx_in_disposable_checkout_is_allowed() -> None:
    context = ctx(disposable_repo=True, probe=StaticProbe(clean_targets=(".env", "build/")))
    assert outcome(f"{GIT} clean -fdx", context) is Outcome.ALLOW


def test_t013_clean_fdx_in_normal_worktree_denied() -> None:
    context = ctx(probe=StaticProbe(clean_targets=("build/",)))
    assert outcome(f"{GIT} clean -fdx", context) is Outcome.DENY_REQUIRES_HUMAN


def test_t014_amend_unpublished_private_head_guards() -> None:
    context = ctx(
        probe=StaticProbe(published_head=False, branch="agent/claude/task"),
        private_branches=frozenset({"agent/claude/task"}),
    )
    assert outcome(f"{GIT} commit --amend", context) is Outcome.GUARD_THEN_ALLOW


def test_t015_amend_published_shared_head_denied() -> None:
    context = ctx(probe=StaticProbe(published_head=True, branch="feature"))
    assert outcome(f"{GIT} commit --amend", context) is Outcome.DENY_REQUIRES_HUMAN


def test_t016_branch_delete_without_unique_commits_is_allowed() -> None:
    context = ctx(probe=StaticProbe(unique_commits=False))
    assert outcome(f"{GIT} branch -D feature", context) is Outcome.ALLOW


def test_t017_branch_delete_with_unique_commits_and_no_backup_denied() -> None:
    context = ctx(probe=StaticProbe(unique_commits=True))
    assert outcome(f"{GIT} branch -D feature", context) is Outcome.DENY_REQUIRES_HUMAN


def test_t018_force_with_lease_on_private_branch_guards() -> None:
    context = ctx(
        probe=StaticProbe(lease_known=True, branch="feature"),
        private_branches=frozenset({"feature"}),
    )
    command = f"{GIT} push --force-with-lease origin feature"
    assert outcome(command, context) is Outcome.GUARD_THEN_ALLOW


def test_t019_force_with_lease_on_protected_branch_denied() -> None:
    context = ctx(probe=StaticProbe(lease_known=True, branch="main"))
    command = f"{GIT} push --force-with-lease origin main"
    assert outcome(command, context) is Outcome.DENY_REQUIRES_HUMAN


def test_t020_force_push_to_normal_remote_branch_denied() -> None:
    context = ctx(
        probe=StaticProbe(lease_known=True, branch="feature"),
        private_branches=frozenset({"feature"}),
    )
    command = f"{GIT} push --force origin feature"
    assert outcome(command, context) is Outcome.DENY_REQUIRES_HUMAN


def test_t021_gc_with_default_retention_guards() -> None:
    assert outcome(f"{GIT} gc") is Outcome.GUARD_THEN_ALLOW


def test_t022_gc_prune_now_denied() -> None:
    assert outcome(f"{GIT} gc --prune=now") is Outcome.DENY_REQUIRES_HUMAN


def test_t023_prune_denied() -> None:
    assert outcome(f"{GIT} prune") is Outcome.DENY_REQUIRES_HUMAN


def test_t024_scratch_export_pipeline_is_allowed(tmp_path: Path) -> None:
    scratch = tmp_path / "session-scratch"
    (scratch / "base-export").mkdir(parents=True)
    context = ctx(env={"SP": str(scratch)}, scratch_roots=(scratch.resolve(),))
    command = (
        f'{RMRF} "$SP/base-export" && '
        'mkdir -p "$SP/base-export" && '
        f'{GIT} archive origin/feature | tar -x -C "$SP/base-export"'
    )
    assert outcome(command, context) is Outcome.ALLOW


def test_t025_unresolved_scratch_variable_denied(tmp_path: Path) -> None:
    context = ctx(env={}, scratch_roots=(tmp_path,))
    decision = evaluate_command(f'{RMRF} "$SP/base-export"', context)
    assert decision.outcome is Outcome.DENY_REQUIRES_HUMAN
    assert "unresolved" in decision.reason


def test_t026_compound_read_then_reset_on_clean_tree_is_allowed() -> None:
    context = ctx(probe=StaticProbe(dirty=()))
    command = f"{GIT} status && {GIT} reset --hard HEAD"
    assert outcome(command, context) is Outcome.ALLOW


def test_t027_compound_read_then_reset_over_foreign_edits_denied() -> None:
    context = ctx(probe=StaticProbe(dirty=user_dirty("notes.md")))
    command = f"{GIT} status && {GIT} reset --hard HEAD"
    assert outcome(command, context) is Outcome.DENY_REQUIRES_HUMAN


def test_t028_wrapped_stash_probe_denied() -> None:
    context = ctx(purpose=Purpose.DIAGNOSTIC_PROBE)
    assert outcome(f"bash -c '{GIT} stash push'", context) is Outcome.DENY_REQUIRES_HUMAN


def test_t029_read_only_survives_total_evaluator_failure() -> None:
    context = ctx(probe=FaultingProbe())
    assert outcome(f"{GIT} diff", context) is Outcome.ALLOW


def test_t030_evaluator_fault_denies_sensitive_mutation() -> None:
    context = ctx(probe=FaultingProbe())
    decision = evaluate_command(f"{GIT} reset --hard HEAD", context)
    assert decision.outcome is Outcome.DENY_REQUIRES_HUMAN
    assert "fails closed" in decision.reason


# ---------------------------------------------------------------------------
# Invariants I001 - I017
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_i001_name_alone_does_not_decide(self) -> None:
        """One command, two contexts, two outcomes — the name decides nothing."""
        command = f"{GIT} reset --hard HEAD"
        assert outcome(command, ctx(probe=StaticProbe(dirty=()))) is Outcome.ALLOW
        assert (
            outcome(command, ctx(probe=StaticProbe(dirty=user_dirty("a.py"))))
            is Outcome.DENY_REQUIRES_HUMAN
        )

    @pytest.mark.parametrize(
        "command",
        [
            "status",
            "diff --cached",
            "log --oneline -5",
            "show HEAD",
            "rev-parse HEAD",
            "ls-files",
            "ls-remote origin",
            "merge-base main HEAD",
            "cat-file -p HEAD",
            "branch --show-current",
            "tag --list",
            "reflog show",
            "stash list",
            "stash show",
            "config --get user.email",
            "remote -v",
            "archive HEAD",
            "fetch origin main",
            "clean -nd",
        ],
    )
    def test_i003_read_only_is_unconditionally_allowed(self, command: str) -> None:
        assert outcome(f"{GIT} {command}", ctx(probe=FaultingProbe())) is Outcome.ALLOW

    def test_i010_recovery_objects_are_not_destroyed(self) -> None:
        for command in ("gc --prune=now", "prune", "reflog expire --all", "stash clear"):
            assert outcome(f"{GIT} {command}") is Outcome.DENY_REQUIRES_HUMAN, command

    @pytest.mark.parametrize(
        "command",
        [
            "stash push",
            "reset --hard HEAD",
            "restore src/app.py",
            "checkout -- src/app.py",
            "clean -fd",
            "branch -D feature",
            "gc",
        ],
    )
    def test_i011_mutating_probes_are_forbidden(self, command: str) -> None:
        context = ctx(
            purpose=Purpose.DIAGNOSTIC_PROBE,
            probe=StaticProbe(dirty=(), clean_targets=(), unique_commits=False),
        )
        assert outcome(f"{GIT} {command}", context) is Outcome.DENY_REQUIRES_HUMAN

    def test_i011_probe_shape_is_inferred_from_stash_pop_sandwich(self) -> None:
        command = f"{GIT} stash push && {GIT} status && {GIT} stash pop"
        context = ctx(probe=StaticProbe(dirty=agent_dirty("a.py")))
        assert outcome(command, context) is Outcome.DENY_REQUIRES_HUMAN

    def test_i012_guard_capture_does_not_mutate_the_protected_state(
        self, stacked_repo: Path, tmp_path: Path
    ) -> None:
        (stacked_repo / "a.txt").write_text("dirty edit\n", encoding="utf-8")
        before = subprocess.run(
            ["git", "-C", str(stacked_repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        vault = tmp_path / "vault"
        receipt = capture_recovery(
            GuardContext(
                root=stacked_repo,
                env={"L9_GUARDRAIL_RECOVERY_DIR": str(vault)},
            ),
            "reset",
        )
        after = subprocess.run(
            ["git", "-C", str(stacked_repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert receipt is not None and receipt.is_file()
        assert vault in receipt.parents, "recovery must live outside the repository"
        assert before == after, "a guardrail must not mutate the state it protects"
        assert "dirty edit" in receipt.read_text(encoding="utf-8")

    def test_i013_compound_is_classified_by_effect_not_by_loudest_token(
        self, tmp_path: Path
    ) -> None:
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        context = ctx(env={"SP": str(scratch)}, scratch_roots=(scratch.resolve(),))
        command = f'{RMRF} "$SP/export" && {GIT} status'
        assert outcome(command, context) is Outcome.ALLOW

    def test_i014_verified_ephemeral_cleanup_is_safe(self, tmp_path: Path) -> None:
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        context = ctx(scratch_roots=(scratch.resolve(),), env={})
        assert outcome(f"{RMRF} {scratch}/build", context) is Outcome.ALLOW

    def test_i015_parser_uncertainty_never_upgrades_to_allow(self) -> None:
        assert outcome(f"{GIT} branch -D") is Outcome.DENY_REQUIRES_HUMAN
        assert outcome(RMRF) is Outcome.DENY_REQUIRES_HUMAN
        assert outcome(f"{GIT} update-ref refs/heads/main HEAD") is Outcome.DENY_REQUIRES_HUMAN

    def test_i016_evaluator_failure_never_blocks_read_only_git(self) -> None:
        assert outcome(f"{GIT} diff", ctx(probe=FaultingProbe())) is Outcome.ALLOW
        assert outcome(f"{GIT} log -1", ctx(probe=FaultingProbe())) is Outcome.ALLOW

    def test_i017_evaluator_failure_never_allows_unrecoverable_mutation(self) -> None:
        for command in ("reset --hard", "clean -fd", "restore src/app.py"):
            assert (
                outcome(f"{GIT} {command}", ctx(probe=FaultingProbe()))
                is Outcome.DENY_REQUIRES_HUMAN
            ), command


# ---------------------------------------------------------------------------
# prohibited_behavior — the contract allows zero of these
# ---------------------------------------------------------------------------


class TestProhibitedBehavior:
    def test_no_blanket_allow_all_git(self) -> None:
        """The old exemption allowed every git command unconditionally."""
        denied = [
            f"{GIT} clean -fdx",
            f"{GIT} gc --prune=now",
            f"{GIT} prune",
            f"{GIT} push --force origin feature",
        ]
        for command in denied:
            assert outcome(command) is Outcome.DENY_REQUIRES_HUMAN, command

    def test_no_blanket_deny_by_subcommand_name(self) -> None:
        """The old isolation gate denied these by name alone."""
        allowed = [
            (f"{GIT} reset --hard HEAD", ctx(probe=StaticProbe(dirty=()))),
            (f"{GIT} clean -fd", ctx(probe=StaticProbe(clean_targets=("build/",)))),
            (
                f"{GIT} restore src/untouched.py",
                ctx(probe=StaticProbe(dirty=user_dirty("other.py"))),
            ),
            (f"{GIT} checkout other", ctx(probe=StaticProbe(dirty=()))),
        ]
        for command, context in allowed:
            assert outcome(command, context) is Outcome.ALLOW, command

    def test_stash_is_neither_inherently_safe_nor_inherently_forbidden(self) -> None:
        task = ctx(
            probe=StaticProbe(dirty=agent_dirty("a.py")),
            recovery_available=frozenset({Recoverability.BACKUP_REF}),
        )
        probe = ctx(purpose=Purpose.DIAGNOSTIC_PROBE)
        assert outcome(f"{GIT} stash push", task) is Outcome.GUARD_THEN_ALLOW
        assert outcome(f"{GIT} stash push", probe) is Outcome.DENY_REQUIRES_HUMAN

    def test_force_with_lease_is_not_denied_when_proven(self) -> None:
        context = ctx(
            probe=StaticProbe(lease_known=True, branch="feature"),
            private_branches=frozenset({"feature"}),
        )
        assert (
            outcome(f"{GIT} push --force-with-lease origin feature", context)
            is Outcome.GUARD_THEN_ALLOW
        )

    def test_force_with_lease_denied_when_expected_sha_unknown(self) -> None:
        context = ctx(
            probe=StaticProbe(lease_known=False, branch="feature"),
            private_branches=frozenset({"feature"}),
        )
        assert (
            outcome(f"{GIT} push --force-with-lease origin feature", context)
            is Outcome.DENY_REQUIRES_HUMAN
        )

    def test_unknown_rm_target_is_never_safe(self) -> None:
        for target in ("/", "~", "$UNSET_ROOT/x", "*"):
            assert outcome(f"{RMRF} {target}") is Outcome.DENY_REQUIRES_HUMAN, target

    def test_repository_root_and_git_dir_are_never_deleted(self, stacked_repo: Path) -> None:
        context = ctx(root=stacked_repo)
        assert outcome(f"{RMRF} {stacked_repo}", context) is Outcome.DENY_REQUIRES_HUMAN
        assert outcome(f"{RMRF} {stacked_repo}/.git", context) is Outcome.DENY_REQUIRES_HUMAN


# ---------------------------------------------------------------------------
# human authorization + guard execution
# ---------------------------------------------------------------------------


class TestHumanAuthorization:
    def test_explicit_reason_lifts_a_denial(self) -> None:
        context = ctx(
            env={HUMAN_AUTHORIZATION_ENV: "operator confirmed disposable clone"},
            probe=StaticProbe(clean_targets=("notes.txt",)),
        )
        assert outcome(f"{GIT} clean -fdx", context) is Outcome.ALLOW

    def test_rubber_stamp_is_not_a_reason(self) -> None:
        for stamp in ("1", "true", "yes", "  ", "ok"):
            context = ctx(
                env={HUMAN_AUTHORIZATION_ENV: stamp},
                probe=StaticProbe(clean_targets=("notes.txt",)),
            )
            assert outcome(f"{GIT} clean -fdx", context) is Outcome.DENY_REQUIRES_HUMAN, stamp

    def test_human_authorized_rejects_empty_and_stamps(self) -> None:
        assert not human_authorized({})
        assert not human_authorized({HUMAN_AUTHORIZATION_ENV: "yes"})
        assert human_authorized({HUMAN_AUTHORIZATION_ENV: "rotating a dead test ref"})


class TestGuardExecution:
    def test_guard_without_recovery_need_allows_immediately(self) -> None:
        context = ctx()
        decision = evaluate_command(f"{GIT} gc", context)
        result = run_guards(decision, context)
        assert result.allowed and result.receipt is None

    def test_guard_needing_capture_denies_when_capture_impossible(self) -> None:
        context = ctx(
            probe=StaticProbe(dirty=user_dirty("a.py"), capture_capable=True),
            root=None,
        )
        decision = evaluate_command(f"{GIT} reset --hard HEAD", context)
        assert decision.outcome is Outcome.GUARD_THEN_ALLOW
        result = run_guards(decision, context)
        assert not result.allowed
        assert "Recovery capture failed" in result.reason

    def test_guard_captures_recovery_on_a_real_repo(
        self, stacked_repo: Path, tmp_path: Path
    ) -> None:
        (stacked_repo / "a.txt").write_text("uncommitted\n", encoding="utf-8")
        context = GuardContext(
            root=stacked_repo,
            env={"L9_GUARDRAIL_RECOVERY_DIR": str(tmp_path / "vault")},
            probe=StaticProbe(dirty=user_dirty("a.txt"), capture_capable=True),
        )
        decision = evaluate_command(f"{GIT} reset --hard HEAD", context)
        assert decision.outcome is Outcome.GUARD_THEN_ALLOW
        result = run_guards(decision, context)
        assert result.allowed and result.receipt is not None
        assert result.receipt.is_file()


class TestGhPolicy:
    @pytest.mark.parametrize(
        "command",
        ["gh pr list", "gh pr view 12", "gh pr checks", "gh run list", "gh repo view"],
    )
    def test_read_only_gh_allowed(self, command: str) -> None:
        assert outcome(command) is Outcome.ALLOW

    def test_api_get_allowed_and_delete_denied(self) -> None:
        assert outcome("gh api repos/o/r/pulls") is Outcome.ALLOW
        assert outcome("gh api -X DELETE repos/o/r/git/refs/heads/x") is (
            Outcome.DENY_REQUIRES_HUMAN
        )

    def test_admin_merge_denied_and_ordinary_merge_guarded(self) -> None:
        assert outcome("gh pr merge 12 --admin") is Outcome.DENY_REQUIRES_HUMAN
        assert outcome("gh pr merge 12 --squash") is Outcome.GUARD_THEN_ALLOW


def test_effects_are_reported_for_audit() -> None:
    decision = evaluate_command(
        f"{GIT} clean -fd", ctx(probe=StaticProbe(clean_targets=("build/",)))
    )
    assert decision.findings
    assert decision.findings[0].effect is Effect.UNTRACKED_DELETION
