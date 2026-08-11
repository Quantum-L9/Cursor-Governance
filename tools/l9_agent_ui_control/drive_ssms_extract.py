#!/usr/bin/env python3
"""SSMS extract via Windows App → IB-PC (Results to Grid only).

Canonical flow (do not invent alternatives):
  1. Raise IB-PC window (never the Devices list).
  2. Focus SQL editor (UPPER pane) → clear → paste query.
  3. Execute (F5 / play). Leave Results to Grid — never Ctrl+T / Results to File.
  4. Focus results grid (LOWER pane) → Ctrl+A → Ctrl+Shift+C (Copy with Headers).
  5. Read Mac clipboard (RDP sync) → write file.

Hard lessons:
  - Cmd+N types literal `n` — never use New Query hotkey.
  - Alt menus often type into the editor — do not use.
  - Selecting in the UPPER pane copies the query — reject that clipboard.
  - Copy with Headers shortcut is Ctrl+Shift+C (maps as Cmd+Shift+C).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

# IB-PC session geometry is typically full client under Windows App chrome.
# Fractions of the Mac screen for a maximized IB-PC RDP surface.
_EDITOR_Y_FRAC = 0.38  # upper: SQL editor
_RESULTS_Y_FRAC = 0.78  # lower: Results grid (below splitter)
_CONTENT_X_FRAC = 0.55  # right of OE / left rail


def raise_ibpc_window() -> None:
    script = """
tell application "Windows App" to activate
delay 0.25
tell application "System Events"
  tell process "Windows App"
    repeat with w in windows
      try
        if (name of w as text) contains "IB-PC" then
          perform action "AXRaise" of w
          return "ok"
        end if
      end try
    end repeat
  end tell
end tell
return "missing"
"""
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if "ok" not in (proc.stdout or ""):
        print(f"warn: IB-PC raise failed: {proc.stdout!r}", file=sys.stderr)


def activate_ibpc() -> tuple[int, int]:
    raise_ibpc_window()
    time.sleep(0.35)
    import pyautogui

    w, h = pyautogui.size()
    return w, h


def _click_frac(w: int, h: int, xf: float, yf: float, *, right: bool = False) -> None:
    import pyautogui

    x = max(200, int(w * xf))
    y = max(100, int(h * yf))
    if right:
        pyautogui.click(x, y, button="right")
    else:
        pyautogui.click(x, y)
    time.sleep(0.2)


def focus_query_editor(w: int, h: int) -> None:
    """UPPER pane — SQL editor only."""
    _click_frac(w, h, _CONTENT_X_FRAC, _EDITOR_Y_FRAC)


def focus_results_grid(w: int, h: int) -> None:
    """LOWER pane — Results grid only (never the editor)."""
    _click_frac(w, h, _CONTENT_X_FRAC, _RESULTS_Y_FRAC)
    time.sleep(0.15)


def clear_editor() -> None:
    import pyautogui

    pyautogui.hotkey("command", "a")
    time.sleep(0.12)
    pyautogui.press("delete")
    time.sleep(0.12)


def paste_text(text: str) -> None:
    proc = subprocess.run(["pbcopy"], input=text, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"pbcopy failed: {proc.stderr}")
    import pyautogui

    pyautogui.hotkey("command", "v")
    time.sleep(0.35)


def execute_query() -> None:
    """Play / Execute. F5 only — keep Results to Grid."""
    import pyautogui

    pyautogui.press("f5")
    time.sleep(0.25)


def copy_results_with_headers(w: int, h: int) -> None:
    """LOWER grid: Select All → Copy with Headers (Ctrl+Shift+C)."""
    import pyautogui

    focus_results_grid(w, h)
    # Select all cells in the grid (focus must already be results)
    pyautogui.hotkey("command", "a")
    time.sleep(0.25)
    # SSMS: Copy with Headers = Ctrl+Shift+C → Cmd+Shift+C under Windows App
    pyautogui.hotkey("command", "shift", "c")
    time.sleep(0.7)


def read_mac_clipboard() -> str:
    proc = subprocess.run(["pbpaste"], capture_output=True, text=True, check=False)
    return proc.stdout or ""


_SQL_LOOKS = re.compile(
    r"^\s*(SET\s+NOCOUNT|SELECT\s|/\*|USE\s|DECLARE\s)",
    re.IGNORECASE | re.MULTILINE,
)


def looks_like_sql(text: str) -> bool:
    """True if we accidentally copied the editor instead of the grid."""
    head = text.lstrip()[:200]
    return bool(_SQL_LOOKS.match(head))


def looks_like_grid(text: str) -> bool:
    """Heuristic: TSV/CSV with a header line and at least one data line."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    if looks_like_sql(text):
        return False
    # header usually has tabs or commas and no SQL keywords as whole line
    return ("\t" in lines[0]) or ("," in lines[0]) or (len(lines[0].split()) >= 2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SSMS Grid extract: paste → F5 → lower grid → Ctrl+Shift+C"
    )
    parser.add_argument("--file", help="SQL file to paste into editor")
    parser.add_argument("--text", help="SQL text to paste into editor")
    parser.add_argument("--out", required=True, type=Path, help="Mac output path")
    parser.add_argument(
        "--wait-exec",
        type=float,
        default=6.0,
        help="Seconds after F5 before copying results",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear editor before paste",
    )
    parser.add_argument(
        "--copy-only",
        action="store_true",
        help="Skip paste/execute; only copy lower Results grid",
    )
    parser.add_argument("--min-chars", type=int, default=8)
    args = parser.parse_args()

    sql = args.text
    if args.file:
        sql = Path(args.file).read_text(encoding="utf-8")

    w, h = activate_ibpc()

    if not args.copy_only:
        if not sql:
            print("need --file or --text unless --copy-only", file=sys.stderr)
            return 2
        focus_query_editor(w, h)
        if not args.no_clear:
            clear_editor()
        paste_text(sql)
        execute_query()
        time.sleep(max(0.5, args.wait_exec))

    marker = f"__L9_CLIP_MARKER_{int(time.time())}__"
    subprocess.run(["pbcopy"], input=marker, text=True, check=False)
    time.sleep(0.2)

    w, h = activate_ibpc()
    copy_results_with_headers(w, h)
    time.sleep(0.5)
    clip = read_mac_clipboard()

    if clip.strip() == marker or len(clip.strip()) < args.min_chars:
        print(
            "FAIL: clipboard unchanged after Ctrl+Shift+C (results not focused?)",
            file=sys.stderr,
        )
        return 1
    if looks_like_sql(clip):
        print(
            "FAIL: clipboard is SQL (copied EDITOR not RESULTS grid). "
            "Re-run with --copy-only after Results grid is visible.",
            file=sys.stderr,
        )
        return 1
    if not looks_like_grid(clip):
        print(
            "FAIL: clipboard does not look like a result grid "
            f"(len={len(clip)} head={clip[:60]!r})",
            file=sys.stderr,
        )
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(clip, encoding="utf-8")
    nz = sum(1 for b in clip.encode("utf-8", errors="replace") if b != 0)
    print(
        f"OK wrote {args.out} chars={len(clip)} nonzero≈{nz} grid_lines={clip.count(chr(10)) + 1}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
