"""
L9 Core Governance - Session Startup Protocol
==============================================

Executable session startup protocol.
Converts patterns from profiles/session-startup-protocol.md into
programmatic preflight checks and mandatory file loading.

Key capabilities:
- Runs preflight checks (symlinks, config, directories, Python version)
- Loads mandatory startup files
- Verifies kernel readiness (two-phase activation)
- Loads and caches mistake patterns from repeated-mistakes.md
- Computes SHA256 hashes for file integrity verification
- Returns structured status (not just instructions)
- Tracks loaded components for debugging

Version: 3.2.0
GMP: GMP-95 Session Startup Enhancement

Harvested from:
- ops/scripts/pre_execution_checker.py (mistake pattern loading)
- integrity/hash-verifier.py (SHA256 file verification)
- ops/scripts/verify-startup-files.sh (extended file list)
- .cursor/rules/*.mdc (20 critical rules)

v3.2.0 Changes:
- Improved regex to capture ALL lessons (not just 8)
- Filters invalid lessons (success patterns)
- Handles duplicate lesson numbers (15, 15b)
- Classifies lessons as curated vs auto-generated
- Detects ULTRA_CRITICAL severity (🚨)
"""

from __future__ import annotations

import subprocess
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import hashlib

logger = structlog.get_logger(__name__)


@dataclass
class CommandResult:
    """Result of a shell command execution."""
    
    command: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int


@dataclass
class StartupFile:
    """
    A mandatory startup file.
    
    Attributes:
        path: Relative path from workspace root
        component_id: Unique identifier (e.g., "PRF-SSP-001")
        required: Whether missing file is a failure
        description: What this file provides
    """
    
    path: str
    component_id: str
    required: bool = True
    description: str = ""


@dataclass
class PreflightResult:
    """Result of a preflight check."""
    
    name: str
    passed: bool
    message: str
    details: Optional[dict[str, Any]] = None


@dataclass
class KernelReadinessResult:
    """Result of kernel readiness check."""

    kernels_ready: bool
    kernel_state: str  # INACTIVE, LOADING, VALIDATING, ACTIVE, ERROR
    kernel_count: int
    kernel_hash_snapshot: Dict[str, str] = field(default_factory=dict)
    integrity_verified: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class MistakePattern:
    """
    A parsed mistake pattern from repeated-mistakes.md.
    
    Harvested from: ops/scripts/pre_execution_checker.py
    """
    
    lesson_id: str
    number: int
    title: str
    mistake: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    keywords: List[str] = field(default_factory=list)
    prevention: str = ""
    rule: str = ""


@dataclass
class CriticalRule:
    """
    A critical rule extracted from .cursor/rules/*.mdc files.
    
    These are the 20 most important behavioral constraints for Cursor.
    Version 3.1.0 - Harvested from .cursor/rules/
    """
    
    rule_id: str
    source: str  # Source .mdc file
    category: str  # PATH, VPS, EXECUTION, PROTECTED, ANTI_PATTERN, SAFETY
    title: str
    rule: str
    keywords: List[str] = field(default_factory=list)


# ============================================================================
# CRITICAL RULES — Hardcoded from .cursor/rules/*.mdc (v3.1.0)
# ============================================================================
# These 20 rules are the most critical behavioral constraints.
# Source: .cursor/rules/92-learned-lessons.mdc, 01-vps-rules.mdc,
#         90-protected-core.mdc, 60-anti-patterns.mdc, 00-global.mdc

