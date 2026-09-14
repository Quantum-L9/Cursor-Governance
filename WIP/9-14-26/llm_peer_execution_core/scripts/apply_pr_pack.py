#!/usr/bin/env python3
"""Governed additive-only porter for Peer Execution Core.

Retargeted to feat/kernel-pack-new-branch-default after Wave 0.
Does not hard-reset, force-clean, force-push, or overwrite additive-only roots.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LANDING_BRANCH = "feat/kernel-pack-new-branch-default"
LANDING_SHA = "5707ea8cefd15cfd5b80a9c1503e3f03119f6adc"
FORBIDDEN_BRANCHES = (
    "backup/local-unpushed-2026-08-14",
    "feat/wip-legal-defense-26cr-ingest",
    "feat/peer-execution-core",
)
OLD_AUTONOMY = "environment/agents/adapters/claude-code/autonomy"
NEW_AUTONOMY = "environment/program-execution/peer_execution/autonomy"
COMMAND_TIMEOUT_SECONDS = 300

# Root files that may only be appended, never wholesale-replaced.
ADDITIVE_ONLY_ROOTS = frozenset(
    {
        "CANONICAL_LAW.md",
        "AGENTS.md",
        "Makefile",
        "conftest.py",
    }
)

# Path prefixes the porter may leave dirty before apply, or write during apply.
ALLOWED_DIRTY_PREFIXES = (
    "WIP/llm_peer_execution_core/",
    "environment/contracts/execution/",
    "docs/decisions/ADR-0017",
    "docs/decisions/ADR-0018",
    "docs/decisions/ADR-0019",
    "docs/decisions/ADR-0020",
    "docs/decisions/ADR-0021",
    "docs/decisions/ADR-0022",
    "docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md",
)

ACTIVE_AUTONOMY_REFERENCE_PATHS = (
    ".claude/hooks/session_start_claude_governance.sh",
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

OVERLAY_SKIP = frozenset({"conftest.py"})


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


def _allowed_dirty(rel: str) -> bool:
    if rel.startswith("WIP/Legal Defense/") or rel.startswith("WIP/Legal Defense"):
        return True  # may exist; porter must not mutate it
    if rel.startswith("WIP/"):
        return True
    return any(
        rel == prefix or rel.startswith(prefix) for prefix in ALLOWED_DIRTY_PREFIXES
    )


def require_landing_base(repo: Path) -> None:
    inside = run(repo, "git", "rev-parse", "--is-inside-work-tree", check=False)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise RuntimeError(f"not a Git worktree: {repo}")
    top = Path(run(repo, "git", "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != repo:
        raise RuntimeError(f"repository argument must be the worktree root: {top}")
    branch = run(repo, "git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch in FORBIDDEN_BRANCHES:
        raise RuntimeError(f"refusing to port on forbidden branch: {branch}")
    if branch != LANDING_BRANCH:
        raise RuntimeError(
            f"landing branch mismatch: expected {LANDING_BRANCH}, found {branch}"
        )
    head = run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    if head != LANDING_SHA:
        raise RuntimeError(f"landing SHA mismatch: expected {LANDING_SHA}, found {head}")
    ancestor = run(
        repo, "git", "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False
    )
    if ancestor.returncode != 0:
        raise RuntimeError("origin/main is not an ancestor of HEAD")
    # Parallel campaigns may dirty unrelated paths. Refuse only if this tree
    # is already ported or a sealed/denied path is missing its pre-port source.
    if (repo / "environment/program-execution/peer_execution/models.py").is_file():
        raise RuntimeError("peer_execution/models.py already exists; refuse re-port")
    if not (repo / "environment/program-execution/adapters/common").exists():
        raise RuntimeError("adapters/common missing; refuse port")
    if not (repo / OLD_AUTONOMY).exists():
        raise RuntimeError(f"{OLD_AUTONOMY} missing; refuse port")


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
            raise RuntimeError(
                f"overlay symlinks are forbidden: {source.relative_to(overlay)}"
            )
        relative = source.relative_to(overlay)
        rel_posix = relative.as_posix()
        if rel_posix in OVERLAY_SKIP or rel_posix in ADDITIVE_ONLY_ROOTS:
            continue
        if rel_posix.startswith("environment/program-execution/core/"):
            continue
        target = _safe_repo_target(repo, relative)
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def patch_peer_execution_base(repo: Path) -> None:
    path = _require_regular_file(
        repo, "environment/program-execution/peer_execution/base.py"
    )
    text = path.read_text(encoding="utf-8")
    old = "SchemaRegistry(Path(__file__).resolve().parents[2])"
    new = "SchemaRegistry(Path(__file__).resolve().parents[1])"
    if old not in text:
        raise RuntimeError("peer_execution/base.py schema-root anchor not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_makefile_additive(repo: Path) -> None:
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
    old_autonomy = (
        "python3 environment/agents/adapters/claude-code/autonomy/validate_autonomy.py"
    )
    new_autonomy = (
        "python3 environment/program-execution/peer_execution/autonomy/validate_autonomy.py"
    )
    if old_autonomy in text:
        text = text.replace(old_autonomy, new_autonomy)
    elif new_autonomy not in text:
        raise RuntimeError("Makefile autonomy-validate path anchor missing")
    path.write_text(text, encoding="utf-8")


def patch_conftest_additive(repo: Path) -> None:
    path = _require_regular_file(repo, "conftest.py")
    text = path.read_text(encoding="utf-8")
    entry = '"environment/program-execution/peer_execution"'
    if entry in text:
        return
    needle = "collect_ignore = ["
    if needle not in text:
        raise RuntimeError("conftest.py collect_ignore anchor missing")
    text = text.replace(
        needle,
        needle + "\n    " + entry + ",",
        1,
    )
    path.write_text(text, encoding="utf-8")


def patch_canonical_law_additive(repo: Path) -> None:
    path = _require_regular_file(repo, "CANONICAL_LAW.md")
    text = path.read_text(encoding="utf-8")
    law_row = (
        "| **Peer Execution thin-adapter law** | "
        "`environment/contracts/execution/PEER_EXECUTION_THIN_ADAPTER_LAW.yaml` | "
        "Binding provider-neutral execution architecture; validate via "
        "`make peer-execution-conformance` |"
    )
    if law_row in text:
        return
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
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def patch_agents_additive(repo: Path) -> None:
    path = _require_regular_file(repo, "AGENTS.md")
    text = path.read_text(encoding="utf-8")
    marker = "<!-- PEER_EXECUTION_CORE_RUNTIME_V1 -->"
    if marker in text:
        return
    block = (
        "\n\n"
        f"{marker}\n"
        "## Peer Execution shared runtime (2026-08-14)\n\n"
        "Bounded concurrency runtime is provider-neutral at "
        "`environment/program-execution/peer_execution/autonomy/`. "
        "Every provider binds to the same shared runtime through Program "
        "Execution; no provider owns a scheduler. Human merge only.\n"
    )
    path.write_text(text.rstrip() + block, encoding="utf-8")


def _replace_required(path: Path, old: str, new: str, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing symlinked doctrine write: {path}")
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"active-doctrine migration anchor missing: {label}: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_execution_template(repo: Path) -> None:
    template = _require_regular_file(
        repo,
        "environment/contracts/execution/templates/"
        "canonical.template.executable_plan.v1.plan.md",
    )
    replacements = (
        (
            "PE adapter (Cursor: cursor-foreground | cursor-background;\n"
            "            Claude: claude-code-bounded-autonomy)",
            "Peer Execution Core -> thin provider\n"
            "  (Cursor: cursor-foreground | cursor-background;\n"
            "   Claude: claude-code-direct)",
            "executable plan provider path",
        ),
        (
            "| repository implementation | `claude-code-bounded-autonomy` → "
            "`cursor-background` → `cursor-foreground` |",
            "| repository implementation | `claude-code-direct` → "
            "`cursor-background` → `cursor-foreground` |",
            "executable plan routing",
        ),
        (
            "  adapter_id: cursor-foreground    # or routed adapter",
            "  provider_ref: cursor-foreground  # or routed thin provider\n"
            "  execution_profile_ref: worker-default",
            "executable plan binding fields",
        ),
    )
    for old, new, label in replacements:
        _replace_required(template, old, new, label)


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
    if "## 2026-08-13 supersession note" in text or "## 2026-08-12 supersession note" in text:
        return
    note = (
        "\n\n## 2026-08-13 supersession note\n\n"
        "Shared bounded-autonomy runtime home moves to "
        "`environment/program-execution/peer_execution/autonomy/` "
        "(see ADR-0017 and ADR-0021). This ADR keeps its title and historical "
        "Claude Code concurrent-autonomy decision. Do not retitle this file.\n"
    )
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
        if not matching:
            continue
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
            raise RuntimeError(
                f"index regeneration failed ({relative}): {result.stderr}"
            )


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
    check_paths = ACTIVE_AUTONOMY_REFERENCE_PATHS + (
        "Makefile",
        "environment/agents/PEER_EXECUTION.md",
    )
    for relative in check_paths:
        path = repo / relative
        if not path.is_file():
            continue
        if OLD_AUTONOMY in path.read_text(encoding="utf-8"):
            stale.append(relative)
    if stale:
        raise RuntimeError(f"active legacy autonomy references remain: {stale}")


def _apply_mutations(repo: Path, overlay: Path) -> None:
    git_mv(
        repo,
        "environment/program-execution/adapters/common",
        "environment/program-execution/peer_execution",
    )
    git_mv(repo, OLD_AUTONOMY, NEW_AUTONOMY)
    old_meta = (
        "environment/contracts/autonomy/meta/"
        "claude-code-bounded-autonomy-scheduler.meta.md"
    )
    new_meta = (
        "environment/contracts/autonomy/meta/"
        "peer-execution-bounded-autonomy-runtime.meta.md"
    )
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
    patch_peer_execution_base(repo)
    patch_makefile_additive(repo)
    patch_conftest_additive(repo)
    patch_canonical_law_additive(repo)
    patch_agents_additive(repo)
    patch_execution_template(repo)
    remove_legacy_bounded_provider_references(repo)
    append_supersession_note(repo)
    regenerate_generated_indexes(repo)
    assert_active_autonomy_refs_migrated(repo)
    regenerate_manifest(repo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="Cursor-Governance landing-branch worktree")
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    pack_root = Path(__file__).resolve().parents[1]
    overlay = pack_root / "repo_overlay"
    require_landing_base(repo)
    run(
        repo,
        "git",
        "checkout",
        "HEAD",
        "--",
        "AGENTS.md",
        "CANONICAL_LAW.md",
        "Makefile",
        "conftest.py",
    )
    _apply_mutations(repo, overlay)
    print(f"APPLIED: Peer Execution Core governed port on {LANDING_SHA}")
    print("REMOTE_MUTATION: none")
    print("NEXT: python3 <pack>/scripts/validate_applied_repo.py <repo>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
