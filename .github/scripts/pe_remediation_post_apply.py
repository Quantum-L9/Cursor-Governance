#!/usr/bin/env python3
"""Idempotent mechanical repair after the approved PE source patch."""
from __future__ import annotations

from pathlib import Path


def update(path: str, fn) -> None:
    p = Path(path)
    before = p.read_text(encoding='utf-8')
    after = fn(before)
    if after != before:
        p.write_text(after, encoding='utf-8')


def restore_hashlib(text: str) -> str:
    if 'hashlib.sha256' not in text or 'import hashlib' in text:
        return text
    marker = 'from __future__ import annotations\n\n'
    if marker not in text:
        raise SystemExit('post-apply: future import anchor missing')
    return text.replace(marker, marker + 'import hashlib\n', 1)


def remove_stale_projection_refs(text: str) -> str:
    lines = []
    for line in text.splitlines(keepends=True):
        if '*projection_errors,' in line:
            continue
        if '"GENERATED_ARTIFACTS_CURRENT": "PASS" if not projection_errors else "FAIL",' in line:
            continue
        lines.append(line)
    return ''.join(lines)


update(
    'environment/program-execution/scripts/tests/test_validate_campaign_promotion.py',
    restore_hashlib,
)
update(
    'environment/program-execution/scripts/validate_campaign_promotion.py',
    remove_stale_projection_refs,
)
Path('.github/pe-executor-failure.txt').unlink(missing_ok=True)
print('post-apply lint repair complete')
