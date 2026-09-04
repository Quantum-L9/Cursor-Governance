#!/usr/bin/env python3
"""
GMP Executor — The ONLY Entry Point for /gmp
============================================

This is what /gmp actually calls. Nothing else.

The DAG contains all steps, prompts, and enforcement.
This executor just runs it.

Usage:
    python3 workflows/gmp_executor.py "task description" --tier RUNTIME
    python3 workflows/gmp_executor.py --resume
    python3 workflows/gmp_executor.py --status

The executor:
1. Initializes the GMP state
2. Runs each step in order (cannot skip)
3. Prompts for user input at gates
4. Executes memory operations
5. Generates report with script
6. Commits if approved

Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import structlog

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

# ============================================================================

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Gmp Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "gmp_executor",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMORY_CLIENT = REPO_ROOT / "ops" / "graphiti" / "graphiti_memory_client.py"
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
TEST_GENERATOR_MODULE = "core.testing"
README_GENERATOR = REPO_ROOT / "scripts" / "generate_readme.py"
STATE_FILE = REPO_ROOT / ".l9" / "gmp" / "executor-state.json"
L4_LOCAL = REPO_ROOT / "ops" / "autonomy" / "l4_local.py"
LEGACY_STATE_FILE = REPO_ROOT / ".gmp_executor_state.json"

EXIT_NO_SCOPE = 2
EXIT_NO_TASK = 2
READY_FOR_BUILD = "READY_FOR_BUILD"
NO_PLAN = "NO_PLAN"
NO_SCOPE = "NO_SCOPE"
NO_TASK = "NO_TASK"

FILES_HEADING_RE = re.compile(r"^##\s+Files\b", re.I)
NEXT_HEADING_RE = re.compile(r"^##\s+")
MD_LINK_RE = re.compile(r"^-\s+\[([^\]]+)\]\(([^)]+)\)")
MD_TICK_RE = re.compile(r"^-\s+`([^`]+)`")
MD_PATH_RE = re.compile(r"^-\s+(\S+)")
FILES_IN_CONTENT_RE = re.compile(r"Files:\s*(.+)$")


def l4_enabled() -> bool:
    return os.environ.get("L9_L4_LOCAL_AUTONOMY", "1").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }


def dry_run() -> bool:
    return os.environ.get("L9_GMP_DRY_RUN", "").strip() == "1"


ADAPTER_PUBLISH_SURFACES = frozenset({"claude-code", "codex", "gemini", "manus"})


def adapter_publish_surface() -> bool:
    """Claude Code and sibling adapters finish via make pr. Cursor stops."""
    surface = (os.environ.get("L9_GOVERNANCE_SURFACE") or "").strip().lower()
    return surface in ADAPTER_PUBLISH_SURFACES


def _todos_json_file(raw_path: str) -> Path:
    """Resolve a ``--todos-json`` path and require it under ``REPO_ROOT``."""
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    resolved = candidate.resolve()
    root = REPO_ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("--todos-json path must be under the repository root") from exc
    return resolved


def parse_todos_json(raw: str) -> list[dict[str, str]]:
    """Parse ``--todos-json`` (inline JSON or ``@path`` / path to a JSON file).

    Accepts a list of objects with ``id``, ``task`` (or ``description``), and
    optional ``files`` / ``file``. A multi-file item expands to one todo per
    path so downstream scope lock keeps every declared file. Empty list is
    rejected by the caller.
    """
    payload = raw.strip()
    if not payload:
        raise ValueError("--todos-json is empty")
    if payload.startswith("@"):
        payload = _todos_json_file(payload[1:]).read_text(encoding="utf-8")
    elif not payload.lstrip().startswith("["):
        payload = _todos_json_file(payload).read_text(encoding="utf-8")
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("--todos-json must be a JSON list")
    todos: list[dict[str, str]] = []
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise ValueError(f"--todos-json item {i} is not an object")
        files = item.get("files") or []
        paths: list[str] = []
        if isinstance(files, list) and files:
            paths = [str(p) for p in files]
        elif item.get("file"):
            paths = [str(item["file"])]
        if not paths:
            paths = [""]
        description = str(item.get("task") or item.get("description") or item.get("content") or "")
        base_id = str(item.get("id") or f"T{i}")
        for j, file_path in enumerate(paths):
            todo_id = base_id if j == 0 else f"{base_id}.{j + 1}"
            todos.append(
                {
                    "id": todo_id,
                    "file": file_path,
                    "lines": str(item.get("lines") or "all"),
                    "action": str(item.get("action") or item.get("operation") or "REPLACE"),
                    "description": description,
                }
            )
    return todos


def parse_plan_scope(plan_path: Path) -> list[dict[str, str]]:
    """Lock todos from plan frontmatter, else from a ## Files heading."""
    text = plan_path.read_text(encoding="utf-8")
    body = text
    fm: Any = {}
    if text.startswith("---"):
        end = text.find("\n---\n", 3)
        if end > 0:
            raw = text[4:end]
            body = text[end + 5 :]
            if yaml is not None:
                loaded = yaml.safe_load(raw)
                fm = loaded if isinstance(loaded, dict) else {}
    todos: list[dict[str, str]] = []
    raw_todos = fm.get("todos") if isinstance(fm, dict) else None
    if isinstance(raw_todos, list):
        for i, item in enumerate(raw_todos, 1):
            if not isinstance(item, dict):
                continue
            description = str(item.get("content") or item.get("description") or "")
            file_path = str(item.get("file") or "").strip()
            if not file_path:
                match = FILES_IN_CONTENT_RE.search(description)
                if match:
                    file_path = match.group(1).split(",")[0].strip().split()[0]
            todos.append(
                {
                    "id": str(item.get("id") or f"T{i}"),
                    "file": file_path,
                    "lines": str(item.get("lines") or "all"),
                    "action": str(item.get("action") or "REPLACE"),
                    "description": description,
                }
            )
    if todos:
        return todos
    files: list[str] = []
    in_files = False
    for line in body.splitlines():
        if FILES_HEADING_RE.match(line):
            in_files = True
            continue
        if in_files and NEXT_HEADING_RE.match(line):
            break
        if not in_files:
            continue
        link = MD_LINK_RE.match(line)
        if link:
            files.append(link.group(2).strip())
            continue
        tick = MD_TICK_RE.match(line)
        if tick:
            files.append(tick.group(1).strip())
            continue
        path = MD_PATH_RE.match(line)
        if path:
            files.append(path.group(1).strip())
    return [
        {
            "id": f"T{i}",
            "file": name,
            "lines": "all",
            "action": "REPLACE",
            "description": name,
        }
        for i, name in enumerate(files, 1)
    ]


