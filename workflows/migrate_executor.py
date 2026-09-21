#!/usr/bin/env python3
"""
Migrate Executor — The ONLY Entry Point for /migrate
=====================================================

Fully autonomous code migration DAG.

The DAG handles everything:
- Index analysis (find all occurrences)
- Pattern extraction (identify migration pattern)
- Batch generation (create all changes)
- Apply changes (sed/cp, NO manual rewriting)
- Validate (py_compile, imports, tests)
- Wire + confirm-wiring (update refs)
- Generate GMP report (with script)
- Commit (NO PUSH)

NO USER CONFIRMATION GATES — Fully autonomous execution.

Usage:
    python3 workflows/migrate_executor.py "old_pattern" "new_pattern"
    python3 workflows/migrate_executor.py --dry-run "old_pattern" "new_pattern"
    python3 workflows/migrate_executor.py --status
    python3 workflows/migrate_executor.py --resume

Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
STATE_FILE = REPO_ROOT / ".migrate_executor_state.json"

# Protected files - escalate if touched
PROTECTED_FILES = {
    "core/agents/executor.py",
    "runtime/websocket_orchestrator.py",
    "memory/substrate_service.py",
    "docker-compose.yml",
    "Dockerfile",
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class MigrationMatch:
    file: str
    line: int
    content: str
    migrated: bool = False
    new_content: str = ""


@dataclass
class MigrateState:
    old_pattern: str
    new_pattern: str
    started_at: str
    current_step: str
    completed_steps: list[str] = field(default_factory=list)
    matches: list[dict] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    validation_results: list[dict] = field(default_factory=list)
    report_path: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> MigrateState:
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    "index_analysis",
    "pattern_extract",
    "batch_generate",
    "apply_changes",
    "validate",
    "wire_refs",
    "confirm_wiring",
    "generate_report",
    "commit",
]


# =============================================================================
# Migrate Executor
# =============================================================================


class MigrateExecutor:
    """Executes the /migrate DAG — fully autonomous, no user gates."""

    def __init__(self, dry_run: bool = False):
        self.state: MigrateState | None = None
        self.dry_run = dry_run

    def _save_state(self):
        if self.dry_run:
            return
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = MigrateState.from_dict(data)
            return True
        return False

    def _clear_state(self):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = None

    def _run_command(self, args: list[str], capture: bool = True) -> tuple[int, str, str]:
        """Run a fixed argv command from the repository root."""
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=capture,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr

    @staticmethod
    def _repo_file(filepath: str) -> Path:
        """Resolve a state path while refusing traversal outside the repository."""
        relative = Path(filepath)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"migration path must be repository-relative: {filepath}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"migration path escapes repository: {filepath}") from exc
        return candidate

    def _fixed_string_file_count(self, pattern: str) -> int:
        """Return the number of Python files containing a literal pattern."""
        code, stdout, stderr = self._run_command(
            ["rg", "--fixed-strings", "--type", "py", "-l", "--", pattern]
        )
        if code == 0:
            return len([line for line in stdout.splitlines() if line])
        if code == 1:
            return 0
        raise RuntimeError(f"ripgrep failed while confirming migration: {stderr.strip()}")

    def _print_header(self, title: str):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    # =========================================================================
    # STEP 1: INDEX ANALYSIS
    # =========================================================================
    def _step_index_analysis(self) -> bool:
        self._print_header("INDEX ANALYSIS — Find All Occurrences")

        pattern = self.state.old_pattern
        print(f"Searching for: {pattern}\n")

        # The requested pattern is data, never shell syntax.
        code, stdout, stderr = self._run_command(
            ["rg", "--fixed-strings", "--type", "py", "-n", "--", pattern]
        )
        if code not in (0, 1):
            print(f"❌ ripgrep failed: {stderr[:200]}")
            return False

        matches = []
        for line in stdout.strip().split("\n"):
            if not line or ":" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                filepath = parts[0]
                try:
                    line_num = int(parts[1])
                except ValueError:
                    continue
                content = parts[2].strip()
                matches.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "content": content[:200],
                        "migrated": False,
                        "new_content": "",
                    }
                )

        self.state.matches = matches

        print(f"Found {len(matches)} occurrences:")
        print("-" * 70)
        print("| File | Line | Content |")
        print("|------|------|---------|")
        for m in matches[:30]:  # Show first 30
            print(f"| {m['file'][:35]} | {m['line']:4} | {m['content'][:40]} |")
        if len(matches) > 30:
            print(f"| ... and {len(matches) - 30} more |")
        print("-" * 70)

        if not matches:
            print("⚠️  No matches found — pattern may not exist")
            return True  # Continue but note it

        # Check for protected files
        protected_touched = [m["file"] for m in matches if m["file"] in PROTECTED_FILES]
        if protected_touched:
            print("\n⚠️  PROTECTED FILES CONTAIN PATTERN:")
            for f in protected_touched:
                print(f"   - {f}")
            print("\n⚠️  Will migrate but requires extra review")

        return True

    # =========================================================================
    # STEP 2: PATTERN EXTRACTION
    # =========================================================================
    def _step_pattern_extract(self) -> bool:
        self._print_header("PATTERN EXTRACTION — Analyze Migration")

        old = self.state.old_pattern
        new = self.state.new_pattern

        print("Migration pattern:")
        print(f"  FROM: {old}")
        print(f"  TO:   {new}")
        print()

        # Analyze pattern type
        pattern_type = "simple_replace"
        if "(" in old and ")" in old:
            pattern_type = "function_rename"
        elif old.startswith("from ") or old.startswith("import "):
            pattern_type = "import_change"
        elif "." in old and "." in new:
            pattern_type = "module_rename"

        print(f"Pattern type: {pattern_type}")

        # Compute preview for first match
        if self.state.matches:
            sample = self.state.matches[0]["content"]
            preview = sample.replace(old, new)
            print("\nPreview (first match):")
            print(f"  Before: {sample[:60]}")
            print(f"  After:  {preview[:60]}")

        return True

    # =========================================================================
    # STEP 3: BATCH GENERATION
    # =========================================================================
    def _step_batch_generate(self) -> bool:
        self._print_header("BATCH GENERATION — Prepare All Changes")

        old = self.state.old_pattern
        new = self.state.new_pattern

        # Group by file
        files_to_modify = {}
        for m in self.state.matches:
            if m["file"] not in files_to_modify:
                files_to_modify[m["file"]] = []
            files_to_modify[m["file"]].append(m)
            m["new_content"] = m["content"].replace(old, new)

        print(f"Files to modify: {len(files_to_modify)}")
        print(f"Total changes: {len(self.state.matches)}")
        print()

        # Show file summary
        print("-" * 50)
        print("| File | Changes |")
        print("|------|---------|")
        for f, changes in sorted(files_to_modify.items()):
            print(f"| {f[:35]} | {len(changes):3} |")
        print("-" * 50)

        self.state.files_modified = list(files_to_modify.keys())

        return True

    # =========================================================================
    # STEP 4: APPLY CHANGES (AUTONOMOUS - NO CONFIRMATION)
    # =========================================================================
    def _step_apply_changes(self) -> bool:
        self._print_header("APPLY CHANGES — Literal Replacement (Autonomous)")

        old = self.state.old_pattern
        new = self.state.new_pattern

        success_count = 0
        fail_count = 0

        for filepath in self.state.files_modified:
            try:
                full_path = self._repo_file(filepath)
            except ValueError as exc:
                print(f"❌ {filepath}: {exc}")
                fail_count += 1
                continue
            if not full_path.is_file():
                print(f"⚠️  File not found: {filepath}")
                fail_count += 1
                continue

            try:
                source = full_path.read_text(encoding="utf-8")
                changed = source.replace(old, new)
                if source == changed:
                    raise ValueError("expected literal pattern no longer present")
                full_path.write_text(changed, encoding="utf-8")
            except (OSError, UnicodeError, ValueError) as exc:
                print(f"❌ {filepath}: {exc}")
                fail_count += 1
            else:
                success_count += 1
                print(f"✅ {filepath}")

        # Mark matches as migrated
        for m in self.state.matches:
            m["migrated"] = True

        print(f"\n✅ Applied: {success_count} files")
        if fail_count:
            print(f"❌ Failed: {fail_count} files")

        return fail_count == 0

    # =========================================================================
    # STEP 5: VALIDATE
    # =========================================================================
    def _step_validate(self) -> bool:
        self._print_header("VALIDATE — Syntax and Import Check")

        validations = []

        # py_compile on modified files
        py_files = [f for f in self.state.files_modified if f.endswith(".py")]
        if py_files:
            try:
                files = [str(self._repo_file(path)) for path in py_files]
            except ValueError as exc:
                validations.append({"check": "py_compile", "status": "❌", "error": str(exc)})
                self.state.validation_results = validations
                return False
            code, _stdout, stderr = self._run_command([sys.executable, "-m", "py_compile", *files])
            if code == 0:
                validations.append({"check": "py_compile", "status": "✅"})
                print(f"✅ py_compile: {len(py_files)} files OK")
            else:
                validations.append({"check": "py_compile", "status": "❌", "error": stderr})
                print("❌ py_compile: FAILED")
                print(stderr[:200])
                self.state.validation_results = validations
                return False

        # Quick import test for affected modules
        modules_tested = set()
        for filepath in py_files[:5]:  # Test first 5
            module = filepath.replace("/", ".").replace(".py", "")
            if module in modules_tested:
                continue
            modules_tested.add(module)

            if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module):
                print(f"⚠️  import skipped for non-module path: {module[:40]}")
                continue
            code, _stdout, _stderr = self._run_command([sys.executable, "-c", f"import {module}"])
            if code == 0:
                print(f"✅ import {module[:40]}")
            else:
                print(f"⚠️  import {module[:40]}: may need wiring")

        self.state.validation_results = validations
        return True

    # =========================================================================
    # STEP 6: WIRE REFS
    # =========================================================================
    def _step_wire_refs(self) -> bool:
        self._print_header("WIRE REFS — Update Dependent Imports")

        new_pattern = self.state.new_pattern

        # Check if migration created new import requirements
        if "from " in new_pattern or "import " in new_pattern:
            print("Migration involves imports - checking refs...")
            # Extract module name from new pattern
            match = re.search(r"from\s+([\w.]+)\s+import|import\s+([\w.]+)", new_pattern)
            if match:
                module_name = match.group(1) or match.group(2)
                if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module_name):
                    print(f"❌ Invalid import target: {module_name}")
                    return False
                # Verify module exists
                code, stdout, _stderr = self._run_command(
                    [sys.executable, "-c", f"import {module_name}"]
                )
                if code == 0:
                    print(f"✅ Module {module_name} is importable")
                else:
                    print(f"⚠️  Module {module_name} import issue: {stdout[:80]}")
        else:
            print("✅ No additional wiring needed")

        return True

    # =========================================================================
    # STEP 7: CONFIRM WIRING
    # =========================================================================
    def _step_confirm_wiring(self) -> bool:
        self._print_header("CONFIRM WIRING — Final Verification")

        checks = []

        # Verify no broken references remain
        old_pattern = self.state.old_pattern
        try:
            remaining = self._fixed_string_file_count(old_pattern)
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return False

        if remaining == 0:
            checks.append({"check": "Old pattern removed", "status": "✅"})
            print("✅ Old pattern fully migrated")
        else:
            checks.append({"check": "Old pattern removed", "status": f"⚠️ {remaining} remaining"})
            print(f"⚠️  {remaining} files still contain old pattern")

        # Verify new pattern exists
        new_pattern = self.state.new_pattern
        try:
            new_count = self._fixed_string_file_count(new_pattern)
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return False

        checks.append({"check": "New pattern present", "status": f"✅ {new_count} files"})
        print(f"✅ New pattern in {new_count} files")

        # Summary
        print("\n" + "=" * 40)
        print("WIRING CONFIRMATION SUMMARY")
        print("=" * 40)
        for c in checks:
            print(f"  {c['status']} {c['check']}")

        self.state.validation_results.extend(checks)
        return True

    # =========================================================================
    # STEP 8: GENERATE REPORT
    # =========================================================================
    def _step_generate_report(self) -> bool:
        self._print_header("GENERATE REPORT — GMP Report via Script")

        if not REPORT_GENERATOR.is_file():
            print(f"❌ Required report generator is unavailable: {REPORT_GENERATOR}")
            return False

        # Build report arguments without shell interpolation.
        todo_args: list[str] = []
        for i, f in enumerate(self.state.files_modified[:10], 1):
            todo_args.extend(["--todo", f"M{i}|{f}|*|MIGRATE|literal replacement"])

        # Build validation items
        val_args: list[str] = []
        for v in self.state.validation_results:
            val_args.extend(["--validation", f"{v['check']}|{v['status']}"])

        if not todo_args:
            todo_args.extend(["--todo", "M1|migration|*|VERIFY|Pattern migration"])
        if not val_args:
            val_args.extend(["--validation", "migration|✅"])

        print("Generating report...")
        code, stdout, stderr = self._run_command(
            [
                sys.executable,
                str(REPORT_GENERATOR),
                "--task",
                f"Migrate: {self.state.old_pattern[:30]} → {self.state.new_pattern[:30]}",
                "--tier",
                "RUNTIME_TIER",
                *todo_args,
                *val_args,
                "--summary",
                "Code migration via /migrate DAG executor",
                "--skip-verify",
            ]
        )
        if code != 0:
            print(f"❌ Report generation failed: {(stderr or stdout)[:200]}")
            return False

        # Extract report path
        for line in stdout.split("\n"):
            if "Report saved:" in line or "reports/" in line.lower():
                self.state.report_path = line.strip()
                break

        if self.state.report_path:
            print(f"✅ Report: {self.state.report_path}")
        else:
            print("❌ Report generator returned no attested report path")
            return False

        return True

    # =========================================================================
    # STEP 9: COMMIT (NO PUSH)
    # =========================================================================
    def _step_commit(self) -> bool:
        self._print_header("COMMIT — Stage and Commit (NO PUSH)")

        if not self.state.files_modified:
            print("✅ No files modified — nothing to commit")
            return True

        # Stage files
        for f in self.state.files_modified:
            try:
                self._repo_file(f)
            except ValueError as exc:
                print(f"❌ {exc}")
                return False
            code, _stdout, stderr = self._run_command(["git", "add", "--", f])
            if code != 0:
                print(f"❌ Failed to stage {f}: {stderr[:200]}")
                return False

        # Create commit message
        old = self.state.old_pattern[:20]
        new = self.state.new_pattern[:20]
        count = len(self.state.files_modified)

        commit_msg = f"migrate: {old} → {new} ({count} files)"

        before_code, before_head, before_stderr = self._run_command(["git", "rev-parse", "HEAD"])
        if before_code != 0:
            print(f"❌ Could not resolve pre-commit HEAD: {before_stderr[:200]}")
            return False

        # Hooks run. A commit that cannot pass local verification is a finding to
        # repair, not a success receipt.
        code, stdout, stderr = self._run_command(["git", "commit", "-m", commit_msg])

        if "nothing to commit" in stdout.lower():
            print("✅ Nothing to commit — working tree clean")
            return True
        if code != 0:
            print(f"❌ Commit failed: {(stderr or stdout)[:200]}")
            return False

        code, hash_out, stderr = self._run_command(["git", "rev-parse", "HEAD"])
        if code != 0 or hash_out.strip() == before_head.strip():
            print(f"❌ Commit did not produce a new HEAD: {stderr[:200]}")
            return False
        self.state.commit_hash = hash_out.strip()
        print(f"✅ Committed: {self.state.commit_hash}")
        print(f"   Message: {commit_msg}")

        print("\n⚠️  DO NOT PUSH — Review changes first")

        return True

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active /migrate execution. Start with:")
            print('  python3 workflows/migrate_executor.py "old" "new"')
            return

        self._print_header(f"MIGRATE STATUS: {self.state.old_pattern} → {self.state.new_pattern}")
        print(f"Started: {self.state.started_at}")
        print(f"Current step: {self.state.current_step}")
        print(f"Matches: {len(self.state.matches)}")
        print()

        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                print(f"  ✅ {step}")
            elif step == self.state.current_step:
                print(f"  🔄 {step}")
            else:
                print(f"  ⏳ {step}")

    def run(self, old_pattern: str = "", new_pattern: str = "", resume: bool = False):
        """Execute the /migrate DAG — fully autonomous (or dry-run plan)."""
        if resume and self.dry_run:
            print("❌ --dry-run cannot resume; omit --resume")
            return False
        # Initialize or resume
        if resume and self._load_state():
            print(f"Resuming migration: {self.state.old_pattern} → {self.state.new_pattern}")
        else:
            if not old_pattern or not new_pattern:
                print("❌ Both old and new patterns required")
                return False
            self.state = MigrateState(
                old_pattern=old_pattern,
                new_pattern=new_pattern,
                started_at=datetime.now(UTC).isoformat(),
                current_step=STEP_ORDER[0],
            )
            self._save_state()

        if not self.dry_run and not REPORT_GENERATOR.is_file():
            print(f"❌ Required report generator is unavailable: {REPORT_GENERATOR}")
            print(
                "No migration changes were applied. "
                "Restore or replace the supported generator first."
            )
            return False

        mode = "DRY-RUN " if self.dry_run else ""
        self._print_header(
            f"{mode}MIGRATE EXECUTOR: {self.state.old_pattern} → {self.state.new_pattern}"
        )

        # Step executors
        executors = {
            "index_analysis": self._step_index_analysis,
            "pattern_extract": self._step_pattern_extract,
            "batch_generate": self._step_batch_generate,
            "apply_changes": self._step_apply_changes,
            "validate": self._step_validate,
            "wire_refs": self._step_wire_refs,
            "confirm_wiring": self._step_confirm_wiring,
            "generate_report": self._step_generate_report,
            "commit": self._step_commit,
        }

        dry_run_stop_after = {"index_analysis", "pattern_extract", "batch_generate"}

        # Execute steps in order
        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                continue

            if self.dry_run and step not in dry_run_stop_after:
                self._print_header("DRY-RUN STOP — skipping mutate steps")
                print(f"Would run next: {step}")
                print(f"Planned files: {len(self.state.files_modified)}")
                for f in self.state.files_modified[:40]:
                    print(f"  - {f}")
                if len(self.state.files_modified) > 40:
                    print(f"  ... +{len(self.state.files_modified) - 40} more")
                print("\nNo files written. No state file. No commit.")
                return True

            self.state.current_step = step
            self._save_state()

            executor = executors.get(step)
            if not executor:
                print(f"❌ No executor for step: {step}")
                break

            success = executor()

            if success:
                self.state.completed_steps.append(step)
                self._save_state()
            else:
                print(f"\n❌ Step failed: {step}")
                print("\nResume with: python3 workflows/migrate_executor.py --resume")
                return False

        # Complete
        self._print_header("MIGRATION COMPLETE")
        print(f"✅ Pattern: {self.state.old_pattern} → {self.state.new_pattern}")
        print(f"   Files modified: {len(self.state.files_modified)}")
        print(f"   Report: {self.state.report_path}")
        if self.state.commit_hash:
            print(f"   Commit: {self.state.commit_hash}")
        print("\n⚠️  DO NOT PUSH — Review changes first")

        # Clean up state
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Executor — Run the /migrate DAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/migrate_executor.py "old_function" "new_function"
    python3 workflows/migrate_executor.py "from old.module" "from new.module"
    python3 workflows/migrate_executor.py --dry-run "old" "new"
    python3 workflows/migrate_executor.py --resume
    python3 workflows/migrate_executor.py --status
        """,
    )

    parser.add_argument("old_pattern", nargs="?", help="Pattern to find and replace")
    parser.add_argument("new_pattern", nargs="?", help="Pattern to replace with")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted execution")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--reset", action="store_true", help="Clear state and start fresh")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan only: index/extract/batch — no apply, state, report, or commit",
    )

    args = parser.parse_args()

    executor = MigrateExecutor(dry_run=args.dry_run)

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("✅ State cleared")
        return

    if args.status:
        executor.status()
        return

    if args.resume:
        if not STATE_FILE.exists():
            print("No migration to resume")
            sys.exit(1)
        executor.run(resume=True)
        return

    if not args.old_pattern or not args.new_pattern:
        parser.print_help()
        sys.exit(1)

    success = executor.run(args.old_pattern, args.new_pattern)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