CRITICAL_RULES: List[CriticalRule] = [
    # === PATH RULES (from 92-learned-lessons.mdc) ===
    CriticalRule(
        rule_id="PATH-001",
        source="92-learned-lessons.mdc",
        category="PATH",
        title="Dropbox Not Library",
        rule="GlobalCommands is in Dropbox, NOT Library. Use $HOME/Dropbox/Cursor Governance/GlobalCommands",
        keywords=["dropbox", "library", "globalcommands", "path"],
    ),
    CriticalRule(
        rule_id="PATH-002",
        source="92-learned-lessons.mdc",
        category="PATH",
        title="Use $HOME Variable",
        rule="NEVER hardcode /Users/ib-mac/ in scripts. ALWAYS use $HOME or Path.home()",
        keywords=["home", "path", "hardcode", "users"],
    ),
    CriticalRule(
        rule_id="PATH-003",
        source="92-learned-lessons.mdc",
        category="PATH",
        title="Docker Compose ROOT Only",
        rule="Always use ROOT docker-compose.yml, not docs/docker-compose.yaml",
        keywords=["docker", "compose", "root", "docs"],
    ),
    
    # === VPS RULES (from 01-vps-rules.mdc) ===
    CriticalRule(
        rule_id="VPS-001",
        source="01-vps-rules.mdc",
        category="VPS",
        title="VPS Hands Off",
        rule="LOCAL EDIT → GIT PUSH → VPS PULL. NEVER edit files directly on VPS",
        keywords=["vps", "edit", "git", "push", "pull"],
    ),
    CriticalRule(
        rule_id="VPS-002",
        source="01-vps-rules.mdc",
        category="VPS",
        title="VPS Forbidden Commands",
        rule="FORBIDDEN on VPS: vim, nano, echo >, touch, mkdir, sed -i, rm, cp, mv, pip install",
        keywords=["vps", "vim", "nano", "forbidden", "edit"],
    ),
    CriticalRule(
        rule_id="VPS-003",
        source="01-vps-rules.mdc",
        category="VPS",
        title="VPS Allowed Commands",
        rule="ALLOWED on VPS: git pull, docker compose up/down/restart, cat, grep, ls, curl",
        keywords=["vps", "git", "docker", "allowed", "read"],
    ),
    
    # === EXECUTION RULES (from 92-learned-lessons.mdc) ===
    CriticalRule(
        rule_id="EXEC-001",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Surgical Edits Only",
        rule="NEVER rewrite entire files. Use search_replace for targeted edits. Preserve formatting",
        keywords=["surgical", "edit", "rewrite", "replace"],
    ),
    CriticalRule(
        rule_id="EXEC-002",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Run Commands Don't Show",
        rule="ALWAYS run commands and display results. NEVER just show command to run",
        keywords=["run", "command", "execute", "proactive"],
    ),
    CriticalRule(
        rule_id="EXEC-003",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Ask Questions First",
        rule="NEVER build first, ask questions later. 5-10 min of questions saves 4-8 hours",
        keywords=["ask", "question", "clarify", "build"],
    ),
    CriticalRule(
        rule_id="EXEC-004",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Never Claim Fixed Without Proof",
        rule="ALWAYS provide evidence before claiming success. Run tests and show results",
        keywords=["fixed", "proof", "evidence", "test"],
    ),
    CriticalRule(
        rule_id="EXEC-005",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Search Before Creating",
        rule="ALWAYS search for existing solutions first. Adapt existing work, don't recreate",
        keywords=["search", "existing", "create", "duplicate"],
    ),
    CriticalRule(
        rule_id="EXEC-006",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Never Fabricate Data",
        rule="NEVER make up phone numbers, emails, addresses, or any data. Leave blank if unknown",
        keywords=["fabricate", "data", "fake", "make up"],
    ),
    CriticalRule(
        rule_id="EXEC-007",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Never Move Files Without Permission",
        rule="NEVER move, rename, or relocate files unless explicitly asked. ASK before moving",
        keywords=["move", "rename", "relocate", "permission"],
    ),
    CriticalRule(
        rule_id="EXEC-008",
        source="92-learned-lessons.mdc",
        category="EXECUTION",
        title="Never Undo User Deletions",
        rule="If user deletes content, it's intentional. NEVER re-add deleted content",
        keywords=["delete", "undo", "restore", "removed"],
    ),
    
    # === PROTECTED FILES (from 90-protected-core.mdc) ===
    CriticalRule(
        rule_id="PROT-001",
        source="90-protected-core.mdc",
        category="PROTECTED",
        title="Protected Core Files",
        rule="Protected: kernel_loader.py, executor.py, websocket_orchestrator.py, memory_substrate_service.py, docker-compose.yml",
        keywords=["protected", "kernel", "executor", "core"],
    ),
    CriticalRule(
        rule_id="PROT-002",
        source="90-protected-core.mdc",
        category="PROTECTED",
        title="Protected File Change Process",
        rule="STOP if change touches protected file. Create separate GMP Phase 0 plan. Wait for approval",
        keywords=["protected", "stop", "gmp", "approval"],
    ),
    
    # === ANTI-PATTERNS (from 60-anti-patterns.mdc) ===
    CriticalRule(
        rule_id="ANTI-001",
        source="60-anti-patterns.mdc",
        category="ANTI_PATTERN",
        title="No TypeScript any",
        rule="NEVER use 'any' type in TypeScript. Use proper interfaces and generics",
        keywords=["typescript", "any", "type", "interface"],
    ),
    CriticalRule(
        rule_id="ANTI-002",
        source="60-anti-patterns.mdc",
        category="ANTI_PATTERN",
        title="No Bare Except",
        rule="NEVER use bare except in Python. Catch specific exceptions and log them",
        keywords=["python", "except", "bare", "catch"],
    ),
    CriticalRule(
        rule_id="ANTI-003",
        source="60-anti-patterns.mdc",
        category="ANTI_PATTERN",
        title="No Business Logic in Routes",
        rule="NEVER put business logic directly in FastAPI route body. Use service layer",
        keywords=["fastapi", "route", "business", "logic", "service"],
    ),
    
    # === SAFETY (from 00-global.mdc) ===
    CriticalRule(
        rule_id="SAFE-001",
        source="00-global.mdc",
        category="SAFETY",
        title="High-Risk Approval Gates",
        rule="High-risk tools (GMPRUN, GITCOMMIT, MACAGENTEXEC) require explicit Igor approval",
        keywords=["approval", "high-risk", "igor", "gate"],
    ),
]