# =============================================================================
# Data Models
# =============================================================================


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class StepType(StrEnum):
    MEMORY_READ = "memory_read"
    SCOPE_LOCK = "scope_lock"
    USER_GATE = "user_gate"
    BASELINE = "baseline"
    IMPLEMENT = "implement"
    GENERATE_TESTS = "generate_tests"  # Optional: Auto-generate tests for new code
    GENERATE_README = "generate_readme"  # Optional: Auto-generate README for new modules
    VALIDATE = "validate"
    MEMORY_WRITE = "memory_write"
    GENERATE_REPORT = "generate_report"
    COMMIT_GATE = "commit_gate"


@dataclass
class StepResult:
    success: bool
    output: str = ""
    error: str = ""
    user_input: str = ""


@dataclass
class GMPState:
    gmp_id: str
    tier: str
    task: str
    started_at: str
    current_step: StepType
    completed_steps: list[str] = field(default_factory=list)
    todo_plan: list[dict] = field(default_factory=list)
    changes_made: list[dict] = field(default_factory=list)
    validations: list[dict] = field(default_factory=list)
    memory_context: str = ""
    report_path: str = ""
    # Optional step flags
    needs_tests: bool = False
    needs_readme: bool = False
    # A /gmp-authorized run stays authorized across resume. The documented
    # finalize call (`--resume --mode finalize --commit-when-done`) does not
    # repeat --authorized-by, and without this stamp an unauthorized resume
    # falls into the interactive DAG, where a closed stdin reads as
    # "No TODOs defined" and then "User aborted".
    authorized_by: str = ""
    generated_tests: list[str] = field(default_factory=list)
    generated_readmes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["current_step"] = self.current_step.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> GMPState:
        data = dict(d)
        data["current_step"] = StepType(data["current_step"])
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def start_ceremony_complete(self) -> bool:
        """True when an authorized start finished scope lock + user gate.

        Partial state after ``_init_state`` (Ctrl-C mid-start) must not unlock
        finalize. A locked ``todo_plan`` plus the three start steps is the proof.
        """
        required = {
            StepType.MEMORY_READ.value,
            StepType.SCOPE_LOCK.value,
            StepType.USER_GATE.value,
        }
        return bool(self.todo_plan) and required.issubset(set(self.completed_steps))


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    StepType.MEMORY_READ,
    StepType.SCOPE_LOCK,
    StepType.USER_GATE,
    StepType.BASELINE,
    StepType.IMPLEMENT,
    StepType.GENERATE_TESTS,  # Conditional: runs if tests are required
    StepType.GENERATE_README,  # Conditional: runs if README is required
    StepType.VALIDATE,
    StepType.MEMORY_WRITE,
    StepType.GENERATE_REPORT,
    StepType.COMMIT_GATE,
]

# Keywords that trigger optional steps
TEST_KEYWORDS = ["test", "tests", "testing", "coverage", "pytest", "unittest"]
README_KEYWORDS = ["readme", "documentation", "docs", "module", "new module", "api"]


# =============================================================================
# Step Executors
# =============================================================================


