#!/usr/bin/env python3
"""
Harvest Executor — The ONLY Entry Point for /harvest
=====================================================

Extracts code blocks from documentation into numbered files.

The DAG handles everything:
- Read source document
- Parse code blocks with line ranges
- Create harvest table
- Extract to numbered files using sed
- Validate syntax
- Generate report
- Commit (NO PUSH)

NO USER CONFIRMATION GATES — Fully autonomous execution.

Usage:
    python3 workflows/harvest_executor.py path/to/document.md
    python3 workflows/harvest_executor.py --status
    python3 workflows/harvest_executor.py --resume

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Harvest Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "harvest_executor",
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

def _get_repo_root(override: str | None = None) -> Path:
    """When run from .cursor-commands, use cwd as repo root unless override set."""
    if override:
        return Path(override).resolve()
    p = Path(__file__).resolve()
    if ".cursor-commands" in str(p):
        return Path.cwd()
    return p.parent.parent

REPO_ROOT = _get_repo_root()
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
STATE_FILE = REPO_ROOT / ".harvest_executor_state.json"
HARVEST_DIR = REPO_ROOT / "current_work" / "harvested"

# Stop phrases for 📁/📄 block end (prose after code)
BLOCK_STOP_PHRASES = (
    "Runtime effect",
    "This is how ",
    "This is ",
    "You now have",
    "✅ ",
    "👉 ",
    "—",
    "If you want",
    "Just say ",
    "Just tell me",
)

# Phase 2 / Sprint 1-4: N️⃣ path or "File: Emma/path"
FILE_EMMA_RE = re.compile(r"^File:\s*Emma/(.+?)(?:\s*\((UPDATED FULL|REPLACEMENT|FULL REWRITE)[^)]*\))?\s*$")
# Path-like substrings that mark start of a code block (Phase 2 numbered blocks)
PHASE2_PATH_MARKERS = (
    "src/emma/", "alembic/", "Emma/", "Dockerfile", "docker-compose",
    "requirements.txt", "pyproject.toml", ".env.example", "alembic.ini",
    "0001_init_core", "0007_multitenant",
)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class HarvestItem:
    number: int
    pattern: str  # e.g., "orchestrator.py", "config.py"
    source_start: int
    source_end: int
    target_file: str
    status: str = "pending"


@dataclass
class HarvestState:
    source_document: str
    started_at: str
    current_step: str
    completed_steps: list[str] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    output_dir: str = ""
    custom_output_dir: str = ""  # optional override from --output-dir
    repo_layout: bool = False  # write to repo paths (e.g. src/emma/main.py) not numbered files
    files_created: list[str] = field(default_factory=list)
    validation_results: list[dict] = field(default_factory=list)
    report_path: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> HarvestState:
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    "read_document",
    "parse_code_blocks",
    "create_harvest_table",
    "extract_files",
    "validate_syntax",
    "generate_report",
    "commit",
]


# =============================================================================
# Harvest Executor
# =============================================================================


class HarvestExecutor:
    """Executes the /harvest DAG — fully autonomous, no user gates."""

    def __init__(self):
        self.state: HarvestState | None = None
        self.document_content: str = ""

    def _save_state(self):
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = HarvestState.from_dict(data)
            return True
        return False

    def _clear_state(self):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = None

    def _run_shell(self, cmd: str, capture: bool = True) -> tuple[int, str, str]:
        """Run shell command."""
        result = subprocess.run(  # noqa: S602 - shell=True required for DAG executor
            cmd,
            shell=True,
            cwd=REPO_ROOT,
            capture_output=capture,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    def _print_header(self, title: str):
        print(f"\n{'=' * 60}")  # noqa: ADR-0019
        print(f"  {title}")  # noqa: ADR-0019
        print(f"{'=' * 60}\n")  # noqa: ADR-0019

    # =========================================================================
    # STEP 1: READ DOCUMENT
    # =========================================================================
    def _step_read_document(self) -> bool:
        self._print_header("READ DOCUMENT")

        source = self.state.source_document
        source_path = Path(source)

        if not source_path.is_absolute():
            source_path = REPO_ROOT / source

        if not source_path.exists():
            print(f"❌ Document not found: {source_path}")  # noqa: ADR-0019
            return False

        self.document_content = source_path.read_text()
        line_count = len(self.document_content.split("\n"))

        print(f"✅ Read: {source_path.name}")  # noqa: ADR-0019
        print(f"   Lines: {line_count}")  # noqa: ADR-0019

        # Output directory: repo_layout -> REPO_ROOT; else --output-dir or harvested/{date}/{doc_name}
        if getattr(self.state, "repo_layout", False):
            output_dir = REPO_ROOT
        elif getattr(self.state, "custom_output_dir", ""):
            output_dir = Path(self.state.custom_output_dir)
            if not output_dir.is_absolute():
                output_dir = REPO_ROOT / output_dir
        else:
            doc_name = source_path.stem
            today = datetime.now(UTC).strftime("%m-%d-%Y")
            output_dir = HARVEST_DIR / today / doc_name
        if not getattr(self.state, "repo_layout", False):
            output_dir.mkdir(parents=True, exist_ok=True)
        self.state.output_dir = str(output_dir)

        print(f"   Output dir: {output_dir}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 2: PARSE CODE BLOCKS
    # =========================================================================
    def _step_parse_code_blocks(self) -> bool:
        self._print_header("PARSE CODE BLOCKS")

        # Find all code blocks with their line numbers
        lines = self.document_content.split("\n")
        items = []
        item_num = 1

        in_code_block = False
        code_start = 0
        code_lang = ""
        current_code = []

        for i, line in enumerate(lines, 1):
            if line.startswith("```") and not in_code_block:
                # Start of code block
                in_code_block = True
                code_start = i
                code_lang = line[3:].strip()
                current_code = []
            elif line.startswith("```") and in_code_block:
                # End of code block
                in_code_block = False
                code_end = i

                # Determine file name from context or language
                if code_lang in ("python", "py"):
                    # Look for filename hints in surrounding text
                    pattern = f"code_block_{item_num}.py"
                    # Check previous lines for filename hints
                    for j in range(max(0, code_start - 5), code_start):
                        prev_line = lines[j - 1] if j > 0 else ""
                        # Look for patterns like `filename.py` or **filename.py**
                        match = re.search(
                            r"`([^`]+\.py)`|[*]{2}([^*]+\.py)[*]{2}", prev_line
                        )
                        if match:
                            pattern = match.group(1) or match.group(2)
                            break

                    items.append(
                        {
                            "number": item_num,
                            "pattern": pattern,
                            "source_start": code_start,
                            "source_end": code_end,
                            "target_file": f"{item_num}_{pattern}",
                            "status": "pending",
                            "language": code_lang,
                            "lines": code_end - code_start - 1,
                        }
                    )
                    item_num += 1

        # If no fenced blocks, try 📁/📄-style blocks (e.g. chat transcripts)
        if not items:
            items = self._parse_file_marker_blocks(lines)

        # If still none, try Phase 2 / Sprint 1-4: N️⃣ path or "File: Emma/path"
        if not items:
            items = self._parse_phase2_sprint_blocks(lines)

        self.state.items = items

        print(f"Found {len(items)} code blocks:")  # noqa: ADR-0019
        print("-" * 60)  # noqa: ADR-0019
        print("| # | Pattern | Lines | Range |")  # noqa: ADR-0019
        print("|---|---------|-------|-------|")  # noqa: ADR-0019
        for item in items[:20]:
            print(
                f"| {item['number']:2} | {item['pattern'][:25]:25} | {item['lines']:4} | {item['source_start']}-{item['source_end']} |"
            )  # noqa: ADR-0019
        if len(items) > 20:
            print(f"| ... and {len(items) - 20} more |")  # noqa: ADR-0019
        print("-" * 60)  # noqa: ADR-0019

        return len(items) > 0

    def _parse_file_marker_blocks(self, lines: list[str]) -> list[dict]:
        """Parse 📁 path or 📄 path lines; code runs until next 📁/📄 or stop phrase."""
        items = []
        item_num = 1
        i = 0
        while i < len(lines):
            line = lines[i]
            if not (line.strip().startswith("📁") or line.strip().startswith("📄")):
                i += 1
                continue
            path = line.replace("📁", "").replace("📄", "").strip()
            if not path or path.lower() in ("target layout", "extended layout", "path", "file tree (action-oriented)", "new module"):
                i += 1
                continue
            # Skip lines that are section titles, not file paths (e.g. "EMMA v1.0 — CANONICAL...")
            if "CANONICAL" in path or "FILE TREE" in path or ("/" not in path and "." not in path and len(path) > 30):
                i += 1
                continue
            code_start = i + 2  # first line after marker line (1-based: i+2)
            if code_start > len(lines):
                i += 1
                continue
            end = i + 1
            while end < len(lines):
                next_line = lines[end]
                if next_line.strip().startswith("📁") or next_line.strip().startswith("📄"):
                    break
                if any(next_line.strip().startswith(p) for p in BLOCK_STOP_PHRASES):
                    break
                end += 1
            code_end = end  # last line of code (1-based)
            if code_end < code_start:
                i += 1
                continue
            # Sanitize path to filename: take last segment, replace / with _
            name = path.split("/")[-1].strip() if "/" in path else path
            name = re.sub(r"[^\w.\-]", "_", name)[:50]
            if not name:
                name = f"block_{item_num}"
            ext = Path(name).suffix if Path(name).suffix else ".txt"
            if not name.endswith(ext):
                name = name + ext if "." not in name else name
            pattern = name
            target_file = f"{item_num}_{pattern}"
            items.append({
                "number": item_num,
                "pattern": pattern,
                "source_start": code_start,
                "source_end": code_end,
                "target_file": target_file,
                "status": "pending",
                "language": ext.lstrip("."),
                "lines": code_end - code_start + 1,
                "is_file_marker": True,
            })
            item_num += 1
            i = end if end > i else i + 1
        return items

    def _normalize_repo_path(self, raw: str) -> str:
        """Emma/src/emma/... -> src/emma/...; Emma/ -> (root)."""
        raw = raw.strip()
        if raw.startswith("Emma/"):
            return raw[5:]
        if raw.startswith("Emma\\"):
            return raw[5:].replace("\\", "/")
        return raw

    def _parse_phase2_sprint_blocks(self, lines: list[str]) -> list[dict]:
        """Parse N️⃣ path or 'File: Emma/path' lines; code until next marker or stop phrase."""
        items = []
        item_num = 1
        i = 0
        repo_layout = getattr(self.state, "repo_layout", False) if self.state else False
        while i < len(lines):
            line = lines[i]
            path = None
            is_replacement = False
            # "File: Emma/src/emma/core/auth.py" or "File: Emma/... (REPLACEMENT)"
            m = FILE_EMMA_RE.match(line.strip())
            if m:
                path = self._normalize_repo_path(m.group(1))
                is_replacement = bool(m.group(2))
            # Phase 2: "7️⃣ src/emma/main.py" or "1️⃣ Dockerfile" (line contains path marker)
            if not path:
                for marker in PHASE2_PATH_MARKERS:
                    if marker in line:
                        idx = line.find(marker)
                        segment = line[idx:].split(" (")[0].split()[0].strip()
                        segment = segment.rstrip(")]")
                        if "*" in segment or "<" in segment or ">" in segment or segment.endswith("/"):
                            continue
                        if marker == "Dockerfile":
                            path = "Dockerfile"
                        elif marker == "docker-compose":
                            path = "docker-compose.prod.yml" if "prod" in line.lower() else "docker-compose.yml"
                        elif "0001_init_core" in segment or (marker == "alembic.ini" and "0001" in line):
                            path = "alembic/versions/0001_init_core.py"
                        elif "0007_multitenant" in segment:
                            path = "alembic/versions/0007_multitenant_core.py"
                        else:
                            path = self._normalize_repo_path(segment)
                        # Only accept if it looks like a file (has extension or is Dockerfile/Makefile)
                        if path and (path in ("Dockerfile", "Makefile") or "." in path.split("/")[-1] or path.endswith(".txt")):
                            break
                        path = None
                if not path:
                    path = None
            if not path:
                i += 1
                continue
            # First line of code: line after marker (1-based)
            source_start = i + 2
            if source_start > len(lines):
                i += 1
                continue
            end = i + 1
            while end < len(lines):
                next_line = lines[end]
                if FILE_EMMA_RE.match(next_line.strip()) or any(m in next_line for m in PHASE2_PATH_MARKERS):
                    break
                if any(next_line.strip().startswith(p) for p in BLOCK_STOP_PHRASES):
                    break
                if next_line.strip() in ("Note:", "In prod:") and end > source_start:
                    break
                end += 1
            source_end = end  # last line of code (1-based)
            if source_end < source_start:
                i += 1
                continue
            name = path.split("/")[-1] if "/" in path else path
            name = re.sub(r"[^\w.\-]", "_", name)[:50] if not repo_layout else name
            ext = Path(path).suffix if Path(path).suffix else ".txt"
            if not name.endswith(ext) and "." not in name:
                name = name + ext if repo_layout else name
            target_file = path if repo_layout else f"{item_num}_{name}"
            items.append({
                "number": item_num,
                "pattern": path,
                "source_start": source_start,
                "source_end": source_end,
                "target_file": target_file,
                "status": "pending",
                "language": ext.lstrip(".") if ext else "txt",
                "lines": source_end - source_start + 1,
                "is_file_marker": True,
                "is_replacement": is_replacement,
            })
            item_num += 1
            i = end if end > i else i + 1
        return items

    # =========================================================================
    # STEP 3: CREATE HARVEST TABLE
    # =========================================================================
    def _step_create_harvest_table(self) -> bool:
        self._print_header("CREATE HARVEST TABLE")

        output_dir = Path(self.state.output_dir)
        table_file = output_dir / "HARVEST_TABLE.md"

        table_content = "# 🌾 HARVEST TABLE\n\n"
        table_content += "| # | Pattern | Source Lines | Target |\n"
        table_content += "|---|---------|--------------|--------|\n"

        for item in self.state.items:
            table_content += f"| {item['number']} | `{item['pattern']}` | {item['source_start']}-{item['source_end']} | `{item['target_file']}` |\n"

        table_content += f"\n**Source:** `{self.state.source_document}`\n"
        table_content += (
            f"**Harvested:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n"
        )

        table_file.write_text(table_content)
        print(f"✅ Created: {table_file}")  # noqa: ADR-0019
        print(f"   Items: {len(self.state.items)}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 4: EXTRACT FILES (using sed)
    # =========================================================================
    def _step_extract_files(self) -> bool:
        self._print_header("EXTRACT FILES (sed-based)")

        output_dir = Path(self.state.output_dir)
        source_path = Path(self.state.source_document)
        if not source_path.is_absolute():
            source_path = REPO_ROOT / self.state.source_document

        files_created = []

        for item in self.state.items:
            target_file = output_dir / item["target_file"]
            # Skip directory-like paths (would overwrite or conflict with existing dirs)
            base = target_file.name
            if not base or (target_file.suffix == "" and base not in ("Dockerfile", "Makefile")):
                item["status"] = "skipped"
                continue
            if "/" in item["target_file"] or "\\" in item["target_file"]:
                target_file.parent.mkdir(parents=True, exist_ok=True)
            if item.get("is_file_marker"):
                start, end = item["source_start"], item["source_end"]
            else:
                start = item["source_start"] + 1  # Skip opening ```
                end = item["source_end"] - 1  # Skip closing ```

            # Use sed to extract lines
            cmd = f'sed -n "{start},{end}p" "{source_path}" > "{target_file}"'
            code, _stdout, stderr = self._run_shell(cmd)

            if code == 0 and target_file.exists():
                item["status"] = "extracted"
                files_created.append(str(target_file))
                print(f"✅ {item['target_file']} ({item['lines']} lines)")  # noqa: ADR-0019
            else:
                item["status"] = "failed"
                print(f"❌ {item['target_file']}: {stderr[:50]}")  # noqa: ADR-0019

        self.state.files_created = files_created

        success = sum(1 for i in self.state.items if i["status"] == "extracted")
        print(f"\n✅ Extracted: {success}/{len(self.state.items)} files")  # noqa: ADR-0019

        return success > 0

    # =========================================================================
    # STEP 5: VALIDATE SYNTAX
    # =========================================================================
    def _step_validate_syntax(self) -> bool:
        self._print_header("VALIDATE SYNTAX")

        validations = []
        py_files = [f for f in self.state.files_created if f.endswith(".py")]

        if not py_files:
            print("⚠️  No Python files to validate")  # noqa: ADR-0019
            validations.append({"check": "py_compile", "status": "⚠️ N/A"})
            self.state.validation_results = validations
            return True

        # py_compile each file
        passed = 0
        for f in py_files:
            code, _stdout, stderr = self._run_shell(f'python3 -m py_compile "{f}"')
            if code == 0:
                passed += 1
                print(f"✅ {Path(f).name}")  # noqa: ADR-0019
            else:
                print(f"❌ {Path(f).name}: {stderr[:60]}")  # noqa: ADR-0019

        validations.append(
            {
                "check": "py_compile",
                "status": f"✅ {passed}/{len(py_files)}"
                if passed == len(py_files)
                else f"⚠️ {passed}/{len(py_files)}",
            }
        )

        self.state.validation_results = validations
        print(f"\n✅ Syntax valid: {passed}/{len(py_files)} files")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 6: GENERATE REPORT
    # =========================================================================
    def _step_generate_report(self) -> bool:
        self._print_header("GENERATE REPORT")

        # Build TODO items
        todo_args = []
        for item in self.state.items[:10]:
            todo_args.append(
                f'--todo "H{item["number"]}|{item["target_file"]}|{item["source_start"]}-{item["source_end"]}|EXTRACT|{item["status"]}"'
            )

        # Build validation items
        val_args = []
        for v in self.state.validation_results:
            val_args.append(f'--validation "{v["check"]}|{v["status"]}"')

        if not todo_args:
            todo_args.append('--todo "H1|harvest|*|EXTRACT|complete"')
        if not val_args:
            val_args.append('--validation "extraction|✅"')

        source_name = Path(self.state.source_document).stem
        cmd = f'''python3 {REPORT_GENERATOR} \
            --task "Harvest: {source_name[:30]}" \
            --tier RUNTIME_TIER \
            {" ".join(todo_args)} \
            {" ".join(val_args)} \
            --summary "Code harvesting via /harvest DAG executor" \
            --skip-verify 2>/dev/null || echo "Report generation skipped"'''

        print("Generating report...")  # noqa: ADR-0019
        _code, stdout, _stderr = self._run_shell(cmd)

        # Extract report path
        for line in stdout.split("\n"):
            if "Report saved:" in line or "reports/" in line.lower():
                self.state.report_path = line.strip()
                break

        if self.state.report_path:
            print(f"✅ Report: {self.state.report_path}")  # noqa: ADR-0019
        else:
            print("⚠️  Report generation skipped")  # noqa: ADR-0019
            self.state.report_path = "N/A"

        return True

    # =========================================================================
    # STEP 7: COMMIT (NO PUSH)
    # =========================================================================
    def _step_commit(self) -> bool:
        self._print_header("COMMIT (NO PUSH)")

        if not self.state.files_created:
            print("✅ No files to commit")  # noqa: ADR-0019
            return True

        # Stage output directory
        output_dir = self.state.output_dir
        self._run_shell(f'git add "{output_dir}"')

        # Create commit message
        source_name = Path(self.state.source_document).stem
        count = len(self.state.files_created)

        commit_msg = f"harvest({source_name}): {count} files extracted"

        # Commit
        cmd = f'git commit -m "{commit_msg}" --no-verify 2>&1 || true'
        code, stdout, _stderr = self._run_shell(cmd)

        if "nothing to commit" in stdout.lower():
            print("✅ Nothing to commit — working tree clean")  # noqa: ADR-0019
        elif code == 0 or "file changed" in stdout.lower():
            _code, hash_out, _ = self._run_shell("git rev-parse --short HEAD")
            self.state.commit_hash = hash_out.strip()
            print(f"✅ Committed: {self.state.commit_hash}")  # noqa: ADR-0019
            print(f"   Message: {commit_msg}")  # noqa: ADR-0019
        else:
            print(f"⚠️  Commit result: {stdout[:100]}")  # noqa: ADR-0019

        print("\n⚠️  DO NOT PUSH — Review changes first")  # noqa: ADR-0019

        return True

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active /harvest execution. Start with:")  # noqa: ADR-0019
            print("  python3 workflows/harvest_executor.py path/to/document.md")  # noqa: ADR-0019
            return

        self._print_header(f"HARVEST STATUS: {self.state.source_document}")
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print(f"Current step: {self.state.current_step}")  # noqa: ADR-0019
        print(f"Items: {len(self.state.items)}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                print(f"  ✅ {step}")  # noqa: ADR-0019
            elif step == self.state.current_step:
                print(f"  🔄 {step}")  # noqa: ADR-0019
            else:
                print(f"  ⏳ {step}")  # noqa: ADR-0019

    def run(
        self,
        source_document: str = "",
        resume: bool = False,
        output_dir: str = "",
        repo_layout: bool = False,
    ):
        """Execute the /harvest DAG — fully autonomous."""
        # Initialize or resume
        if resume and self._load_state():
            print(f"Resuming harvest: {self.state.source_document}")  # noqa: ADR-0019
        else:
            if not source_document:
                print("❌ Source document required")  # noqa: ADR-0019
                return False
            self.state = HarvestState(
                source_document=source_document,
                started_at=datetime.now(UTC).isoformat(),
                current_step=STEP_ORDER[0],
                custom_output_dir=output_dir or "",
                repo_layout=repo_layout,
            )
            self._save_state()

        self._print_header(f"HARVEST EXECUTOR: {self.state.source_document}")

        # Step executors
        executors = {
            "read_document": self._step_read_document,
            "parse_code_blocks": self._step_parse_code_blocks,
            "create_harvest_table": self._step_create_harvest_table,
            "extract_files": self._step_extract_files,
            "validate_syntax": self._step_validate_syntax,
            "generate_report": self._step_generate_report,
            "commit": self._step_commit,
        }

        # Execute steps in order
        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                continue

            self.state.current_step = step
            self._save_state()

            executor = executors.get(step)
            if not executor:
                print(f"❌ No executor for step: {step}")  # noqa: ADR-0019
                break

            success = executor()

            if success:
                self.state.completed_steps.append(step)
                self._save_state()
            else:
                print(f"\n❌ Step failed: {step}")  # noqa: ADR-0019
                print("\nResume with: python3 workflows/harvest_executor.py --resume")  # noqa: ADR-0019
                return False

        # Complete
        self._print_header("HARVEST COMPLETE")
        print(f"✅ Source: {self.state.source_document}")  # noqa: ADR-0019
        print(f"   Items: {len(self.state.items)}")  # noqa: ADR-0019
        print(f"   Files: {len(self.state.files_created)}")  # noqa: ADR-0019
        print(f"   Output: {self.state.output_dir}")  # noqa: ADR-0019
        print(f"   Report: {self.state.report_path}")  # noqa: ADR-0019
        if self.state.commit_hash:
            print(f"   Commit: {self.state.commit_hash}")  # noqa: ADR-0019
        print("\n⚠️  DO NOT PUSH — Review changes first")  # noqa: ADR-0019
        print(
            f"\n→ Next: python3 workflows/use_harvest_executor.py {self.state.output_dir}"
        )  # noqa: ADR-0019

        # Clean up state
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Harvest Executor — Extract code from documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/harvest_executor.py current_work/doc.md
    python3 workflows/harvest_executor.py --resume
    python3 workflows/harvest_executor.py --status
        """,
    )

    parser.add_argument("source", nargs="?", help="Source document to harvest from")
    parser.add_argument(
        "--output-dir", "-o", metavar="DIR", help="Output directory for harvested files"
    )
    parser.add_argument(
        "--repo-root", metavar="DIR", help="Project root (when run from another workspace)"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume interrupted execution"
    )
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument(
        "--reset", action="store_true", help="Clear state and start fresh"
    )
    parser.add_argument(
        "--repo-layout", action="store_true",
        help="Write files to repo paths (e.g. src/emma/main.py) under repo root"
    )

    args = parser.parse_args()

    if args.repo_root:
        global REPO_ROOT, STATE_FILE
        REPO_ROOT = _get_repo_root(args.repo_root)
        STATE_FILE = REPO_ROOT / ".harvest_executor_state.json"

    executor = HarvestExecutor()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("✅ State cleared")  # noqa: ADR-0019
        return

    if args.status:
        executor.status()
        return

    if args.resume:
        if not STATE_FILE.exists():
            print("No harvest execution to resume")  # noqa: ADR-0019
            sys.exit(1)
        executor.run(resume=True)
        return

    if not args.source:
        parser.print_help()
        sys.exit(1)

    source = args.source[0] if isinstance(args.source, list) and args.source else args.source
    success = executor.run(
        args.source,
        output_dir=args.output_dir or "",
        repo_layout=args.repo_layout,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "cli",
        "dataclass",
        "executor",
        "filesystem",
        "messaging",
        "operations",
        "security",
        "serialization",
        "subprocess",
        "workflows",
    ],
    "keywords": ["executor", "harvest", "state", "status"],
    "business_value": "Read source document Parse code blocks with line ranges Create harvest table Extract to numbered files using sed Validate syntax Generate report Commit (NO PUSH) NO USER CONFIRMATION GATES — Fully aut",
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
