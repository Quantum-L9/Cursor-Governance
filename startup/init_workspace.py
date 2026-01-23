#!/usr/bin/env python3
"""
L9 Workspace Initialization Script (Consolidated)
==================================================

Unified workspace initialization that combines:
- L9-native governance module loading (SessionStartup, mistake prevention, etc.)
- Suite 6 workspace setup (symlink management, env-manager, YAML orchestrator)

Usage:
    python .cursor-commands/startup/init_workspace.py
    python .cursor-commands/startup/init_workspace.py --workspace /path/to/workspace
    python .cursor-commands/startup/init_workspace.py --verbose
    python .cursor-commands/startup/init_workspace.py --suite6  # Suite 6 mode
    python .cursor-commands/startup/init_workspace.py --dry-run  # Dry run mode

Returns exit code 0 if READY, 1 if DEGRADED, 2 if BLOCKED.

Version: 2.0.0 (Consolidated)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import structlog

logger = structlog.get_logger(__name__)

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class InitResult:
    """Complete workspace initialization result."""
    
    status: str  # READY, DEGRADED, BLOCKED
    startup_status: str
    suite6_status: Optional[str] = None
    mistakes_loaded: int = 0
    quickfixes_loaded: int = 0
    credentials_patterns: int = 0
    errors: list[str] = None
    warnings: list[str] = None
    duration_ms: int = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# ---------------------------------------------------------------------------
# Suite 6 Functions (from init_workspace_NEW.py)
# ---------------------------------------------------------------------------

def _log(msg: str, *, level: str = "INFO", verbose: bool = True) -> None:
    """Simple logging helper."""
    if not verbose and level == "INFO":
        return
    logger.info(f"[{level}] {msg}")


def ensure_cursor_commands_symlink(
    *,
    workspace_root: Path,
    global_commands_env: str = "CURSOR_GOV_GLOBAL_COMMANDS",
    dry_run: bool = False,
    verbose: bool = False,
    force_resymlink: bool = False,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Ensure `.cursor-commands` is a symlink pointing to the GlobalCommands pack.
    
    Resolution order for target:
        1. $CURSOR_GOV_GLOBAL_COMMANDS (absolute or ~-relative path)
        2. ~/Dropbox/Cursor Governance/GlobalCommands (legacy default)
        3. ./GlobalCommands under workspace_root (fallback)
    
    Returns:
        (success, data, error)
    """
    cwd = workspace_root
    link_path = cwd / ".cursor-commands"
    
    # Resolve target root
    env_target = os.environ.get(global_commands_env, "").strip()
    candidates = []
    
    if env_target:
        candidates.append(Path(env_target).expanduser())
    
    # Legacy default from audit: Dropbox/Cursor Governance/GlobalCommands
    candidates.append(
        Path.home()
        / "Dropbox"
        / "Cursor Governance"
        / "GlobalCommands"
    )
    
    # Fallback: a GlobalCommands directory inside workspace
    candidates.append(cwd / "GlobalCommands")
    
    target: Path | None = None
    for cand in candidates:
        if cand.exists():
            target = cand
            break
    
    if target is None:
        msg = (
            "Could not locate GlobalCommands pack. "
            f"Tried: {[str(c) for c in candidates]}"
        )
        _log(msg, level="ERROR", verbose=verbose)
        return False, {}, msg
    
    _log(f"Resolved GlobalCommands target: {target}", verbose=verbose)
    
    # Check existing link / directory
    if link_path.exists() or link_path.is_symlink():
        # Already correct?
        if link_path.is_symlink():
            try:
                current_target = link_path.resolve()
            except Exception:
                current_target = None
            
            if current_target == target and not force_resymlink:
                _log(
                    f".cursor-commands already points to {current_target}, "
                    "keeping existing symlink.",
                    verbose=verbose,
                )
                return True, {"link": str(link_path), "target": str(target)}, ""
        # Need to remove and recreate?
        if dry_run:
            _log(
                f"[DRY RUN] Would remove existing {link_path} and re-create "
                f"symlink -> {target}",
                verbose=verbose,
            )
            return True, {"link": str(link_path), "target": str(target)}, ""
        else:
            if link_path.is_dir() and not link_path.is_symlink():
                _log(
                    f"Removing existing directory at {link_path} "
                    "to replace with symlink.",
                    verbose=verbose,
                )
            else:
                _log(
                    f"Removing existing entry at {link_path} "
                    "to replace with symlink.",
                    verbose=verbose,
                )
            if link_path.is_dir() and not link_path.is_symlink():
                # Refuse to delete directory contents
                for child in link_path.iterdir():
                    _log(
                        f"Refusing to delete contents of existing directory "
                        f"{link_path}. Please clean up manually.",
                        level="ERROR",
                        verbose=verbose,
                    )
                    return False, {}, (
                        f"Existing non-symlink directory {link_path} detected. "
                        "Clean or move it before running this script."
                    )
                link_path.rmdir()
            else:
                link_path.unlink()
    
    # Create new symlink
    if dry_run:
        _log(
            f"[DRY RUN] Would create symlink {link_path} -> {target}",
            verbose=verbose,
        )
        return True, {"link": str(link_path), "target": str(target)}, ""
    else:
        _log(f"Creating symlink {link_path} -> {target}", verbose=verbose)
        link_path.symlink_to(target, target_is_directory=True)
        return True, {"link": str(link_path), "target": str(target)}, ""


