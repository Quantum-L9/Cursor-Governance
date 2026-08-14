#!/usr/bin/env python3
"""Apply the Peer Execution Core PR pack to the exact bound Cursor-Governance base."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_SHA = "0fbd477e507d33ee52f2a87c2d9eb77c15b6a492"
OLD_AUTONOMY = "environment/agents/adapters/claude-code/autonomy"
NEW_AUTONOMY = "environment/program-execution/peer_execution/autonomy"
COMMAND_TIMEOUT_SECONDS = 300

ACTIVE_AUTONOMY_REFERENCE_PATHS = (
    "Makefile",
    ".claude/hooks/session_start_claude_governance.sh",
    "conftest.py",
    "environment/agents/PEER_EXECUTION.md",
    "environment/agents/adapters/claude-code/hooks/SESSION_START_SPEC.md",
    "environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh",
    "environment/agents/tools/validate_executable_peers.py",
    "environment/contracts/autonomy/README.md",
    "environment/program-execution/COMPATIBILITY.yaml",
    "environment/program-execution/OWNERSHIP.md",
    "environment/program-execution/tests/test_existing_runtime_boundaries.py",
    "ops/config/python-contract.json",
    "ops/scripts/run_python_test_suites.py",
    "rules/88-bounded-session-autonomy.mdc",
    "skills/l9-bounded-autonomy/SKILL.md",
    "skills/l9-bounded-autonomy/references/claude-code-bridge.md",
    "skills/l9-bounded-autonomy/references/doctrine-map.md",
    "skills/l9-bounded-autonomy/references/join-and-merge-gate.md",
    "skills/l9-code-maintenance/references/protected-paths.md",
)


def run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(args),
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out: {' '.join(args)}") from exc
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}"
        )
    return result


def _safe_repo_target(repo: Path, relative: str | Path) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError(f"unsafe repository-relative path: {relative}")
    cursor = repo
    for part in rel.parts[:-1]:
        cursor /= part
        if cursor.is_symlink():
            raise RuntimeError(f"refusing symlinked parent write target: {cursor}")
    target = repo / rel
    if target.is_symlink():
        raise RuntimeError(f"refusing symlinked write target: {target}")
    return target


def _require_regular_file(repo: Path, relative: str | Path) -> Path:
    target = _safe_repo_target(repo, relative)
    if not target.is_file():
        raise RuntimeError(f"required file missing: {relative}")
    return target


def require_exact_base(repo: Path) -> None:
    inside = run(repo, "git", "rev-parse", "--is-inside-work-tree", check=False)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise RuntimeError(f"not a Git worktree: {repo}")
    top = Path(run(repo, "git", "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != repo:
        raise RuntimeError(f"repository argument must be the worktree root: {top}")
    head = run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    if head != BASE_SHA:
        raise RuntimeError(f"base SHA mismatch: expected {BASE_SHA}, found {head}")
    dirty = run(repo, "git", "status", "--porcelain").stdout.strip()
    if dirty:
        raise RuntimeError("worktree must be clean before applying this pack")


def git_mv(repo: Path, source: str, target: str) -> None:
    src = repo / source
    if src.is_symlink():
        raise RuntimeError(f"refusing to move symlinked source path: {source}")
    if not src.exists():
        raise RuntimeError(f"required source path missing: {source}")
    target_path = _safe_repo_target(repo, target)
    if target_path.exists() or target_path.is_symlink():
        raise RuntimeError(f"move target already exists: {target}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    run(repo, "git", "mv", source, target)


def git_rm_if_present(repo: Path, rel: str) -> None:
    path = repo / rel
    if path.exists() or path.is_symlink():
        run(repo, "git", "rm", "-f", "--", rel)


def git_rm_tree_if_present(repo: Path, rel: str) -> None:
    path = repo / rel
    if path.exists() or path.is_symlink():
        run(repo, "git", "rm", "-r", "-f", "--", rel)


def replace_in_paths(repo: Path, old: str, new: str, paths: tuple[str, ...]) -> int:
    replacements = 0
    for relative in paths:
        path = _require_regular_file(repo, relative)
        text = path.read_text(encoding="utf-8")
        hits = text.count(old)
        if hits == 0:
            raise RuntimeError(f"active migration anchor missing: {relative}: {old}")
        path.write_text(text.replace(old, new), encoding="utf-8")
        replacements += hits
    return replacements


def copy_overlay(repo: Path, overlay: Path) -> None:
    for source in sorted(overlay.rglob("*")):
        if source.is_symlink():
            raise RuntimeError(f"overlay symlinks are forbidden: {source.relative_to(overlay)}")
        relative = source.relative_to(overlay)
        target = _safe_repo_target(repo, relative)
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def patch_peer_execution_base(repo: Path) -> None:
    path = _require_regular_file(repo, "environment/program-execution/peer_execution/base.py")
    text = path.read_text(encoding="utf-8")
    old = "SchemaRegistry(Path(__file__).resolve().parents[2])"
    new = "SchemaRegistry(Path(__file__).resolve().parents[1])"
    if old not in text:
        raise RuntimeError("peer_execution/base.py schema-root anchor not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_makefile(repo: Path) -> None:
    path = _require_regular_file(repo, "Makefile")
    text = path.read_text(encoding="utf-8")
    marker = "$(PE_ROOT)/scripts/validate_execution_adapters.py"
    thin = "$(PE_ROOT)/scripts/validate_thin_providers.py"
    if marker not in text:
        raise RuntimeError("Makefile Program Execution validator anchor missing")
    if thin not in text:
        lines = text.splitlines()
        output: list[str] = []
        for line in lines:
            output.append(line)
            if marker in line:
                output.append(
                    "\tPYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) "
                    "python3 -B $(PE_ROOT)/scripts/validate_thin_providers.py"
                )
        text = "\n".join(output) + "\n"
    text = text.replace(
        "program-execution-conformance: autonomy-contracts-validate",
        "program-execution-conformance: autonomy-validate",
        1,
    )
    path.write_text(text, encoding="utf-8")


def _replace_required(path: Path, old: str, new: str, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing symlinked doctrine write: {path}")
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"active-doctrine migration anchor missing: {label}: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_active_doctrine(repo: Path) -> None:
    law = _require_regular_file(repo, "CANONICAL_LAW.md")
    _replace_required(
        law,
        "root `autonomy/` + `ops/autonomy` + Claude scheduler SSOTs",
        "root `autonomy/` + `ops/autonomy` + shared Peer Execution bounded runtime",
        "canonical autonomy family",
    )
    text = law.read_text(encoding="utf-8")
    law_row = (
        "| **Peer Execution thin-adapter law** | "
        "`environment/contracts/execution/PEER_EXECUTION_THIN_ADAPTER_LAW.yaml` | "
        "Binding provider-neutral execution architecture; validate via "
        "`make peer-execution-conformance` |"
    )
    if law_row not in text:
        lines = text.splitlines()
        output: list[str] = []
        inserted = False
        for line in lines:
            output.append(line)
            if "**Autonomy family**" in line:
                output.append(law_row)
                inserted = True
        if not inserted:
            raise RuntimeError("CANONICAL_LAW autonomy-family row missing")
        law.write_text("\n".join(output) + "\n", encoding="utf-8")

    agents = _require_regular_file(repo, "AGENTS.md")
    old_agents = (
        "Claude Code\nmachine runtime remains `environment/claude-code/autonomy/` — "
        "see its README\n“Cursor SOP” link. Human merge only; do not rewrite the "
        "Python scheduler from Cursor."
    )
    new_agents = (
        "Bounded concurrency runtime is provider-neutral at "
        "`environment/program-execution/peer_execution/autonomy/`. Every "
        "provider binds to the same shared runtime through Program Execution; "
        "no provider owns a scheduler. Human merge only."
    )
    _replace_required(agents, old_agents, new_agents, "AGENTS bounded runtime")

    autonomy = _require_regular_file(repo, "commands/autonomy.md")
    _replace_required(
        autonomy,
        "(SSOT map for root `autonomy/`, `ops/autonomy`, Claude scheduler).",
        "(SSOT map for root `autonomy/`, `ops/autonomy`, and the shared Peer "
        "Execution bounded runtime).",
        "autonomy command family",
    )

    l9_plan = _require_regular_file(repo, "commands/l9-plan.md")
    _replace_required(
        l9_plan,
        "  → PE adapter (cursor-foreground default)",
        "  → Peer Execution Core → thin provider (cursor-foreground default)",
        "l9-plan execution path",
    )

    template = _require_regular_file(
        repo,
        "environment/contracts/execution/templates/"
        "canonical.template.executable_plan.v1.plan.md",
    )
    _replace_required(
        template,
        "PE adapter (Cursor: cursor-foreground | cursor-background;\n"
        "            Claude: claude-code-bounded-autonomy)",
        "Peer Execution Core -> thin provider\n"
        "  (Cursor: cursor-foreground | cursor-background;\n"
        "   Claude: claude-code-direct)",
        "executable plan provider path",
    )
    _replace_required(
        template,
        "| repository implementation | `claude-code-bounded-autonomy` → "
        "`cursor-background` → `cursor-foreground` |",
        "| repository implementation | `claude-code-direct` → "
        "`cursor-background` → `cursor-foreground` |",
        "executable plan routing",
    )
    _replace_required(
        template,
        "  adapter_id: cursor-foreground    # or routed adapter",
        "  provider_ref: cursor-foreground  # or routed thin provider\n"
        "  execution_profile_ref: worker-default",
        "executable plan binding fields",
    )


def patch_controller_abort(repo: Path) -> None:
    controller = _require_regular_file(
        repo,
        "environment/program-execution/core/program-execution-controller-template/"
        "scripts/pec/controller.py",
    )
    text = controller.read_text(encoding="utf-8")
    import_old = (
        "from .common import digest_object, load_json, load_yaml, parse_time, "
        "run_git, utc_now, write_json"
    )
    import_new = (
        "from .common import digest_object, load_json, load_yaml, parse_time, "
        "resolve_within, run_git, utc_now, write_json"
    )
    if import_old in text:
        text = text.replace(import_old, import_new, 1)
    elif import_new not in text:
        raise RuntimeError("Controller common-import anchor missing")
    if "def abort_execution(" not in text:
        marker = "\ndef recover(workspace: Path, actor: str) -> dict[str, Any]:\n"
        if marker not in text:
            raise RuntimeError("Controller recover anchor missing")
        abort_code = r'''

def abort_execution(
    workspace: Path,
    task_id: str,
    reason: str,
    actor: str,
) -> dict[str, Any]:
    """Controller-owned fail-closed abort for an admitted repository execution."""

    workspace = workspace.resolve()
    db, ledger = open_runtime(workspace)
    moved_worktree = None
    moved_receipt = None
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        allowed_states = {
            "LEASED", "PREPARED", "CONTRACTED", "EXECUTING", "VERIFYING", "FAILED"
        }
        if task["runtime_state"] not in allowed_states:
            raise ControllerError(f"task cannot abort from state {task['runtime_state']}")
        lease = db.active_lease_for_task(task_id)
        if lease is None:
            raise ControllerError("active lease required for execution abort")
        repo = db.repository(lease["repository_id"])
        if repo is None or not repo.get("local_path"):
            raise ControllerError("reconciled repository required for execution abort")
        recovery_root = workspace / "recovery" / task_id / lease["lease_id"]
        if recovery_root.exists():
            raise ControllerError(f"recovery artifact already exists: {recovery_root}")
        recovery_root.mkdir(parents=True, exist_ok=False)
        metadata = {
            "schema": "program-execution-controller.execution-abort.v1",
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "runtime_state_before": task["runtime_state"],
            "reason": reason,
            "actor": actor,
            "aborted_at": utc_now(),
            "base_sha": lease["base_sha"],
            "branch": lease["branch"],
        }
        worktree = Path(lease["worktree"]) if lease.get("worktree") else None
        if worktree is not None and worktree.is_dir():
            (recovery_root / "status.txt").write_text(
                run_git(worktree, "status", "--porcelain=v1").stdout,
                encoding="utf-8",
            )
            (recovery_root / "changes.patch").write_text(
                run_git(worktree, "diff", "--binary", check=False).stdout,
                encoding="utf-8",
            )
            (recovery_root / "untracked.txt").write_text(
                run_git(worktree, "ls-files", "--others", "--exclude-standard").stdout,
                encoding="utf-8",
            )
            moved = recovery_root / "worktree"
            repo_path = Path(repo["local_path"]).resolve()
            move_result = run_git(
                repo_path, "worktree", "move", str(worktree), str(moved), check=False
            )
            if move_result.returncode != 0:
                raise ControllerError(
                    "failed to move worktree into recovery: " + move_result.stderr.strip()
                )
            recovery_branch = (
                f"recovery/peer-execution/{task_id.lower()}/"
                f"{lease['lease_id'].split('-', 1)[-1]}"
            )
            rename = run_git(moved, "branch", "-m", recovery_branch, check=False)
            if rename.returncode != 0:
                run_git(repo_path, "worktree", "move", str(moved), str(worktree))
                raise ControllerError(
                    "failed to rename recovery branch: " + rename.stderr.strip()
                )
            moved_worktree = (
                repo_path, worktree, moved, lease["branch"], recovery_branch
            )
            metadata["recovery_worktree"] = str(moved)
            metadata["recovery_branch"] = recovery_branch
        rendered_path = task.get("rendered_contract_path")
        if rendered_path and Path(rendered_path).is_file():
            rendered = load_json(Path(rendered_path))
            receipt_value = rendered.get("attempt_receipt_path")
            if isinstance(receipt_value, str) and receipt_value:
                receipt = resolve_within(
                    workspace / "attempts", Path(receipt_value).expanduser()
                )
                if receipt.is_file() and db.latest_attempt(task_id) is None:
                    quarantine = recovery_root / "unrecorded-attempt-receipt.json"
                    receipt.replace(quarantine)
                    moved_receipt = (receipt, quarantine)
                    metadata["quarantined_attempt_receipt"] = str(quarantine)
        write_json(recovery_root / "metadata.json", metadata)
        target_state = (
            "FAILED"
            if task["runtime_state"] in {"EXECUTING", "VERIFYING", "FAILED"}
            else "STALE"
        )
        try:
            db.conn.execute("BEGIN IMMEDIATE")
            db.conn.execute(
                "UPDATE leases SET active=0 WHERE lease_id=? AND active=1",
                (lease["lease_id"],),
            )
            db.conn.execute(
                """
                UPDATE tasks
                SET runtime_state=?, lease_id=NULL, worktree=NULL,
                    rendered_contract_path=NULL, rendered_contract_digest=NULL,
                    last_error=?
                WHERE id=?
                """,
                (target_state, f"execution_aborted:{reason}", task_id),
            )
            db.conn.commit()
        except Exception:
            db.conn.rollback()
            if moved_receipt is not None:
                original, quarantine = moved_receipt
                original.parent.mkdir(parents=True, exist_ok=True)
                quarantine.replace(original)
            if moved_worktree is not None:
                repo_path, original, moved, original_branch, _ = moved_worktree
                run_git(moved, "branch", "-m", original_branch, check=False)
                run_git(
                    repo_path,
                    "worktree",
                    "move",
                    str(moved),
                    str(original),
                    check=False,
                )
            raise
        evidence_id = f"EVID-ABORT-{lease['lease_id']}"
        ledger.append(
            "EXECUTION_ABORTED",
            actor,
            {
                "task_id": task_id,
                "lease_id": lease["lease_id"],
                "reason": reason,
                "state": target_state,
                "recovery_artifact": str(recovery_root),
                "evidence_id": evidence_id,
            },
        )
        return {
            "status": "ABORTED",
            "task_id": task_id,
            "state": target_state,
            "lease_id": lease["lease_id"],
            "recovery_artifact": str(recovery_root),
            "evidence_id": evidence_id,
        }
    finally:
        db.close()
'''
        text = text.replace(marker, abort_code + marker, 1)
    controller.write_text(text, encoding="utf-8")

    cli = _require_regular_file(
        repo,
        "environment/program-execution/core/program-execution-controller-template/"
        "scripts/pec/cli.py",
    )
    text = cli.read_text(encoding="utf-8")
    if "    abort_execution,\n" not in text:
        anchor = "    add_approval,\n"
        if anchor not in text:
            raise RuntimeError("Controller CLI import anchor missing")
        text = text.replace(anchor, "    abort_execution,\n" + anchor, 1)
    parser_anchor = (
        '    cmd = sub.add_parser("recover")\n'
        '    cmd.add_argument("--workspace", required=True, type=Path)\n'
        '    cmd.add_argument("--actor", required=True)\n'
    )
    parser_block = (
        '    cmd = sub.add_parser("abort-execution")\n'
        '    cmd.add_argument("task_id")\n'
        '    cmd.add_argument("--workspace", required=True, type=Path)\n'
        '    cmd.add_argument("--reason", required=True)\n'
        '    cmd.add_argument("--actor", required=True)\n\n'
    )
    if 'sub.add_parser("abort-execution")' not in text:
        if parser_anchor not in text:
            raise RuntimeError("Controller CLI recover parser anchor missing")
        text = text.replace(parser_anchor, parser_block + parser_anchor, 1)
    dispatch_anchor = (
        '        elif args.command == "recover":\n'
        '            value = recover(args.workspace, args.actor)\n'
    )
    dispatch_block = (
        '        elif args.command == "abort-execution":\n'
        '            value = abort_execution(\n'
        '                args.workspace, args.task_id, args.reason, args.actor\n'
        '            )\n'
    )
    if 'args.command == "abort-execution"' not in text:
        if dispatch_anchor not in text:
            raise RuntimeError("Controller CLI recover dispatch anchor missing")
        text = text.replace(dispatch_anchor, dispatch_block + dispatch_anchor, 1)
    cli.write_text(text, encoding="utf-8")


def archive_stale_validation(repo: Path) -> None:
    moves = (
        (
            "environment/program-execution/validation/validation_checks.jsonl",
            "environment/program-execution/validation/history/"
            "validation_checks.pre_peer_execution_core.jsonl",
        ),
        (
            "environment/program-execution/validation/validation_report.yaml",
            "environment/program-execution/validation/history/"
            "validation_report.pre_peer_execution_core.yaml",
        ),
        (
            "environment/program-execution/validation/validation_findings.jsonl",
            "environment/program-execution/validation/history/"
            "validation_findings.pre_peer_execution_core.jsonl",
        ),
        (
            "environment/program-execution/validation/collision_report.yaml",
            "environment/program-execution/validation/history/"
            "collision_report.pre_peer_execution_core.yaml",
        ),
        (
            "environment/program-execution/validation/source_reuse_report.yaml",
            "environment/program-execution/validation/history/"
            "source_reuse_report.pre_peer_execution_core.yaml",
        ),
        (
            "environment/program-execution/validation/VALIDATION.md",
            "environment/program-execution/validation/history/"
            "VALIDATION.pre_peer_execution_core.md",
        ),
    )
    for source, target in moves:
        git_mv(repo, source, target)


def append_supersession_note(repo: Path) -> None:
    path = _require_regular_file(
        repo,
        "docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md",
    )
    text = path.read_text(encoding="utf-8")
    note = (
        "\n\n## 2026-08-12 supersession note\n\n"
        "The scheduler mechanics described here are no longer Claude-adapter-owned. "
        "Their canonical home is "
        "`environment/program-execution/peer_execution/autonomy/`. "
        "Provider adapters remain thin; Program Execution remains the "
        "Program-state authority.\n"
    )
    if "## 2026-08-12 supersession note" not in text:
        path.write_text(text.rstrip() + note, encoding="utf-8")


def remove_legacy_bounded_provider_references(repo: Path) -> None:
    relative_paths = (
        "environment/program-execution/scripts/validate_execution_adapters.py",
        "environment/program-execution/tests/test_full_adapter_matrix.py",
    )
    target = '"claude-code-bounded-autonomy",'
    for relative in relative_paths:
        path = _require_regular_file(repo, relative)
        lines = path.read_text(encoding="utf-8").splitlines()
        matching = [index for index, line in enumerate(lines) if line.strip() == target]
        if len(matching) != 1:
            raise RuntimeError(f"bounded-provider migration anchor invalid: {path}")
        del lines[matching[0]]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def regenerate_generated_indexes(repo: Path) -> None:
    scripts = (
        "environment/program-execution/scripts/render_capability_index.py",
        "environment/program-execution/scripts/render_adapter_matrix.py",
    )
    for relative in scripts:
        result = run(repo, sys.executable, relative, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"index regeneration failed ({relative}): {result.stderr}")


def regenerate_llm_rules(repo: Path) -> None:
    result = run(
        repo,
        sys.executable,
        "ops/scripts/project_llm_rules.py",
        "--root",
        str(repo),
        "--quiet",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LLM-rule regeneration failed: {result.stderr}")


def regenerate_manifest(repo: Path) -> None:
    result = run(
        repo,
        sys.executable,
        "environment/program-execution/scripts/generate_manifest.py",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"manifest regeneration failed: {result.stderr}")


def assert_active_autonomy_refs_migrated(repo: Path) -> None:
    stale: list[str] = []
    for relative in ACTIVE_AUTONOMY_REFERENCE_PATHS:
        path = _require_regular_file(repo, relative)
        if OLD_AUTONOMY in path.read_text(encoding="utf-8"):
            stale.append(relative)
    generated = repo / "environment/generated/llm-rules"
    if generated.is_dir():
        for path in sorted(generated.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if OLD_AUTONOMY in text:
                stale.append(path.relative_to(repo).as_posix())
    if stale:
        raise RuntimeError(f"active legacy autonomy references remain: {stale}")


def _apply_mutations(repo: Path, overlay: Path) -> None:
    git_mv(
        repo,
        "environment/program-execution/adapters/common",
        "environment/program-execution/peer_execution",
    )
    git_mv(repo, OLD_AUTONOMY, NEW_AUTONOMY)
    old_meta = "environment/contracts/autonomy/meta/claude-code-bounded-autonomy-scheduler.meta.md"
    new_meta = "environment/contracts/autonomy/meta/peer-execution-bounded-autonomy-runtime.meta.md"
    git_mv(repo, old_meta, new_meta)

    replaced = replace_in_paths(
        repo,
        OLD_AUTONOMY,
        NEW_AUTONOMY,
        ACTIVE_AUTONOMY_REFERENCE_PATHS,
    )
    if replaced < len(ACTIVE_AUTONOMY_REFERENCE_PATHS):
        raise RuntimeError("active autonomy reference migration was incomplete")

    shared_cli = _require_regular_file(repo, f"{NEW_AUTONOMY}/cli.py")
    _replace_required(
        shared_cli,
        'argparse.ArgumentParser(prog="l9-claude-autonomy")',
        'argparse.ArgumentParser(prog="l9-peer-execution-autonomy")',
        "shared bounded-runtime CLI identity",
    )

    delete_paths = (
        "environment/program-execution/adapters/claude-code/driver.py",
        "environment/program-execution/adapters/claude-code/receipt_mapper.py",
        "environment/program-execution/adapters/cursor-foreground/receipt_mapper.py",
        "environment/program-execution/adapters/cursor-background/receipt_mapper.py",
        "environment/program-execution/adapters/claude-code-bounded-autonomy/receipt_mapper.py",
        "environment/program-execution/adapters/codex/driver.py",
        "environment/program-execution/adapters/gemini/driver.py",
        "environment/program-execution/adapters/manus/driver.py",
        "environment/program-execution/adapters/chatgpt/receipt_mapper.py",
        "environment/program-execution/adapters/ci/generic-shell/driver.py",
        "environment/program-execution/adapters/ci/generic-shell/receipt_mapper.py",
        "environment/program-execution/adapters/ci/github-actions/receipt_mapper.py",
        "environment/program-execution/adapters/github/remote-actions/receipt_mapper.py",
        "environment/program-execution/adapters/github/checks/receipt_mapper.py",
        "environment/program-execution/adapters/github/deployments/receipt_mapper.py",
    )
    for rel in delete_paths:
        git_rm_if_present(repo, rel)

    git_rm_tree_if_present(
        repo,
        "environment/program-execution/adapters/claude-code-bounded-autonomy",
    )
    git_rm_tree_if_present(
        repo,
        "environment/program-execution/integrations/claude-code-bounded-autonomy",
    )

    archive_stale_validation(repo)
    copy_overlay(repo, overlay)
    patch_controller_abort(repo)
    patch_peer_execution_base(repo)
    patch_makefile(repo)
    patch_active_doctrine(repo)
    remove_legacy_bounded_provider_references(repo)
    append_supersession_note(repo)
    regenerate_generated_indexes(repo)
    regenerate_llm_rules(repo)
    assert_active_autonomy_refs_migrated(repo)
    regenerate_manifest(repo)



def _rollback_clean_base(repo: Path) -> None:
    run(repo, "git", "reset", "--hard", BASE_SHA, check=False)
    run(repo, "git", "clean", "-fd", check=False)


def _apply_patch_atomically(repo: Path, patch: str, expected_tree: str) -> None:
    result = subprocess.run(
        ["git", "apply", "--index", "--binary", "--whitespace=nowarn", "-"],
        cwd=repo,
        input=patch,
        text=True,
        capture_output=True,
        check=False,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        _rollback_clean_base(repo)
        raise RuntimeError(f"atomic patch apply failed: {result.stderr}")
    observed_tree = run(repo, "git", "write-tree").stdout.strip()
    if observed_tree != expected_tree:
        _rollback_clean_base(repo)
        raise RuntimeError(
            f"applied tree mismatch: expected {expected_tree}, observed {observed_tree}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="clean Cursor-Governance clone")
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    pack_root = Path(__file__).resolve().parents[1]
    overlay = pack_root / "repo_overlay"
    require_exact_base(repo)

    with tempfile.TemporaryDirectory(prefix="l9-peer-execution-stage-") as tmp:
        staging = Path(tmp) / "repo"
        run(repo, "git", "worktree", "add", "--detach", str(staging), BASE_SHA)
        try:
            _apply_mutations(staging, overlay)
            run(staging, "git", "add", "-A")
            check = run(staging, "git", "diff", "--cached", "--check", check=False)
            if check.returncode != 0:
                raise RuntimeError(
                    f"staged change whitespace check failed: {check.stdout}{check.stderr}"
                )
            expected_tree = run(staging, "git", "write-tree").stdout.strip()
            patch = run(
                staging,
                "git",
                "diff",
                "--cached",
                "--binary",
                "--full-index",
                BASE_SHA,
                "--",
            ).stdout
            if not patch.strip():
                raise RuntimeError("staged repair produced an empty patch")
        finally:
            run(
                repo,
                "git",
                "worktree",
                "remove",
                "--force",
                str(staging),
                check=False,
            )

    _apply_patch_atomically(repo, patch, expected_tree)
    print(f"APPLIED: Cursor-Governance Peer Execution Core pack on {BASE_SHA}")
    print(f"APPLIED_TREE: {expected_tree}")
    print("REMOTE_MUTATION: none")
    print("NEXT: python3 <pack>/scripts/validate_applied_repo.py <repo>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
