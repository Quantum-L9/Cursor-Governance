#!/usr/bin/env python3
"""
Agent UI Control runner — standalone local file-queue worker.

No hard deps on orchestrators.*, api.slack_client, core.decorators, or
integrations.mac_agent.*. Every completion persists a non-empty result payload.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc  # py<3.11
from pathlib import Path
from typing import Any

# Ensure tools/ parent is on path so `import l9_agent_ui_control` works when
# LaunchAgent invokes this file by absolute path.
_PACK_DIR = Path(__file__).resolve().parent
_TOOLS_DIR = _PACK_DIR.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import structlog

from l9_agent_ui_control.config import get_config
from l9_agent_ui_control.task_queue import get_next_task, mark_task_completed


def must_stay_async(reason: str = ""):
    """No-op decorator stub (standalone; no core.decorators)."""

    def decorator(fn):
        return fn

    return decorator


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = structlog.get_logger(__name__)


def _soft_post_result(channel: str | None, task: dict[str, Any], result: dict[str, Any]) -> None:
    """Best-effort notify — never hard-fails the runner (Slack optional)."""
    logger.info(
        "agent_ui_control.task_complete",
        task_id=task.get("task_id"),
        status=result.get("status"),
        channel=channel,
    )
    try:
        from api.slack_client import post_result_async  # type: ignore

        # Soft import only; do not schedule if no running loop / client
        if channel and asyncio.get_event_loop().is_running():
            asyncio.ensure_future(post_result_async(channel, task, result))
    except Exception:
        pass


def _resolve_argv(
    cmd: str | None = None, argv: list[str] | None = None
) -> list[str]:
    """Build argv for subprocess with shell=False (no shell injection surface)."""
    if argv:
        if not all(isinstance(x, str) for x in argv):
            raise ValueError("argv must be a list of strings")
        return list(argv)
    if not cmd or not str(cmd).strip():
        raise ValueError("shell task missing cmd/argv")
    # Tokenize trusted Cursor-authored command; callers needing shell operators
    # must enqueue argv=["/bin/bash", "-c", "<script>"] explicitly.
    return shlex.split(str(cmd), posix=True)


def execute_shell(
    cmd: str | None = None,
    cwd: str | None = None,
    timeout: float = 120.0,
    argv: list[str] | None = None,
) -> dict[str, Any]:
    """Run a command via argv list (shell=False). Returns a result payload."""
    display = cmd or (shlex.join(argv) if argv else "")
    try:
        args = _resolve_argv(cmd=cmd, argv=argv)
        if not args:
            raise ValueError("empty argv")
        proc = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd or None,
            timeout=timeout,
            check=False,
        )
        status = "done" if proc.returncode == 0 else "error"
        return {
            "status": status,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "exit_code": proc.returncode,
            "cmd": display,
            "argv": args,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "error",
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {timeout}s",
            "exit_code": 124,
            "cmd": display,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(exc),
            "exit_code": 1,
            "cmd": display,
        }


def execute_sql_studio(sql: str) -> dict[str, Any]:
    """
    GUI fallback: paste SQL into the frontmost SQL client and execute (Cmd+E / F5).

    Prefer shell/sqlcmd for bulk extract. This path requires Accessibility + an
    open SSMS or Azure Data Studio window.
    """
    try:
        import pyautogui
    except ImportError as exc:
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"sql-studio GUI deps missing: {exc}",
            "exit_code": 1,
            "sql_len": len(sql),
        }

    try:
        # Activate likely SQL Studio apps (best-effort)
        for app in ("Azure Data Studio", "Microsoft SQL Server Management Studio", "SSMS"):
            subprocess.run(
                ["osascript", "-e", f'tell application "{app}" to activate'],
                capture_output=True,
                check=False,
            )

        time.sleep(0.4)
        proc = subprocess.run(
            ["pbcopy"],
            input=sql,
            text=True,
            check=False,
            capture_output=True,
        )
        if proc.returncode != 0:
            return {
                "status": "error",
                "stdout": "",
                "stderr": f"pbcopy failed: {proc.stderr}",
                "exit_code": proc.returncode,
                "sql_len": len(sql),
            }
        pyautogui.hotkey("command", "n")  # new query tab when supported
        time.sleep(0.2)
        pyautogui.hotkey("command", "v")
        time.sleep(0.2)
        # ADS/SSMS: F5 execute (Windows App RDP may remap)
        pyautogui.press("f5")
        return {
            "status": "done",
            "stdout": "sql typed+execute dispatched to frontmost SQL client",
            "stderr": "",
            "exit_code": 0,
            "sql_len": len(sql),
            "note": "verify results in SQL client; prefer shell/sqlcmd for extracts",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(exc),
            "exit_code": 1,
            "sql_len": len(sql),
        }


async def _run_gui_steps(task: dict[str, Any]) -> dict[str, Any]:
    from l9_agent_ui_control.executor import AutomationExecutor

    steps = task.get("steps") or []
    if not steps:
        return {
            "status": "error",
            "stdout": "",
            "stderr": "no steps",
            "exit_code": 1,
        }
    executor = AutomationExecutor()
    cfg = get_config()
    raw = await executor.run_steps(
        steps, headless=cfg.playwright_headless, task_id=task.get("task_id")
    )
    # Normalize to result contract
    return {
        "status": raw.get("status", "done"),
        "stdout": raw.get("stdout", "") or str(raw.get("data") or ""),
        "stderr": raw.get("stderr", "")
        or (raw.get("data", {}) or {}).get("error", "")
        or "",
        "exit_code": 0 if raw.get("status") in ("done", "success", None) else 1,
        "logs": raw.get("logs", []),
        "screenshots": raw.get("screenshots", []),
    }


@must_stay_async("callers use await")
async def poll_and_execute() -> None:
    """Main polling loop (file-based task system)."""
    cfg = get_config()
    if not cfg.enabled:
        logger.info("Agent UI Control disabled (L9_AGENT_UI_ENABLED=false). Exiting.")
        sys.exit(0)

    logger.info(
        "Agent UI Control runner starting (mode=%s). Polling ~/.l9/mac_tasks every %ss",
        cfg.mode,
        cfg.poll_interval,
    )

    try:
        import pyautogui

        pyautogui_available = True
    except ImportError:
        pyautogui_available = False
        logger.warning("pyautogui not available - desktop screenshots disabled")

    while True:
        task: dict[str, Any] | None = None
        task_id: str | None = None
        try:
            task = get_next_task()
            if not task:
                await asyncio.sleep(cfg.poll_interval)
                continue

            task_id = task.get("task_id", "unknown")
            task_type = task.get("type", "shell")
            logger.info("Executing task %s type=%s", task_id, task_type)

            if task_type == "shell":
                cmd = task.get("cmd") or task.get("command") or None
                argv = task.get("argv")
                if isinstance(argv, list):
                    argv = [str(x) for x in argv]
                else:
                    argv = None
                if not cmd and not argv:
                    result = {
                        "status": "error",
                        "stdout": "",
                        "stderr": "shell task missing cmd/argv",
                        "exit_code": 1,
                    }
                else:
                    result = execute_shell(
                        cmd=cmd,
                        argv=argv,
                        cwd=task.get("cwd"),
                        timeout=float(task.get("timeout", 120)),
                    )
            elif task_type in ("sql_studio", "sql-studio"):
                sql = task.get("sql") or ""
                if not sql and task.get("file"):
                    sql = Path(task["file"]).read_text()
                if not sql:
                    result = {
                        "status": "error",
                        "stdout": "",
                        "stderr": "sql-studio task missing sql/file",
                        "exit_code": 1,
                    }
                else:
                    result = await asyncio.to_thread(execute_sql_studio, sql)
            elif task_type in ("mac_task", "gui", "browser"):
                result = await _run_gui_steps(task)
            elif task.get("steps"):
                result = await _run_gui_steps(task)
            else:
                result = {
                    "status": "error",
                    "stdout": "",
                    "stderr": f"unknown task type: {task_type}",
                    "exit_code": 1,
                }

            if result.get("status") == "error" and pyautogui_available:
                try:
                    shot_dir = Path.home() / ".l9" / "mac_tasks" / "screenshots" / task_id
                    shot_dir.mkdir(parents=True, exist_ok=True)
                    shot = shot_dir / f"error_{int(time.time())}.png"
                    pyautogui.screenshot(str(shot))
                    result["screenshots"] = [str(shot)]
                except Exception:
                    logger.debug("agent_ui_control.screenshot_failed")

            meta = task.get("metadata") or {}
            channel = meta.get("channel") or meta.get("user")
            if channel:
                _soft_post_result(channel, task, result)

            mark_task_completed(task_id, result)
            logger.info(
                "Task %s completed status=%s", task_id, result.get("status")
            )

        except KeyboardInterrupt:
            logger.info("Agent UI Control runner stopped by user")
            sys.exit(0)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error processing task %s: %s",
                task_id or "unknown",
                exc,
                exc_info=True,
            )
            if task_id:
                mark_task_completed(
                    task_id,
                    {
                        "status": "error",
                        "stdout": "",
                        "stderr": f"Runner error: {exc}",
                        "exit_code": 1,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
            await asyncio.sleep(cfg.poll_interval)


def main() -> None:
    try:
        asyncio.run(poll_and_execute())
    except KeyboardInterrupt:
        logger.info("Agent UI Control runner stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