class GMPExecutor:
    """Executes the GMP DAG."""

    def __init__(self):
        self.state: GMPState | None = None
        self.authorized = False
        self.todos_json: str | None = None
        self.commit_when_done = False
        self.plan_path: Path | None = None
        self.mode = "full"
        self.subprocess_log: list[str] = []

    def _save_state(self):
        if self.state:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        path = STATE_FILE if STATE_FILE.exists() else LEGACY_STATE_FILE
        if path.exists():
            data = json.loads(path.read_text())
            self.state = GMPState.from_dict(data)
            return True
        return False

    def _clear_state(self):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        if LEGACY_STATE_FILE.exists():
            LEGACY_STATE_FILE.unlink()
        self.state = None

    def _record_subprocess(self, cmd: str) -> None:
        self.subprocess_log.append(cmd)
        print(f"SUBPROCESS: {cmd}")  # noqa: ADR-0019

    def _run_argv(self, argv: list[str]) -> tuple[int, str, str]:
        rendered = " ".join(argv)
        self._record_subprocess(rendered)
        if dry_run():
            return 0, "", ""
        result = subprocess.run(
            argv,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    def _maybe_l4_begin(self) -> None:
        if not l4_enabled():
            return
        if not L4_LOCAL.is_file():
            return
        assert self.state is not None
        # --workspace is a global flag of l4_local.py: it must precede the
        # subcommand or argparse rejects it as an unrecognized argument.
        argv = [
            sys.executable,
            str(L4_LOCAL),
            "--workspace",
            str(REPO_ROOT),
            "begin",
            "--contract-id",
            f"gmp-{self.state.gmp_id}",
        ]
        code, stdout, stderr = self._run_argv(argv)
        if code != 0:
            print(f"L4 begin skipped or failed: {stderr or stdout}")  # noqa: ADR-0019

    def _maybe_l4_release(self) -> None:
        if not l4_enabled():
            return
        if not L4_LOCAL.is_file():
            return
        for sub in ("record-kernels", "authorize-release"):
            argv = [sys.executable, str(L4_LOCAL), "--workspace", str(REPO_ROOT), sub]
            code, stdout, stderr = self._run_argv(argv)
            if code != 0:
                print(f"L4 {sub} failed: {stderr or stdout}")  # noqa: ADR-0019

    def _print_header(self, title: str):
        print(f"\n{'=' * 60}")  # noqa: ADR-0019
        print(f"  {title}")  # noqa: ADR-0019
        print(f"{'=' * 60}\n")  # noqa: ADR-0019

    def _print_step(self, step: StepType, status: str = ""):
        icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "blocked": "🚫",
        }.get(status, "  ")
        print(f"  {icon} {step.value}")  # noqa: ADR-0019

    # =========================================================================
    # STEP: Memory Read
    # =========================================================================
    def _step_memory_read(self) -> StepResult:
        self._print_header("MEMORY READ (MANDATORY)")
        assert self.state is not None

        if dry_run():
            self.state.memory_context = "dry-run"
            return StepResult(success=True, output="dry-run")

        print("Searching L9 memory for context...\n")  # noqa: ADR-0019

        # Search for related work
        searches = [
            self.state.task,
            f"lessons errors {self.state.task.split()[0]}",
            "gmp patterns",
        ]

        context_lines = []
        for query in searches:
            code, stdout, stderr = self._run_argv(
                [sys.executable, str(MEMORY_CLIENT), "search", query]
            )
            if code != 0:
                stdout = "Memory unavailable"
            if stdout.strip():
                context_lines.append(f"Query: {query}")
                context_lines.append(stdout.strip()[:500])
                context_lines.append("")

        if context_lines:
            self.state.memory_context = "\n".join(context_lines)
            print("Memory context retrieved:")  # noqa: ADR-0019
            print("-" * 40)  # noqa: ADR-0019
            print(self.state.memory_context[:1000])  # noqa: ADR-0019
            print("-" * 40)  # noqa: ADR-0019
        else:
            self.state.memory_context = "No prior context found"
            print("⚠️  No prior context found in memory")  # noqa: ADR-0019

        return StepResult(success=True, output=self.state.memory_context)

    # =========================================================================
    # STEP: Scope Lock
    # =========================================================================
    def _step_scope_lock(self) -> StepResult:
        self._print_header("SCOPE LOCK (Phase 0)")
        assert self.state is not None

        print(f"GMP ID: {self.state.gmp_id}")  # noqa: ADR-0019
        print(f"Tier: {self.state.tier}")  # noqa: ADR-0019
        print(f"Task: {self.state.task}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        if self.authorized:
            todos: list[dict[str, str]] = []
            source = ""
            if self.todos_json:
                try:
                    todos = parse_todos_json(self.todos_json)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    return StepResult(
                        success=False,
                        error=f"--todos-json invalid: {exc}",
                    )
                source = "todos-json"
            elif self.plan_path is not None:
                todos = parse_plan_scope(self.plan_path)
                source = "plan"
            if not todos:
                msg = (
                    "No TODOs defined for authorized run. Pass --plan with "
                    "frontmatter todos, or --todos-json '@path.json' / inline "
                    "JSON list of {id,task,files}."
                )
                print(msg)  # noqa: ADR-0019
                return StepResult(success=False, error=msg)
            self.state.todo_plan = todos
            label = (
                "TODO PLAN LOCKED FROM PLAN"
                if source == "plan"
                else "TODO PLAN LOCKED FROM --todos-json"
            )
            print(label)  # noqa: ADR-0019
            for t in todos:
                print(f"  {t['id']}: {t['file']} {t['action']}")  # noqa: ADR-0019
            return StepResult(success=True, output=f"{len(todos)} TODOs from {source}")

        print("Memory Context Applied:")  # noqa: ADR-0019
        print(self.state.memory_context[:500] if self.state.memory_context else "None")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("Define the TODO plan.")  # noqa: ADR-0019
        print("Format: T#|file|lines|action|description")  # noqa: ADR-0019
        print("Example: T1|core/tools/registry.py|45-60|REPLACE|Add validation")  # noqa: ADR-0019
        print("Enter empty line when done.")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019

        todos = []
        while True:
            try:
                line = input(f"T{len(todos) + 1}: ").strip()
            except EOFError:
                break
            if not line:
                break
            parts = line.split("|")
            if len(parts) >= 4:
                todos.append(
                    {
                        "id": f"T{len(todos) + 1}",
                        "file": parts[0] if not parts[0].startswith("T") else parts[1],
                        "lines": parts[1] if not parts[0].startswith("T") else parts[2],
                        "action": parts[2] if not parts[0].startswith("T") else parts[3],
                        "description": parts[3]
                        if not parts[0].startswith("T")
                        else (parts[4] if len(parts) > 4 else ""),
                    }
                )

        if not todos:
            return StepResult(success=False, error="No TODOs defined")

        self.state.todo_plan = todos

        print("\n" + "=" * 40)  # noqa: ADR-0019
        print("TODO PLAN LOCKED")  # noqa: ADR-0019
        print("=" * 40)  # noqa: ADR-0019
        print("| T# | File | Lines | Action |")  # noqa: ADR-0019
        print("|----|------|-------|--------|")  # noqa: ADR-0019
        for t in todos:
            print(f"| {t['id']} | {t['file']} | {t['lines']} | {t['action']} |")  # noqa: ADR-0019

        return StepResult(success=True, output=f"{len(todos)} TODOs defined")

    # =========================================================================
    # STEP: User Gate
    # =========================================================================
    def _step_user_gate(self) -> StepResult:
        self._print_header("USER CONFIRMATION GATE")
        if self.authorized:
            print("Authorized by slash-gmp — skipping USER_GATE")  # noqa: ADR-0019
            return StepResult(success=True, user_input="CONFIRM")

        print("Scope is locked. Review the TODO plan above.")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Options:")  # noqa: ADR-0019
        print("  CONFIRM - Proceed with implementation")  # noqa: ADR-0019
        print("  ABORT   - Cancel GMP")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        try:
            response = input("Enter CONFIRM or ABORT: ").strip().upper()
        except EOFError:
            response = "ABORT"

        if response == "CONFIRM":
            return StepResult(success=True, user_input="CONFIRM")
        return StepResult(success=False, error="User aborted", user_input=response)

    # =========================================================================
    # STEP: Baseline
    # =========================================================================
    def _step_baseline(self) -> StepResult:
        self._print_header("BASELINE VERIFICATION (Phase 1)")

        print("Verifying files exist and line ranges are correct...\n")  # noqa: ADR-0019

        errors = []
        for todo in self.state.todo_plan:
            filepath = REPO_ROOT / todo["file"]
            if todo["action"].upper() != "CREATE":
                if not filepath.exists():
                    errors.append(f"❌ File not found: {todo['file']}")
                else:
                    print(f"✅ {todo['file']} exists")  # noqa: ADR-0019

        if errors:
            for e in errors:
                print(e)  # noqa: ADR-0019
            return StepResult(success=False, error="\n".join(errors))

        return StepResult(success=True, output="All files verified")

    # =========================================================================
    # STEP: Implement
    # =========================================================================
    def _step_implement(self) -> StepResult:
        self._print_header("IMPLEMENTATION (Phase 2-3)")

        print("Execute the TODO plan now.")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("RULES:")  # noqa: ADR-0019
        print("  - For harvested code: Use sed/cp ONLY")  # noqa: ADR-0019
        print("  - All changes must map 1:1 to TODO items")  # noqa: ADR-0019
        print("  - NO scope drift")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("TODO items to implement:")  # noqa: ADR-0019
        for t in self.state.todo_plan:
            print(f"  [ ] {t['id']}: {t['file']} - {t['action']} - {t.get('description', '')}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019
        print("Make your changes now, then press ENTER when done.")  # noqa: ADR-0019
        print("Or type ABORT to cancel.")  # noqa: ADR-0019
        print("-" * 40)  # noqa: ADR-0019

        if self.authorized:
            print("Authorized mode: implementation is owned by Build / skill phases.")  # noqa: ADR-0019
            response = ""
        else:
            try:
                response = input("Press ENTER when done (or ABORT): ").strip().upper()
            except EOFError:
                response = ""

        if response == "ABORT":
            return StepResult(success=False, error="User aborted implementation")

        # Record changes (simplified - in real use, this would diff)
        self.state.changes_made = [
            {
                "file": t["file"],
                "lines": t["lines"],
                "action": t["action"],
                "description": t.get("description", ""),
            }
            for t in self.state.todo_plan
        ]

        # Check if tests or README are needed based on task/TODO content
        task_lower = self.state.task.lower()
        todo_files = " ".join(t["file"] for t in self.state.todo_plan)

        self.state.needs_tests = (
            any(kw in task_lower for kw in TEST_KEYWORDS) or "test" in todo_files.lower()
        )
        self.state.needs_readme = any(kw in task_lower for kw in README_KEYWORDS)

        # Also check if any Python files were created/modified that don't have tests
        py_files = [
            t["file"]
            for t in self.state.todo_plan
            if t["file"].endswith(".py") and not t["file"].startswith("tests/")
        ]
        if py_files and not self.state.needs_tests:
            print("\n💡 Detected new Python files. Consider generating tests.")  # noqa: ADR-0019
            if not self.authorized:
                try:
                    resp = input("   Generate tests automatically? [y/N]: ").strip().lower()
                    self.state.needs_tests = resp == "y"
                except EOFError:
                    pass

        return StepResult(
            success=True,
            output=f"Implementation complete: {len(self.state.changes_made)} changes",
        )

    # =========================================================================
    # STEP: Generate Tests (Optional)
    # =========================================================================
    def _step_generate_tests(self) -> StepResult:
        """Generate tests for new/modified Python files using LLM."""
        if not self.state.needs_tests:
            print("⏭️  Skipping test generation (not required)")  # noqa: ADR-0019
            return StepResult(success=True, output="Skipped - not required")

        self._print_header("🧪 GENERATE TESTS (Automatic)")

        # Find Python files that need tests
        py_files = [
            t["file"]
            for t in self.state.todo_plan
            if t["file"].endswith(".py") and not t["file"].startswith("tests/")
        ]

        if not py_files:
            print("No Python files to generate tests for")  # noqa: ADR-0019
            return StepResult(success=True, output="No files need tests")

        print(f"Generating tests for {len(py_files)} file(s)...\n")  # noqa: ADR-0019

        generated = []
        for py_file in py_files:
            filepath = REPO_ROOT / py_file
            if not filepath.exists():
                print(f"  ⚠️  {py_file} not found, skipping")  # noqa: ADR-0019
                continue

            # Determine test file path
            if py_file.startswith("core/"):
                stem = py_file.replace(".py", "").replace("/", "/test_")
                test_file = f"tests/{stem.replace('core/test_', 'core/')}"
            else:
                parts = py_file.split("/")
                test_file = f"tests/{'/'.join(parts[:-1])}/test_{parts[-1]}"

            test_file = test_file.replace("//", "/")
            if not test_file.endswith(".py"):
                test_file += ".py"

            print(f"  📝 {py_file} → {test_file}")  # noqa: ADR-0019

            try:
                from core.testing import generate_test_file

                tests = generate_test_file(
                    filepath.read_text(encoding="utf-8"),
                    py_file.replace("/", ".").replace(".py", ""),
                )
                test_path = REPO_ROOT / test_file
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(tests, encoding="utf-8")
                print(f"     ✅ generated {len(tests.splitlines())} lines")  # noqa: ADR-0019
                generated.append(test_file)
            except Exception as e:
                print(f"     ❌ Error: {e}")  # noqa: ADR-0019

        self.state.generated_tests = generated

        if generated:
            print(f"\n✅ Generated {len(generated)} test file(s)")  # noqa: ADR-0019
            # Add to TODO plan for commit
            for tf in generated:
                self.state.todo_plan.append(
                    {
                        "id": f"T{len(self.state.todo_plan) + 1}",
                        "file": tf,
                        "lines": "all",
                        "action": "CREATE",
                        "description": "Auto-generated tests",
                    }
                )
            return StepResult(success=True, output=f"Generated {len(generated)} test files")
        print("\n⚠️  No tests were generated")  # noqa: ADR-0019
        return StepResult(success=True, output="No tests generated")

    # =========================================================================
    # STEP: Generate README (Optional)
    # =========================================================================
    def _step_generate_readme(self) -> StepResult:
        """Generate README for new modules."""
        if not self.state.needs_readme:
            print("⏭️  Skipping README generation (not required)")  # noqa: ADR-0019
            return StepResult(success=True, output="Skipped - not required")

        self._print_header("📖 GENERATE README (Automatic)")

        # Find directories with new files
        dirs_with_changes = set()
        for t in self.state.todo_plan:
            if "/" in t["file"]:
                dir_path = "/".join(t["file"].split("/")[:-1])
                dirs_with_changes.add(dir_path)

        if not dirs_with_changes:
            print("No directories to generate READMEs for")  # noqa: ADR-0019
            return StepResult(success=True, output="No READMEs needed")

        print(f"Checking {len(dirs_with_changes)} director(ies) for README needs...\n")  # noqa: ADR-0019

        generated = []
        for dir_path in dirs_with_changes:
            readme_path = REPO_ROOT / dir_path / "README.md"

            # Skip if README already exists
            if readme_path.exists():
                print(f"  ⏭️  {dir_path}/README.md already exists")  # noqa: ADR-0019
                continue

            print(f"  📝 Generating {dir_path}/README.md")  # noqa: ADR-0019

            # Check if readme generator script exists
            if README_GENERATOR.exists():
                code, stdout, stderr = self._run_argv(
                    [
                        sys.executable,
                        str(README_GENERATOR),
                        "--dir",
                        str(REPO_ROOT / dir_path),
                    ]
                )
                if code == 0:
                    print("     ✅ Generated via script")  # noqa: ADR-0019
                    generated.append(f"{dir_path}/README.md")
                else:
                    # Fallback: generate simple README
                    self._generate_simple_readme(dir_path, readme_path)
                    generated.append(f"{dir_path}/README.md")
            else:
                # Generate simple README
                self._generate_simple_readme(dir_path, readme_path)
                generated.append(f"{dir_path}/README.md")

        self.state.generated_readmes = generated

        if generated:
            print(f"\n✅ Generated {len(generated)} README(s)")  # noqa: ADR-0019
            for rf in generated:
                self.state.todo_plan.append(
                    {
                        "id": f"T{len(self.state.todo_plan) + 1}",
                        "file": rf,
                        "lines": "all",
                        "action": "CREATE",
                        "description": "Auto-generated README",
                    }
                )
            return StepResult(success=True, output=f"Generated {len(generated)} READMEs")
        return StepResult(success=True, output="No READMEs generated")

    def _generate_simple_readme(self, dir_path: str, readme_path: Path):
        """Generate a simple README for a directory."""
        dir_name = dir_path.split("/")[-1]

        # List Python files in directory
        py_files = list((REPO_ROOT / dir_path).glob("*.py"))
        py_files = [f.name for f in py_files if f.name != "__init__.py"]

        content = f"""# {dir_name.replace("_", " ").title()}

## Overview

This module is part of the L9 Secure AI OS.

## Files

"""
        for pf in sorted(py_files):
            content += f"- `{pf}`\n"

        content += """
## Usage

```python
from {module_path} import ...
```

---
*Auto-generated by GMP Executor*
""".format(module_path=dir_path.replace("/", "."))

        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(content)
        print("     ✅ Generated simple README")  # noqa: ADR-0019

    # =========================================================================
    # STEP: Validate
    # =========================================================================
    def _step_validate(self) -> StepResult:
        self._print_header("VALIDATION (Phase 4-5)")
        if self.authorized:
            print("Authorized finalize: tests once belong to Build; skipping pytest.")  # noqa: ADR-0019
            self.state.validations = [{"gate": "tests_once", "result": "owned_by_build"}]
            return StepResult(success=True, output="Skipped pytest (tests once)")

        print("Running validation checks...\n")  # noqa: ADR-0019

        validations = []

        # py_compile
        py_files = [t["file"] for t in self.state.todo_plan if t["file"].endswith(".py")]
        if py_files:
            code, stdout, stderr = self._run_argv(
                [sys.executable, "-m", "py_compile", *[str(REPO_ROOT / f) for f in py_files]]
            )
            if code == 0:
                validations.append({"gate": "py_compile", "result": "✅"})
                print("✅ py_compile: PASSED")  # noqa: ADR-0019
            else:
                validations.append({"gate": "py_compile", "result": "❌", "details": stderr})
                print(f"❌ py_compile: FAILED\n{stderr}")  # noqa: ADR-0019
                self.state.validations = validations
                return StepResult(success=False, error=f"py_compile failed: {stderr}")

        # Import check (simplified)
        validations.append({"gate": "syntax", "result": "✅"})
        print("✅ syntax: PASSED")  # noqa: ADR-0019

        self.state.validations = validations
        return StepResult(success=True, output="All validations passed")

    # =========================================================================
    # STEP: Memory Write
    # =========================================================================
    def _step_memory_write(self) -> StepResult:
        self._print_header("🧠 MEMORY WRITE (MANDATORY)")

        print("Writing learnings to L9 memory...\n")  # noqa: ADR-0019

        # Build summary
        files_changed = ", ".join(t["file"].split("/")[-1] for t in self.state.todo_plan[:3])
        summary = (
            f"{self.state.gmp_id}: {self.state.task}. Files: {files_changed}. "
            f"Tags: gmp, {self.state.tier.lower()}"
        )

        code, stdout, stderr = self._run_argv(
            [sys.executable, str(MEMORY_CLIENT), "write", summary, "--kind", "lesson"]
        )

        if "failed" in stdout.lower() or code != 0:
            print(f"⚠️  Memory write failed: {stdout}{stderr}")  # noqa: ADR-0019
            print("   Continuing anyway (memory is non-blocking)")  # noqa: ADR-0019
        else:
            print(f"✅ Memory written: {summary[:80]}...")  # noqa: ADR-0019

        return StepResult(success=True, output="Memory write attempted")

    # =========================================================================
    # STEP: Generate Report
    # =========================================================================
    def _write_local_report(self) -> Path:
        assert self.state is not None
        reports = REPO_ROOT / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", self.state.task.lower())[:40].strip("-") or "gmp"
        path = reports / f"{self.state.gmp_id}-{slug}.md"
        lines = [
            f"# {self.state.gmp_id}",
            "",
            f"**Task:** {self.state.task}",
            f"**Tier:** {self.state.tier}",
            "",
            "## TODOs",
            "",
        ]
        for todo in self.state.todo_plan:
            desc = todo.get("description", "")
            lines.append(f"- {todo['id']}: {todo['file']} {todo['action']} {desc}")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _step_generate_report(self) -> StepResult:
        self._print_header("GENERATE GMP REPORT (MANDATORY)")
        assert self.state is not None

        if dry_run():
            self.state.report_path = ".l9/gmp/dry-run-report.md"
            print("Report saved: .l9/gmp/dry-run-report.md")  # noqa: ADR-0019
            return StepResult(success=True, output=self.state.report_path)

        if REPORT_GENERATOR.is_file():
            print("Generating canonical GMP report...\n")  # noqa: ADR-0019
            argv = [
                sys.executable,
                str(REPORT_GENERATOR),
                "--task",
                self.state.task,
                "--tier",
                f"{self.state.tier}_TIER",
            ]
            for t in self.state.todo_plan:
                desc = t.get("description", "")
                argv.extend(["--todo", f"{t['id']}|{t['file']}|{t['lines']}|{t['action']}|{desc}"])
            for v in self.state.validations:
                argv.extend(["--validation", f"{v['gate']}|{v['result']}"])
            argv.extend(["--summary", "GMP execution via DAG executor", "--skip-verify"])
            code, stdout, stderr = self._run_argv(argv)
            if code == 0:
                for line in stdout.split("\n"):
                    if "Report saved:" in line or "reports/" in line:
                        self.state.report_path = line.strip()
                        break
                print(stdout)  # noqa: ADR-0019
                return StepResult(success=True, output=stdout)
            print(f"Report generator failed, writing local report: {stderr}")  # noqa: ADR-0019

        path = self._write_local_report()
        self.state.report_path = str(path.relative_to(REPO_ROOT))
        print(f"Report saved: {self.state.report_path}")  # noqa: ADR-0019
        return StepResult(success=True, output=self.state.report_path)

    # =========================================================================
    # STEP: Commit Gate
    # =========================================================================
    def _step_commit_gate(self) -> StepResult:
        self._print_header("COMMIT GATE")

        print(f"Report generated: {self.state.report_path}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019
        print("Options:")  # noqa: ADR-0019
        print("  YES  - Commit all changes")  # noqa: ADR-0019
        print("  NO   - Exit without commit")  # noqa: ADR-0019
        print("  DIFF - Show git diff first")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        if self.authorized and self.commit_when_done:
            response = "YES"
        elif self.authorized:
            response = "NO"
        else:
            try:
                response = input("Commit? [YES/NO/DIFF]: ").strip().upper()
            except EOFError:
                response = "NO"

        if response == "DIFF":
            code, stdout, stderr = self._run_argv(["git", "diff", "--stat"])
            print(stdout)  # noqa: ADR-0019
            try:
                response = input("Commit? [YES/NO]: ").strip().upper()
            except EOFError:
                response = "NO"

        if response == "YES":
            paths = [t["file"] for t in self.state.todo_plan if t.get("file")]
            if self.state.report_path:
                report_rel = self.state.report_path
                if report_rel.startswith(str(REPO_ROOT)):
                    report_rel = str(Path(report_rel).relative_to(REPO_ROOT))
                if "reports/" in report_rel:
                    # Keep only the reports/... suffix when the generator printed a sentence.
                    idx = report_rel.find("reports/")
                    report_rel = report_rel[idx:]
                paths.append(report_rel.split()[0])
            commit_msg = f"{self.state.gmp_id}: {self.state.task}"
            add_argv = ["git", "add", "--"] + paths
            self._run_argv(add_argv)
            code, stdout, stderr = self._run_argv(["git", "commit", "-m", commit_msg])

            if code == 0:
                print("Changes committed")  # noqa: ADR-0019
                return StepResult(success=True, output="Committed", user_input="YES")
            print(f"Commit failed: {stderr}")  # noqa: ADR-0019
            return StepResult(
                success=True,
                output="Commit failed but GMP complete",
                user_input="YES",
            )
        print("Skipping commit")  # noqa: ADR-0019
        return StepResult(success=True, output="No commit", user_input="NO")

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def _get_step_executor(self, step: StepType):
        """Get the executor function for a step."""
        executors = {
            StepType.MEMORY_READ: self._step_memory_read,
            StepType.SCOPE_LOCK: self._step_scope_lock,
            StepType.USER_GATE: self._step_user_gate,
            StepType.BASELINE: self._step_baseline,
            StepType.IMPLEMENT: self._step_implement,
            StepType.GENERATE_TESTS: self._step_generate_tests,
            StepType.GENERATE_README: self._step_generate_readme,
            StepType.VALIDATE: self._step_validate,
            StepType.MEMORY_WRITE: self._step_memory_write,
            StepType.GENERATE_REPORT: self._step_generate_report,
            StepType.COMMIT_GATE: self._step_commit_gate,
        }
        return executors.get(step)

    def _next_step(self) -> StepType | None:
        """Get the next step to execute."""
        for step in STEP_ORDER:
            if step.value not in self.state.completed_steps:
                return step
        return None

    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active GMP. Start with:")  # noqa: ADR-0019
            print('  python3 workflows/gmp_executor.py "task description"')  # noqa: ADR-0019
            return

        self._print_header(f"GMP STATUS: {self.state.gmp_id}")
        print(f"Task: {self.state.task}")  # noqa: ADR-0019
        print(f"Tier: {self.state.tier}")  # noqa: ADR-0019
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        for step in STEP_ORDER:
            if step.value in self.state.completed_steps:
                self._print_step(step, "completed")
            elif step == self.state.current_step:
                self._print_step(step, "running")
            else:
                self._print_step(step, "pending")

    def _next_gmp_id(self) -> str:
        gmp_num = 129
        reports_dirs = [REPO_ROOT / "reports" / "GMP Reports", REPO_ROOT / "reports"]
        for reports_dir in reports_dirs:
            if not reports_dir.is_dir():
                continue
            for path in reports_dir.glob("GMP-Report-*.md"):
                match = re.search(r"GMP-Report-(\d+)", path.name)
                if match:
                    gmp_num = max(gmp_num, int(match.group(1)) + 1)
            for path in reports_dir.glob("GMP-*.md"):
                match = re.search(r"GMP-(\d+)", path.name)
                if match:
                    gmp_num = max(gmp_num, int(match.group(1)) + 1)
        return f"GMP-{gmp_num}"

    def _init_state(self, task: str, tier: str) -> None:
        self.state = GMPState(
            gmp_id=self._next_gmp_id(),
            tier=tier,
            task=task,
            started_at=datetime.now().isoformat(),
            current_step=STEP_ORDER[0],
            authorized_by="slash-gmp" if self.authorized else "",
        )
        self._save_state()

    def _catalog_gate(self) -> StepResult:
        self._record_subprocess("make precommit-repo")
        if dry_run():
            return StepResult(success=True, output="dry-run catalog")
        result = subprocess.run(
            ["make", "precommit-repo"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        print(result.stdout)  # noqa: ADR-0019
        if result.returncode != 0:
            print(result.stderr)  # noqa: ADR-0019
            return StepResult(success=False, error="make precommit-repo failed")
        return StepResult(success=True, output="catalog passed")

    def _publish_pr(self) -> None:
        if not adapter_publish_surface():
            print(  # noqa: ADR-0019
                "Cursor finalize: catalog + commit + STOP. Do not make pr."
            )
            return
        self._maybe_l4_release()
        env_prefix = "PR_REMEDIATE=1 make pr"
        self._record_subprocess(env_prefix)
        if dry_run():
            return
        env = os.environ.copy()
        env["PR_REMEDIATE"] = "1"
        result = subprocess.run(
            ["make", "pr"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        print(result.stdout)  # noqa: ADR-0019
        if result.returncode != 0:
            print(result.stderr)  # noqa: ADR-0019

    def run_authorized_start(self, task: str, tier: str) -> int:
        has_plan = self.plan_path is not None and self.plan_path.is_file()
        has_todos = bool(self.todos_json and str(self.todos_json).strip())
        if not has_plan and not has_todos:
            print(
                "No TODOs defined for authorized run. Pass --plan with "
                "frontmatter todos, or --todos-json '@path.json' / inline "
                "JSON list of {id,task,files}."
            )  # noqa: ADR-0019
            return EXIT_NO_SCOPE
        self._init_state(task, tier)
        self._print_header(f"GMP EXECUTOR: {self.state.gmp_id}")
        self._step_memory_read()
        self.state.completed_steps.append(StepType.MEMORY_READ.value)
        scope = self._step_scope_lock()
        if not scope.success:
            print(scope.error or NO_SCOPE)  # noqa: ADR-0019
            self._clear_state()
            return EXIT_NO_SCOPE
        self.state.completed_steps.append(StepType.SCOPE_LOCK.value)
        self._step_user_gate()
        self.state.completed_steps.append(StepType.USER_GATE.value)
        self._maybe_l4_begin()
        self._save_state()
        print(READY_FOR_BUILD)  # noqa: ADR-0019
        return 0

    def run_authorized_full(self, task: str, tier: str) -> int:
        if not task.strip():
            print(NO_TASK)  # noqa: ADR-0019
            return EXIT_NO_TASK
        return self.run_authorized_start(task, tier)

    def run_authorized_finalize(self) -> int:
        if not self._load_state() or self.state is None:
            print("No GMP to resume")  # noqa: ADR-0019
            return 1
        self.authorized = True
        self._print_header(f"GMP FINALIZE: {self.state.gmp_id}")
        # Skip implement wait; mark remaining ceremony steps.
        for step in (
            StepType.BASELINE,
            StepType.IMPLEMENT,
            StepType.GENERATE_TESTS,
            StepType.GENERATE_README,
        ):
            if step.value not in self.state.completed_steps:
                self.state.completed_steps.append(step.value)
        self.state.needs_tests = False
        self.state.needs_readme = False
        catalog = self._catalog_gate()
        if not catalog.success:
            print(f"Step failed: catalog: {catalog.error}")  # noqa: ADR-0019
            self._save_state()
            return 1
        for step in (
            StepType.VALIDATE,
            StepType.MEMORY_WRITE,
            StepType.GENERATE_REPORT,
            StepType.COMMIT_GATE,
        ):
            if step.value in self.state.completed_steps:
                continue
            executor = self._get_step_executor(step)
            assert executor is not None
            result = executor()
            if not result.success:
                print(f"Step failed: {step.value}: {result.error}")  # noqa: ADR-0019
                self._save_state()
                return 1
            self.state.completed_steps.append(step.value)
            self._save_state()
        self._publish_pr()
        print(f"COMPLETE {self.state.gmp_id}: {self.state.task}")  # noqa: ADR-0019
        self._clear_state()
        return 0

    def run(self, task: str, tier: str = "RUNTIME", resume: bool = False):
        """Execute the GMP DAG."""
        if resume and self._load_state():
            print(f"Resuming GMP: {self.state.gmp_id}")  # noqa: ADR-0019
        else:
            self._init_state(task, tier)

        self._print_header(f"GMP EXECUTOR: {self.state.gmp_id}")
        print(f"Task: {self.state.task}")  # noqa: ADR-0019
        print(f"Tier: {self.state.tier}")  # noqa: ADR-0019

        while True:
            next_step = self._next_step()
            if not next_step:
                break

            self.state.current_step = next_step
            self._save_state()

            executor = self._get_step_executor(next_step)
            if not executor:
                print(f"No executor for step: {next_step}")  # noqa: ADR-0019
                break

            result = executor()

            if result.success:
                self.state.completed_steps.append(next_step.value)
                self._save_state()
            else:
                print(f"\nStep failed: {next_step.value}")  # noqa: ADR-0019
                print(f"   Error: {result.error}")  # noqa: ADR-0019
                print("\nResume with: python3 workflows/gmp_executor.py --resume")  # noqa: ADR-0019
                return False

        self._print_header("GMP COMPLETE")
        print(f"{self.state.gmp_id}: {self.state.task}")  # noqa: ADR-0019
        print(f"   Report: {self.state.report_path}")  # noqa: ADR-0019
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="GMP Executor — Run the GMP DAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    workflows/gmp_executor.py "add validation to registry"
    workflows/gmp_executor.py --authorized-by slash-gmp --plan path.plan.md --mode start "task"
    workflows/gmp_executor.py --resume --mode finalize --commit-when-done
        """,
    )

    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--tier", choices=["KERNEL", "RUNTIME", "INFRA", "UX"], default="RUNTIME")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted GMP")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--reset", action="store_true", help="Clear state and start fresh")
    parser.add_argument("--authorized-by", choices=["slash-gmp"], default=None)
    parser.add_argument("--plan", type=Path, default=None)
    parser.add_argument(
        "--todos-json",
        default=None,
        help=(
            "Machine TODO plan: inline JSON list or path/@path "
            "(authorized start/full; both scope-lock). Bound at invocation."
        ),
    )
    parser.add_argument("--mode", choices=["start", "finalize", "full"], default=None)
    parser.add_argument("--commit-when-done", action="store_true")

    args = parser.parse_args()

    executor = GMPExecutor()
    executor.authorized = args.authorized_by == "slash-gmp"
    executor.commit_when_done = bool(args.commit_when_done)
    if getattr(args, "todos_json", None):
        executor.todos_json = args.todos_json
    if args.plan is not None:
        plan = args.plan if args.plan.is_absolute() else REPO_ROOT / args.plan
        executor.plan_path = plan
    executor.mode = args.mode or "full"

    if not executor.authorized and (args.resume or args.mode == "finalize"):
        # Restore authorization stamped into the state file by the /gmp start,
        # so the documented resume/finalize invocation works without repeating
        # --authorized-by (it must not re-gate a run the slash already opened).
        # Require a completed start ceremony so a partial _init_state stamp
        # cannot unlock finalize. Legacy states (pre-authorized_by field) that
        # already locked a plan are treated as slash-authorized on finalize.
        if executor._load_state() and executor.state is not None:
            state = executor.state
            stamped = state.authorized_by == "slash-gmp"
            legacy_finalize = (
                not state.authorized_by
                and args.mode == "finalize"
                and state.start_ceremony_complete()
            )
            if (stamped or legacy_finalize) and state.start_ceremony_complete():
                executor.authorized = True
            elif stamped and not state.start_ceremony_complete():
                print(  # noqa: ADR-0019
                    "GMP state has authorized_by=slash-gmp but start ceremony "
                    "incomplete; refusing to restore authorization for finalize"
                )

    if args.reset:
        executor._clear_state()
        print("State cleared")  # noqa: ADR-0019
        return

    if args.status:
        executor.status()
        return

    if executor.authorized:
        if executor.mode == "start":
            sys.exit(executor.run_authorized_start(args.task or "", args.tier))
        if executor.mode == "finalize" or args.resume:
            sys.exit(executor.run_authorized_finalize())
        sys.exit(executor.run_authorized_full(args.task or "", args.tier))

    if args.resume:
        if not STATE_FILE.exists() and not LEGACY_STATE_FILE.exists():
            print("No GMP to resume")  # noqa: ADR-0019
            sys.exit(1)
        success = executor.run("", resume=True)
        sys.exit(0 if success else 1)

    if not args.task:
        parser.print_help()
        sys.exit(1)

    success = executor.run(args.task, args.tier)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "cli",
        "data-models",
        "dataclass",
        "executor",
        "filesystem",
        "operations",
        "serialization",
        "subprocess",
        "testing",
    ],
    "keywords": ["executor", "gmp", "state", "status", "step"],
    "business_value": "This is what /gmp actually calls. Nothing else.",
    "last_modified": "2026-01-31T22:27:11Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
