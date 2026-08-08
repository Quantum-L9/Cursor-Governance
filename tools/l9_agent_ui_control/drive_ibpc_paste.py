#!/usr/bin/env python3
"""Activate Windows App (IB-PC) and paste+execute text via keystrokes."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time


def activate_ibpc() -> None:
    subprocess.run(
        ["osascript", "-e", 'tell application "Windows App" to activate'],
        check=False,
    )
    time.sleep(0.4)
    # Click roughly center of main display to focus the RDP surface
    try:
        import pyautogui

        w, h = pyautogui.size()
        pyautogui.click(w // 2, h // 2)
        time.sleep(0.3)
    except Exception as exc:  # noqa: BLE001
        print(f"click_warn: {exc}", file=sys.stderr)


def paste_text(text: str) -> None:
    proc = subprocess.run(
        ["pbcopy"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pbcopy failed: {proc.stderr}")
    import pyautogui

    # Windows App usually maps Mac Cmd → Ctrl inside the session for paste
    pyautogui.hotkey("command", "v")
    time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default=None)
    parser.add_argument("--file", default=None)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Press F5 after paste (SSMS / ADS execute)",
    )
    parser.add_argument(
        "--enter",
        action="store_true",
        help="Press Enter after paste (PowerShell)",
    )
    args = parser.parse_args()
    text = args.text
    if args.file:
        text = open(args.file, encoding="utf-8").read()
    if not text:
        print("need --text or --file", file=sys.stderr)
        return 2

    activate_ibpc()
    paste_text(text)
    import pyautogui

    if args.execute:
        pyautogui.press("f5")
    if args.enter:
        pyautogui.press("enter")
    print("dispatched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