@dataclass
class StartupResult:
    """Complete startup protocol result."""

    status: str  # "READY", "DEGRADED", "BLOCKED"
    preflight_passed: bool
    files_loaded: list[str]
    files_failed: list[str]
    errors: list[str]
    warnings: list[str]
    started_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    # Kernel readiness (v2.0)
    kernels_ready: bool = False
    kernel_state: str = "NOT_CHECKED"
    kernel_hash_snapshot: Dict[str, str] = field(default_factory=dict)
    # Mistake patterns (v3.2 - harvested from pre_execution_checker.py)
    mistakes_loaded: int = 0
    mistakes_ultra_critical: int = 0
    mistakes_critical: int = 0
    mistakes_curated: int = 0
    # Critical rules (v3.1 - harvested from .cursor/rules/*.mdc)
    rules_loaded: int = 0
    # Index generation (v3.3)
    indexes_generated: bool = False
    indexes_count: int = 0


class SessionStartup:
    """
    Executable session startup protocol.

    Runs preflight checks, loads mandatory files, and verifies kernel readiness,
    returning structured status for governance verification.

    Usage:
        startup = SessionStartup(Path("/Users/ib-mac/Projects/L9"))
        result = startup.execute()
        if result.status != "READY":
            # Handle startup issues
            pass

    Cursor Kernel Check:
        - Checks if Cursor workflow kernel exists (agents/cursor/cursor_workflow_kernel.yaml)
        - Verifies kernel file is readable and valid YAML
        - Computes SHA256 hash for integrity verification
    """

    def __init__(
        self,
        workspace_root: Path,
        check_kernels: bool = True,
    ) -> None:
        """
        Initialize startup protocol.

        Args:
            workspace_root: Path to workspace root directory
            check_kernels: Whether to check Cursor workflow kernel (default True)
        """
        self.root = workspace_root
        self.check_kernels = check_kernels
        self._files_loaded: list[str] = []
        self._errors: list[str] = []
        self._warnings: list[str] = []
        self._kernel_result: Optional[KernelReadinessResult] = None
    
    @property
    def mandatory_files(self) -> list[StartupFile]:
        """Get list of mandatory startup files."""
        return [
            # Core governance
            StartupFile(
                ".cursor-commands/profiles/session-startup-protocol.md",
                "PRF-SSP-001",
                required=True,
                description="Session startup protocol",
            ),
            StartupFile(
                ".cursor-commands/startup/REASONING_STACK.yaml",
                "REASONING-STACK-001",
                required=True,
                description="Reasoning activation config",
            ),
            # Learning files
            StartupFile(
                ".cursor-commands/learning/credentials-policy.md",
                "LRN-006",
                required=False,
                description="Credentials handling policy",
            ),
            StartupFile(
                ".cursor-commands/learning/failures/repeated-mistakes.md",
                "LRN-001",
                required=True,
                description="Critical mistake patterns",
            ),
            StartupFile(
                ".cursor-commands/learning/patterns/quick-fixes.md",
                "LRN-002",
                required=True,
                description="Quick fix patterns",
            ),
            # Startup files
            StartupFile(
                ".cursor-commands/startup/system_capabilities.md",
                "STARTUP-001",
                required=False,
                description="System capabilities manifest",
            ),
            # Reasoning profiles
            StartupFile(
                ".cursor-commands/profiles/reasoning_docs.md",
                "PROFILE-001",
                required=False,
                description="Documentation reasoning mode",
            ),
            StartupFile(
                ".cursor-commands/profiles/reasoning_technical_operations.md",
                "PROFILE-002",
                required=False,
                description="Technical operations reasoning",
            ),
            # Operating modes
            StartupFile(
                ".cursor-commands/profiles/ynp_mode.md",
                "MODE-001",
                required=False,
                description="YNP co-pilot mode",
            ),
            StartupFile(
                ".cursor-commands/profiles/dev_mode.md",
                "MODE-002",
                required=False,
                description="Development automation mode",
            ),
            StartupFile(
                ".cursor-commands/profiles/orchestrator.md",
                "MODE-003",
                required=False,
                description="Orchestrator coordination mode",
            ),
            # Workflow state (CRITICAL - always read first after preflight)
            StartupFile(
                "workflow_state.md",
                "STATE-001",
                required=True,
                description="Current workflow state, phase, next steps",
            ),
            # ============================================================
            # CURSOR-SPECIFIC FILES (agents/cursor/)
            # ============================================================
            # Cursor workflow kernel (BINDING CONTRACT)
            StartupFile(
                "agents/cursor/cursor_workflow_kernel.yaml",
                "CURSOR-KERNEL-001",
                required=True,  # This is LAW
                description="Cursor workflow kernel - binding behavioral contract",
            ),
            # GMP Protocol - Phase contracts
            StartupFile(
                "agents/cursor/gmp_protocol/gmp-contract.yaml",
                "CURSOR-GMP-001",
                required=False,
                description="GMP phase execution contract (binding)",
            ),
            # GMP Protocol - Report contracts
            StartupFile(
                "agents/cursor/gmp_protocol/gmp-report-contract.yaml",
                "CURSOR-GMP-002",
                required=False,
                description="GMP report structure contract (binding)",
            ),
            # GMP Protocol - Report template
            StartupFile(
                "agents/cursor/gmp_protocol/gmp-report-template.md",
                "CURSOR-GMP-003",
                required=False,
                description="GMP report template for generation",
            ),
            # Cursor memory client documentation
            StartupFile(
                "agents/cursor/docs/CURSOR-MEMORY-CLIENT.md",
                "CURSOR-DOC-001",
                required=False,
                description="Memory client commands reference (27 commands)",
            ),
            # Cursor-L9 integration guide
            StartupFile(
                "agents/cursor/docs/CURSOR-L9-INTEGRATION.md",
                "CURSOR-DOC-002",
                required=False,
                description="How Cursor leverages L9 infrastructure",
            ),
            # Cursor README overview
            StartupFile(
                "agents/cursor/README.md",
                "CURSOR-README-001",
                required=False,
                description="Cursor agent pack overview",
            ),
            # Production patterns and templates (reference on demand)
            StartupFile(
                "agents/cursor/docs/PRODUCTION-SPEED-PACK.md",
                "CURSOR-REF-001",
                required=False,
                description="Code templates, refactoring patterns, production checklist",
            ),
            # ============================================================
            # EXTENDED FILES (v3.0 - harvested from verify-startup-files.sh)
            # ============================================================
            StartupFile(
                ".cursor-commands/profiles/workflow-governance.md",
                "EXE-WF-001",
                required=False,
                description="Workflow governance profile",
            ),
            StartupFile(
                ".cursor-commands/profiles/operational-health.md",
                "EXE-OP-001",
                required=False,
                description="Operational health profile",
            ),
            StartupFile(
                ".cursor-commands/intelligence/context-memory/context-extractor.py",
                "INT-CTX-001",
                required=False,
                description="Context memory extractor",
            ),
            StartupFile(
                ".cursor-commands/foundation/logic/universal-kernel.md",
                "FND-LG-002",
                required=False,
                description="Universal kernel logic",
            ),
            StartupFile(
                ".cursor-commands/foundation/logic/rule-registry.json",
                "FND-LG-001",
                required=False,
                description="Rule registry",
            ),
        ]
    
    def run_preflight(self) -> list[PreflightResult]:
        """
        Execute preflight checks.
        
        Returns:
            List of PreflightResult objects
        """
        results: list[PreflightResult] = []
        
        # Check 1: Workspace root exists
        results.append(PreflightResult(
            name="workspace_exists",
            passed=self.root.exists(),
            message=f"Workspace root: {self.root}",
        ))
        
        # Check 2: .cursor-commands symlink
        symlink = self.root / ".cursor-commands"
        symlink_valid = symlink.is_symlink() and symlink.exists()
        symlink_target = ""
        if symlink.is_symlink():
            try:
                symlink_target = str(symlink.resolve())
            except Exception:
                symlink_target = "unresolvable"
        
        results.append(PreflightResult(
            name="symlink_valid",
            passed=symlink_valid,
            message=f"Symlink target: {symlink_target}",
            details={"target": symlink_target, "is_symlink": symlink.is_symlink()},
        ))
        
        # Check 3: Symlink points to Dropbox (not Library)
        dropbox_valid = "Dropbox" in symlink_target
        results.append(PreflightResult(
            name="symlink_dropbox",
            passed=dropbox_valid,
            message="Symlink must point to Dropbox, not Library",
            details={"contains_dropbox": dropbox_valid},
        ))
        
        # Check 4: workflow_state.md exists
        workflow_state = self.root / "workflow_state.md"
        results.append(PreflightResult(
            name="workflow_state_exists",
            passed=workflow_state.exists(),
            message=f"Workflow state: {workflow_state}",
        ))
        
        # Check 5: core/governance/ exists
        gov_dir = self.root / "core" / "governance"
        results.append(PreflightResult(
            name="governance_dir_exists",
            passed=gov_dir.exists(),
            message=f"Governance directory: {gov_dir}",
        ))
        
        # Check 6: Python version (v3.0 - harvested from env-manager.py pattern)
        import sys
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        py_ok = sys.version_info >= (3, 10)
        results.append(PreflightResult(
            name="python_version",
            passed=py_ok,
            message=f"Python {py_version} (requires >= 3.10)",
            details={"version": py_version, "major": sys.version_info.major, "minor": sys.version_info.minor},
        ))
        
        return results
    
    def load_mandatory_files(self) -> dict[str, Any]:
        """
        Load all mandatory startup files.
        
        Returns:
            Dict with loaded, failed, and total counts
        """
        results: dict[str, Any] = {
            "loaded": [],
            "failed": [],
            "total": len(self.mandatory_files),
        }
        
        for sf in self.mandatory_files:
            path = self.root / sf.path
            
            if path.exists():
                try:
                    # Just verify we can read it
                    content = path.read_text(encoding="utf-8")
                    self._files_loaded.append(sf.component_id)
                    results["loaded"].append({
                        "path": sf.path,
                        "component_id": sf.component_id,
                        "size_bytes": len(content),
                    })
                    logger.debug(
                        "session_startup.file_loaded",
                        path=sf.path,
                        component_id=sf.component_id,
                    )
                except Exception as e:
                    results["failed"].append({
                        "path": sf.path,
                        "error": str(e),
                    })
                    if sf.required:
                        self._errors.append(f"CRITICAL: Cannot read {sf.path}: {e}")
                    else:
                        self._warnings.append(f"Cannot read {sf.path}: {e}")
            else:
                results["failed"].append({
                    "path": sf.path,
                    "error": "File not found",
                })
                if sf.required:
                    self._errors.append(f"CRITICAL: Missing required file {sf.path}")
                else:
                    self._warnings.append(f"Optional file missing: {sf.path}")
        
        results["success"] = len([f for f in results["failed"] if "CRITICAL" in str(f)]) == 0
        return results

    def check_cursor_workflow_kernel(self) -> KernelReadinessResult:
        """
        Check Cursor workflow kernel readiness.
        
        Verifies:
        1. Cursor workflow kernel file exists: agents/cursor/cursor_workflow_kernel.yaml
        2. Kernel file is readable and valid YAML

        Returns:
            KernelReadinessResult with readiness status
        """
        errors: list[str] = []
        kernel_hashes: Dict[str, str] = {}

        # Check Cursor workflow kernel file exists (top-level in agents/cursor/)
        cursor_kernel_path = self.root / "agents" / "cursor" / "cursor_workflow_kernel.yaml"
        
        if not cursor_kernel_path.exists():
            errors.append(f"Cursor workflow kernel not found: {cursor_kernel_path}")
            return KernelReadinessResult(
                kernels_ready=False,
                kernel_state="NOT_FOUND",
                kernel_count=0,
                errors=errors,
            )

        # Verify file is readable and compute hash
        try:
            import hashlib
            data = cursor_kernel_path.read_bytes()
            kernel_hashes[str(cursor_kernel_path.relative_to(self.root))] = hashlib.sha256(
                data
            ).hexdigest()
            
            # Basic YAML validation
            try:
                import yaml
                yaml.safe_load(data)
            except Exception as e:
                errors.append(f"Cursor kernel YAML invalid: {e}")
        except Exception as e:
            errors.append(f"Failed to read Cursor kernel: {e}")

        # Determine readiness
        kernels_ready = len(errors) == 0
        kernel_state = "READY" if kernels_ready else "ERROR"

        result = KernelReadinessResult(
            kernels_ready=kernels_ready,
            kernel_state=kernel_state,
            kernel_count=1 if kernels_ready else 0,
            kernel_hash_snapshot=kernel_hashes,
            integrity_verified=len(kernel_hashes) == 1,
            errors=errors,
        )

        self._kernel_result = result

        logger.info(
            "session_startup.cursor_kernel_check",
            kernels_ready=kernels_ready,
            kernel_path=str(cursor_kernel_path.relative_to(self.root)),
            kernel_state=kernel_state,
            errors=errors,
        )

        return result

    def execute(self) -> StartupResult:
        """
        Execute full startup protocol.

        Includes:
        1. Preflight checks (workspace, symlinks, directories)
        2. Mandatory file loading
        3. Cursor workflow kernel verification (if check_kernels=True)

        Returns:
            StartupResult with complete status
        """
        start_time = datetime.utcnow()

        # Clear state
        self._files_loaded = []
        self._errors = []
        self._warnings = []
        self._kernel_result = None

        # Run preflight
        preflight_results = self.run_preflight()
        preflight_passed = all(
            r.passed
            for r in preflight_results
            if r.name in ["workspace_exists", "workflow_state_exists"]
        )

        if not preflight_passed:
            for r in preflight_results:
                if not r.passed:
                    self._errors.append(f"Preflight failed: {r.name} - {r.message}")

            return StartupResult(
                status="BLOCKED",
                preflight_passed=False,
                files_loaded=[],
                files_failed=[r.name for r in preflight_results if not r.passed],
                errors=self._errors,
                warnings=self._warnings,
                duration_ms=self._calc_duration_ms(start_time),
            )

        # Load mandatory files
        file_results = self.load_mandatory_files()

        # Load mistake patterns (v3.2)
        mistake_patterns = self.load_mistake_patterns()
        mistakes_loaded = len(mistake_patterns)
        mistakes_ultra_critical = len([p for p in mistake_patterns if p.severity == "ULTRA_CRITICAL"])
        mistakes_critical = len([p for p in mistake_patterns if p.severity == "CRITICAL"])
        mistakes_curated = len([p for p in mistake_patterns if not p.title.endswith("...")])

        # Load critical rules (v3.1)
        critical_rules = self.load_critical_rules()
        rules_loaded = len(critical_rules)

        # Run index export (v3.3) - generates repo index files including adr_catalog.txt
        indexes_generated, indexes_count = self.run_index_export()
        if not indexes_generated:
            self._warnings.append("Index export failed or skipped")

        # Check Cursor workflow kernel readiness
        kernels_ready = False
        kernel_state = "NOT_CHECKED"
        kernel_hash_snapshot: Dict[str, str] = {}

        if self.check_kernels:
            kernel_result = self.check_cursor_workflow_kernel()
            kernels_ready = kernel_result.kernels_ready
            kernel_state = kernel_result.kernel_state
            kernel_hash_snapshot = kernel_result.kernel_hash_snapshot

            # Add kernel errors to main errors
            for err in kernel_result.errors:
                if "not found" in err.lower() or "invalid" in err.lower():
                    self._errors.append(f"CRITICAL: {err}")
                else:
                    self._warnings.append(f"Cursor kernel: {err}")

        # Determine status
        critical_failures = [e for e in self._errors if "CRITICAL" in e]
        if critical_failures:
            status = "BLOCKED"
        elif self._warnings:
            status = "DEGRADED"
        else:
            status = "READY"

        duration_ms = self._calc_duration_ms(start_time)

        logger.info(
            "session_startup.complete",
            status=status,
            files_loaded=len(file_results["loaded"]),
            files_failed=len(file_results["failed"]),
            kernels_ready=kernels_ready,
            kernel_state=kernel_state,
            mistakes_loaded=mistakes_loaded,
            mistakes_ultra_critical=mistakes_ultra_critical,
            mistakes_critical=mistakes_critical,
            mistakes_curated=mistakes_curated,
            rules_loaded=rules_loaded,
            indexes_generated=indexes_generated,
            indexes_count=indexes_count,
            duration_ms=duration_ms,
        )

        return StartupResult(
            status=status,
            preflight_passed=preflight_passed,
            files_loaded=self._files_loaded,
            files_failed=[f["path"] for f in file_results["failed"]],
            errors=self._errors,
            warnings=self._warnings,
            duration_ms=duration_ms,
            kernels_ready=kernels_ready,
            kernel_state=kernel_state,
            kernel_hash_snapshot=kernel_hash_snapshot,
            mistakes_loaded=mistakes_loaded,
            mistakes_ultra_critical=mistakes_ultra_critical,
            mistakes_critical=mistakes_critical,
            mistakes_curated=mistakes_curated,
            rules_loaded=rules_loaded,
            indexes_generated=indexes_generated,
            indexes_count=indexes_count,
        )
    
    def _calc_duration_ms(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)

    def _sha256_file(self, path: Path) -> str:
        """
        Compute SHA256 hash of a file.
        
        Harvested from: integrity/hash-verifier.py
        
        Args:
            path: Path to file
            
        Returns:
            Hex digest of SHA256 hash
        """
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for pattern matching.
        
        Harvested from: ops/scripts/pre_execution_checker.py
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keywords (up to 10)
        """
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
            'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'just', 'don', 'now'
        }
        words = re.findall(r'\b\w{4,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        return list(set(keywords))[:10]

    def load_mistake_patterns(self) -> List[MistakePattern]:
        """
        Load mistake patterns from repeated-mistakes.md.
        
        Harvested from: ops/scripts/pre_execution_checker.py
        
        Returns:
            List of MistakePattern objects
        """
        mistakes_file = self.root / ".cursor-commands" / "learning" / "failures" / "repeated-mistakes.md"
        
        if not mistakes_file.exists():
            logger.warning("session_startup.mistakes_not_found", path=str(mistakes_file))
            return []
        
        try:
            content = mistakes_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("session_startup.mistakes_read_error", error=str(e))
            return []
        
        # Improved regex pattern (v3.2) - captures all lessons including auto-generated
        # Changes from v3.0:
        # - Allows optional letter suffix on lesson number (15a, 15b)
        # - Captures severity marker after closing ** (group 3)
        # - Uses \n+ to handle multiline content between section headers
        # - Uses lookahead to stop at next lesson or section break
        # - Filters out invalid lessons (e.g., "success patterns")
        # Groups: 1=number, 2=title, 3=severity_marker, 4=mistake, 5=impact, 6=prevention, 7=rule
        lesson_pattern = r'### \*\*(\d+)[a-z]?\.\s*(.*?)\*\*\s*([^\n]*?)\n+\*\*Mistake:\*\*\s*(.*?)\n+\*\*Impact:\*\*\s*(.*?)\n+\*\*Prevention:\*\*\s*(.*?)\n+\*\*Rule:\*\*\s*(.*?)(?=\n+### \*\*|\n+---\n|\Z)'
        matches = re.findall(lesson_pattern, content, re.DOTALL)
        
        patterns: List[MistakePattern] = []
        seen_numbers: set = set()  # Track duplicates
        
        for match in matches:
            lesson_num, title, severity_marker, mistake, impact, prevention, rule = match
            title_clean = title.strip()
            
            # Skip invalid lessons (success patterns are NOT mistakes)
            if "successful solution" in title_clean.lower() or "success pattern" in title_clean.lower():
                logger.debug(
                    "session_startup.skipped_invalid_lesson",
                    lesson_num=lesson_num,
                    reason="success pattern, not a mistake",
                )
                continue
            
            # Determine severity from marker (after **) or title
            severity = "MEDIUM"
            marker_upper = severity_marker.upper()
            if "🚨" in severity_marker or "ULTRA" in marker_upper:
                severity = "ULTRA_CRITICAL"
            elif "🔴" in severity_marker or "CRITICAL" in marker_upper:
                severity = "CRITICAL"
            elif "💎" in severity_marker or "HIGH" in marker_upper:
                severity = "HIGH"
            
            # Determine quality (curated vs auto-generated)
            is_auto_generated = (
                title_clean.endswith("...") or 
                "Pattern detected:" in title_clean or
                "Occurred" in impact
            )
            quality = "auto" if is_auto_generated else "curated"
            
            # Handle duplicate lesson numbers (add suffix)
            num = int(lesson_num)
            lesson_id = f"lesson_{num}"
            if num in seen_numbers:
                # Find unique suffix
                suffix = 'b'
                while f"lesson_{num}{suffix}" in [p.lesson_id for p in patterns]:
                    suffix = chr(ord(suffix) + 1)
                lesson_id = f"lesson_{num}{suffix}"
            seen_numbers.add(num)
            
            patterns.append(MistakePattern(
                lesson_id=lesson_id,
                number=num,
                title=title_clean,
                mistake=mistake.strip(),
                severity=severity,
                keywords=self._extract_keywords(mistake + ' ' + title_clean),
                prevention=prevention.strip(),
                rule=rule.strip(),
            ))
        
        # Count by severity and quality
        ultra_critical = len([p for p in patterns if p.severity == "ULTRA_CRITICAL"])
        critical = len([p for p in patterns if p.severity == "CRITICAL"])
        curated = len([p for p in patterns if not p.title.endswith("...")])
        
        logger.info(
            "session_startup.mistakes_loaded",
            count=len(patterns),
            ultra_critical=ultra_critical,
            critical=critical,
            curated=curated,
        )
        
        return patterns

    def load_critical_rules(self) -> List[CriticalRule]:
        """
        Load critical rules from .cursor/rules/*.mdc files.
        
        These are the 20 most important behavioral constraints, hardcoded
        from the .cursor/rules/ directory for fast startup and reliability.
        
        Version: 3.1.0
        Source files:
        - 92-learned-lessons.mdc (path rules, execution rules)
        - 01-vps-rules.mdc (VPS workflow rules)
        - 90-protected-core.mdc (protected file rules)
        - 60-anti-patterns.mdc (code anti-patterns)
        - 00-global.mdc (safety constraints)
        
        Returns:
            List of CriticalRule objects (20 rules)
        """
        rules = CRITICAL_RULES.copy()
        
        logger.info(
            "session_startup.critical_rules_loaded",
            count=len(rules),
            categories=list(set(r.category for r in rules)),
        )
        
        return rules

    def run_index_export(self) -> tuple[bool, int]:
        """
        Run repository index export (tools/export_repo_indexes.py).
        
        Generates 34 index files including adr_catalog.txt for LLM context.
        
        Version: 3.3.0
        
        Returns:
            Tuple of (success, count_of_files_generated)
        """
        export_script = self.root / "tools" / "export_repo_indexes.py"
        
        if not export_script.exists():
            logger.warning(
                "session_startup.index_export_not_found",
                path=str(export_script),
            )
            return False, 0
        
        try:
            result = subprocess.run(
                ["python3", str(export_script)],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(self.root),
                timeout=120,  # 2 minute timeout
            )
            
            if result.returncode == 0:
                # Count generated files from output or directory
                index_dir = self.root / "readme" / "repo-index"
                if index_dir.exists():
                    count = len([f for f in index_dir.iterdir() if f.suffix == ".txt"])
                else:
                    count = 0
                
                logger.info(
                    "session_startup.index_export_success",
                    count=count,
                    stdout_lines=len(result.stdout.split('\n')) if result.stdout else 0,
                )
                return True, count
            else:
                logger.error(
                    "session_startup.index_export_failed",
                    exit_code=result.returncode,
                    stderr=result.stderr[:500] if result.stderr else "",
                )
                return False, 0
                
        except subprocess.TimeoutExpired:
            logger.error("session_startup.index_export_timeout")
            return False, 0
        except Exception as e:
            logger.error(
                "session_startup.index_export_error",
                error=str(e),
            )
            return False, 0

    def run_command(self, cmd: str, description: str = "") -> CommandResult:
        """
        Run a shell command and return result.
        
        Useful pattern from run_setup_protocol.py for verification commands.
        
        Args:
            cmd: Shell command to run
            description: Human-readable description
            
        Returns:
            CommandResult with stdout, stderr, exit code
        """
        logger.debug("session_startup.run_command", command=cmd, description=description)
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(self.root),
            )
            
            return CommandResult(
                command=cmd,
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except Exception as e:
            logger.error("session_startup.command_failed", command=cmd, error=str(e))
            return CommandResult(
                command=cmd,
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
            )


# Factory function
def create_session_startup(workspace_root: Optional[Path] = None) -> SessionStartup:
    """
    Create a SessionStartup instance.
    
    Args:
        workspace_root: Workspace root (defaults to L9 project)
        
    Returns:
        Configured SessionStartup
    """
    root = workspace_root or Path("/Users/ib-mac/Projects/L9")
    return SessionStartup(root)


__all__ = [
    "SessionStartup",
    "StartupFile",
    "PreflightResult",
    "StartupResult",
    "KernelReadinessResult",
    "MistakePattern",
    "CriticalRule",
    "CRITICAL_RULES",
    "CommandResult",
    "create_session_startup",
]