def run_env_manager(
    *,
    workspace_root: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Run environment/env-manager.py to sync workspace configuration and
    ensure `.suite6-config.json` is created or updated.
    """
    env_manager_path = workspace_root / ".cursor-commands" / "environment" / "env-manager.py"
    
    if not env_manager_path.exists():
        msg = f"env-manager.py not found at {env_manager_path}"
        _log(msg, level="ERROR", verbose=verbose)
        return False, {}, msg
    
    cmd = [sys.executable, str(env_manager_path), "sync"]
    _log(f"Prepared env-manager command: {' '.join(cmd)}", verbose=verbose)
    
    if dry_run:
        _log("[DRY RUN] Would execute env-manager sync.", verbose=verbose)
        return True, {"command": cmd}, ""
    else:
        try:
            _log("Running env-manager sync...", verbose=verbose)
            result = subprocess.run(
                cmd,
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                msg = (
                    "env-manager sync failed with exit code "
                    f"{result.returncode}: {result.stderr.strip()}"
                )
                _log(msg, level="ERROR", verbose=verbose)
                return False, {"stdout": result.stdout, "stderr": result.stderr}, msg
            _log("env-manager sync completed successfully.", verbose=verbose)
            return True, {"stdout": result.stdout}, ""
        except Exception as e:
            msg = f"Error running env-manager: {e}"
            _log(msg, level="ERROR", verbose=verbose)
            return False, {}, msg


def run_setup_new_workspace_yaml(
    *,
    workspace_root: Path,
    yaml_path: Path | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Invoke `setup-new-workspace.yaml` orchestrator to perform phased initialization.
    
    The YAML defines phases:
        Phase 1: Python governance (core/governance, env-manager, etc.)
        Phase 2: workflow_state / STATESYNC
        Phase 3: REASONINGSTACK.yaml / reasoning activation
        Phase 4: Reference files, profiles, commands, features
    """
    if yaml_path is None:
        yaml_path = workspace_root / ".cursor-commands" / "setup-new-workspace.yaml"
    
    if not yaml_path.exists():
        msg = f"setup-new-workspace.yaml not found at {yaml_path}"
        _log(msg, level="ERROR", verbose=verbose)
        return False, {}, msg
    
    # Try to use the run_setup_protocol.py script if it exists
    runner_script = workspace_root / ".cursor-commands" / "run_setup_protocol.py"
    
    if runner_script.exists():
        cmd = [sys.executable, str(runner_script)]
        if dry_run:
            _log(
                f"[DRY RUN] Would invoke setup protocol runner: {' '.join(cmd)}",
                verbose=verbose,
            )
            return True, {"yaml": str(yaml_path), "command": cmd}, ""
        else:
            try:
                _log("Running setup-new-workspace.yaml orchestrator...", verbose=verbose)
                result = subprocess.run(
                    cmd,
                    cwd=str(workspace_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    msg = (
                        f"Setup protocol runner failed with exit code "
                        f"{result.returncode}: {result.stderr.strip()}"
                    )
                    _log(msg, level="ERROR", verbose=verbose)
                    return False, {"stdout": result.stdout, "stderr": result.stderr}, msg
                _log("Setup protocol completed successfully.", verbose=verbose)
                return True, {"stdout": result.stdout}, ""
            except Exception as e:
                msg = f"Error running setup protocol: {e}"
                _log(msg, level="ERROR", verbose=verbose)
                return False, {}, msg
    else:
        # Fallback: manual step
        cmd_hint = f"[MANUAL STEP] Execute governance orchestrator for {yaml_path}"
        if dry_run:
            _log(
                f"[DRY RUN] Would invoke workspace orchestrator for {yaml_path}. "
                f"{cmd_hint}",
                verbose=verbose,
            )
            return True, {"yaml": str(yaml_path), "hint": cmd_hint}, ""
        else:
            _log(
                "No automatic YAML runner found. Please execute the configured orchestrator "
                f"for {yaml_path} (e.g., via run_setup_protocol.py).",
                level="WARNING",
                verbose=verbose,
            )
            return True, {"yaml": str(yaml_path), "hint": cmd_hint}, ""


# ---------------------------------------------------------------------------
# L9-Native Functions (from init_workspace.py)
# ---------------------------------------------------------------------------

def init_workspace(
    workspace_root: Path,
    verbose: bool = False,
    suite6_mode: bool = False,
    dry_run: bool = False,
    force_resymlink: bool = False,
) -> InitResult:
    """
    Initialize workspace by loading all governance modules.
    
    Args:
        workspace_root: Path to workspace root
        verbose: Print detailed output
        suite6_mode: Enable Suite 6 initialization (symlink, env-manager, YAML)
        dry_run: Show what would be done without making changes
        force_resymlink: Force re-creation of .cursor-commands symlink
        
    Returns:
        InitResult with complete status
    """
    start_time = datetime.utcnow()
    errors: list[str] = []
    warnings: list[str] = []
    suite6_status: Optional[str] = None
    
    if verbose:
        logger.info(f"\n🚀 Initializing L9 workspace: {workspace_root}\n")
    
    # ─────────────────────────────────────────────────────────────
    # Suite 6 Setup (if enabled)
    # ─────────────────────────────────────────────────────────────
    if suite6_mode:
        if verbose:
            logger.info("📦 Suite 6 Mode: Setting up workspace infrastructure...")
        
        # Step 1: Ensure symlink
        ok, data, err = ensure_cursor_commands_symlink(
            workspace_root=workspace_root,
            dry_run=dry_run,
            verbose=verbose,
            force_resymlink=force_resymlink,
        )
        if not ok:
            errors.append(f"Suite 6 symlink setup FAILED: {err}")
            suite6_status = "BLOCKED"
        else:
            if verbose:
                logger.info(f"✅ Symlink: {data.get('target', 'N/A')}")
        
        # Step 2: Run env-manager
        if ok:
            ok, data, err = run_env_manager(
                workspace_root=workspace_root,
                dry_run=dry_run,
                verbose=verbose,
            )
            if not ok:
                warnings.append(f"env-manager sync FAILED: {err}")
                suite6_status = "DEGRADED"
            else:
                if verbose:
                    logger.info("✅ env-manager sync completed")
        
        # Step 3: Run setup-new-workspace.yaml
        if ok:
            ok, data, err = run_setup_new_workspace_yaml(
                workspace_root=workspace_root,
                dry_run=dry_run,
                verbose=verbose,
            )
            if not ok:
                warnings.append(f"Setup YAML orchestrator FAILED: {err}")
                if suite6_status != "BLOCKED":
                    suite6_status = "DEGRADED"
            else:
                if verbose:
                    logger.info("✅ Setup protocol completed")
        
        if suite6_status is None:
            suite6_status = "READY"
    
    # ─────────────────────────────────────────────────────────────
    # 1. Session Startup (preflight + mandatory files)
    # ─────────────────────────────────────────────────────────────
    try:
        # Try importing from same directory first (we're in .cursor-commands/startup/)
        try:
            from .session_startup import create_session_startup
        except (ImportError, ValueError):
            # Fallback: try absolute import
            import sys
            startup_dir = Path(__file__).parent
            if str(startup_dir) not in sys.path:
                sys.path.insert(0, str(startup_dir.parent))
            from startup.session_startup import create_session_startup
        
        startup = create_session_startup(workspace_root)
        startup_result = startup.execute()
        
        if verbose:
            logger.info(f"📋 Session Startup: {startup_result.status}")
            logger.info(f"   Files loaded: {len(startup_result.files_loaded)}")
            if startup_result.errors:
                for e in startup_result.errors:
                    logger.info(f"   ❌ {e}")
            if startup_result.warnings:
                for w in startup_result.warnings:
                    logger.info(f"   ⚠️  {w}")
        
        errors.extend(startup_result.errors)
        warnings.extend(startup_result.warnings)
        startup_status = startup_result.status
        
    except ImportError:
        # Fallback to core.governance if startup module not found
        try:
            from core.governance import create_session_startup
            
            startup = create_session_startup(workspace_root)
            startup_result = startup.execute()
            
            if verbose:
                logger.info(f"📋 Session Startup: {startup_result.status}")
                logger.info(f"   Files loaded: {len(startup_result.files_loaded)}")
            
            errors.extend(startup_result.errors)
            warnings.extend(startup_result.warnings)
            startup_status = startup_result.status
        except Exception as e:
            errors.append(f"Session Startup FAILED: {e}")
            startup_status = "BLOCKED"
            if verbose:
                logger.info(f"❌ Session Startup FAILED: {e}")
    except Exception as e:
        errors.append(f"Session Startup FAILED: {e}")
        startup_status = "BLOCKED"
        if verbose:
            logger.info(f"❌ Session Startup FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 2. Mistake Prevention (load critical rules)
    # ─────────────────────────────────────────────────────────────
    mistakes_loaded = 0
    try:
        from core.governance import create_mistake_prevention
        
        mistake_engine = create_mistake_prevention()
        mistakes_loaded = len(mistake_engine.rules)
        
        if verbose:
            logger.info(f"\n🛡️  Mistake Prevention: {mistakes_loaded} rules loaded")
            for rule in mistake_engine.rules[:3]:
                logger.info(f"   • {rule.id}: {rule.name}")
            if mistakes_loaded > 3:
                logger.info(f"   ... and {mistakes_loaded - 3} more")
                
    except Exception as e:
        errors.append(f"Mistake Prevention FAILED: {e}")
        if verbose:
            logger.info(f"❌ Mistake Prevention FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 3. Quick Fixes (load remediation patterns)
    # ─────────────────────────────────────────────────────────────
    quickfixes_loaded = 0
    try:
        from core.governance import create_quick_fix_engine
        
        quickfix_engine = create_quick_fix_engine()
        quickfixes_loaded = len(quickfix_engine.fixes)
        
        if verbose:
            logger.info(f"\n🔧 Quick Fix Engine: {quickfixes_loaded} fixes loaded")
            for fix in quickfix_engine.fixes[:3]:
                logger.info(f"   • {fix.id}: {fix.problem[:40]}...")
            if quickfixes_loaded > 3:
                logger.info(f"   ... and {quickfixes_loaded - 3} more")
                
    except Exception as e:
        warnings.append(f"Quick Fix Engine FAILED: {e}")
        if verbose:
            logger.info(f"⚠️  Quick Fix Engine FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 4. Credentials Policy (load secret patterns)
    # ─────────────────────────────────────────────────────────────
    credentials_patterns = 0
    try:
        from core.governance import create_credentials_policy
        
        credentials_policy = create_credentials_policy()
        credentials_patterns = len(credentials_policy.patterns)
        
        if verbose:
            logger.info(f"\n🔐 Credentials Policy: {credentials_patterns} patterns loaded")
            for pattern in credentials_policy.patterns[:3]:
                logger.info(f"   • {pattern.secret_type.value}: {pattern.name}")
            if credentials_patterns > 3:
                logger.info(f"   ... and {credentials_patterns - 3} more")
                
    except Exception as e:
        warnings.append(f"Credentials Policy FAILED: {e}")
        if verbose:
            logger.info(f"⚠️  Credentials Policy FAILED: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # 5. Determine final status
    # ─────────────────────────────────────────────────────────────
    critical_errors = [e for e in errors if "CRITICAL" in e or "BLOCKED" in e or "FAILED" in e]
    
    if critical_errors or startup_status == "BLOCKED" or (suite6_status == "BLOCKED"):
        status = "BLOCKED"
    elif warnings or startup_status == "DEGRADED" or (suite6_status == "DEGRADED"):
        status = "DEGRADED"
    else:
        status = "READY"
    
    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    return InitResult(
        status=status,
        startup_status=startup_status,
        suite6_status=suite6_status,
        mistakes_loaded=mistakes_loaded,
        quickfixes_loaded=quickfixes_loaded,
        credentials_patterns=credentials_patterns,
        errors=errors,
        warnings=warnings,
        duration_ms=duration_ms,
    )


def print_banner(result: InitResult) -> None:
    """Print final status banner."""
    status_icon = {"READY": "✅", "DEGRADED": "⚠️", "BLOCKED": "❌"}.get(result.status, "❓")
    
    logger.info("\n" + "═" * 60)
    logger.info(f"  {status_icon} L9 WORKSPACE INITIALIZATION: {result.status}")
    logger.info("═" * 60)
    
    components = [
        ("Session Startup", result.startup_status),
    ]
    
    if result.suite6_status:
        components.append(("Suite 6 Setup", result.suite6_status))
    
    components.extend([
        ("Mistake Prevention Rules", str(result.mistakes_loaded)),
        ("Quick Fix Patterns", str(result.quickfixes_loaded)),
        ("Credentials Policy Patterns", str(result.credentials_patterns)),
    ])
    
    table_rows = "\n".join([
        f"  │ {name:<35} │ {status:<8} │"
        for name, status in components
    ])
    
    logger.info(f"""
  ┌─────────────────────────────────────┬──────────┐
  │ Component                           │ Status   │
  ├─────────────────────────────────────┼──────────┤
{table_rows}
  └─────────────────────────────────────┴──────────┘
  
  Duration: {result.duration_ms}ms
""")
    
    if result.errors:
        logger.info("  ❌ Errors:")
        for e in result.errors:
            logger.info(f"     • {e}")
        logger.info()
    
    if result.warnings:
        logger.info("  ⚠️  Warnings:")
        for w in result.warnings:
            logger.info(f"     • {w}")
        logger.info()
    
    if result.status == "READY":
        logger.info("  🎯 READY FOR WORK - Python governance enforcement ACTIVE\n")
    elif result.status == "DEGRADED":
        logger.info("  ⚠️  DEGRADED - Some systems unavailable, proceed with caution\n")
    else:
        logger.info("  🛑 BLOCKED - Critical systems failed, resolve before proceeding\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize L9 workspace with Python governance modules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python .cursor-commands/startup/init_workspace.py
  python .cursor-commands/startup/init_workspace.py --verbose
  python .cursor-commands/startup/init_workspace.py --workspace /path/to/l9
  python .cursor-commands/startup/init_workspace.py --suite6  # Suite 6 mode
  python .cursor-commands/startup/init_workspace.py --dry-run  # Dry run
  
Exit Codes:
  0 = READY (all systems operational)
  1 = DEGRADED (some warnings, proceed with caution)
  2 = BLOCKED (critical failures, resolve first)
        """,
    )
    parser.add_argument(
        "--workspace", "-w",
        type=Path,
        default=PROJECT_ROOT,
        help="Workspace root path (default: L9 project root)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only print final status line",
    )
    parser.add_argument(
        "--suite6",
        action="store_true",
        help="Enable Suite 6 initialization (symlink, env-manager, YAML orchestrator)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--force-resymlink",
        action="store_true",
        help="Force re-creation of .cursor-commands symlink even if it exists",
    )
    
    args = parser.parse_args()
    
    result = init_workspace(
        args.workspace,
        verbose=args.verbose,
        suite6_mode=args.suite6,
        dry_run=args.dry_run,
        force_resymlink=args.force_resymlink,
    )
    
    if args.quiet:
        logger.info(f"{result.status}")
    else:
        print_banner(result)
    
    # Return exit code based on status
    return {"READY": 0, "DEGRADED": 1, "BLOCKED": 2}.get(result.status, 2)


if __name__ == "__main__":
    sys.exit(main())
