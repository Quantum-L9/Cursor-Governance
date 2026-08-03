from __future__ import annotations

from pathlib import Path

from adapters.common.imports import load_module

_module = load_module(Path(__file__).with_name("driver.py"), "pes_claude_direct_driver")
ClaudeCodeDirectAdapter = _module.ClaudeCodeDirectAdapter
