#!/usr/bin/env python3
"""One-shot continuation repair for the temporary PE remediation executor."""
from __future__ import annotations

from pathlib import Path

PATCHER = Path('.github/scripts/pe_remediation_apply.py')
text = PATCHER.read_text(encoding='utf-8')

old_helpers = """def replace_once(path: str, old: str, new: str) -> None:\n    text = read(path)\n    count = text.count(old)\n    if count != 1:\n        raise SystemExit(f'{path}: expected exactly one anchor, found {count}: {old[:120]!r}')\n    write(path, text.replace(old, new, 1))\n\n\ndef regex_once(path: str, pattern: str, replacement: str, *, flags: int = 0) -> None:\n    text = read(path)\n    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)\n    if count != 1:\n        raise SystemExit(f'{path}: expected exactly one regex anchor, found {count}: {pattern[:120]!r}')\n    write(path, updated)\n"""
new_helpers = """def replace_once(path: str, old: str, new: str) -> None:\n    text = read(path)\n    if path == \"environment/program-execution/scripts/run_campaign.py\" and \"def _default_execute_peer(\" in text:\n        return\n    count = text.count(old)\n    if count != 1:\n        raise SystemExit(f'{path}: expected exactly one anchor, found {count}: {old[:120]!r}')\n    write(path, text.replace(old, new, 1))\n\n\ndef regex_once(path: str, pattern: str, replacement: str, *, flags: int = 0) -> None:\n    text = read(path)\n    if path == \"environment/program-execution/scripts/run_campaign.py\" and \"def _default_execute_peer(\" in text:\n        return\n    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)\n    if count != 1:\n        raise SystemExit(f'{path}: expected exactly one regex anchor, found {count}: {pattern[:120]!r}')\n    write(path, updated)\n"""
if old_helpers in text:
    text = text.replace(old_helpers, new_helpers, 1)
elif 'and "def _default_execute_peer(" in text' not in text:
    raise SystemExit('resume: helper anchor drift')

old_worker = """replace_once(\n    WORKER,\n    '\"\"\"Provider-neutral worker handoff for Program Execution tasks.\\n',\n    '\"\"\"Legacy direct-worker compatibility shim.\\n\\nThe live `make campaign` path executes through Peer Execution Core. This module\\nis retained only for deterministic embedding/tests that intentionally own the\\nwrite seam; it is not a canonical production dispatcher.\\n\\n',\n)"""
new_worker = """regex_once(\n    WORKER,\n    r'\\A#!/usr/bin/env python3\\n\"\"\".*?\"\"\"\\n',\n    '#!/usr/bin/env python3\\n\"\"\"Legacy direct-worker compatibility shim.\\n\\n'\n    'The live `make campaign` path executes through Peer Execution Core. This module\\n'\n    'is retained only for deterministic embedding/tests that intentionally own the\\n'\n    'write seam; it is not a canonical production dispatcher.\\n\"\"\"\\n',\n    flags=re.S,\n)"""
if old_worker in text:
    text = text.replace(old_worker, new_worker, 1)
elif 'Legacy direct-worker compatibility shim' not in text:
    raise SystemExit('resume: worker anchor drift')

PATCHER.write_text(text, encoding='utf-8')
Path('.github/pe-executor-failure.txt').unlink(missing_ok=True)
print('resume patch applied')
