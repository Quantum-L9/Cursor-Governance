#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/test_validators.py
#   layer: test
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-07-28
"""Self-test for validate_agents.py and render_principals.py.

Positive: real pack passes; principals render for all 5 agents with correct
role grants. Negative: mutated registries (duplicate user_id, bad naming,
unknown role, committed secret, shared token) must FAIL. Exit 0 = all pass.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
PY = sys.executable
results: list[tuple[str, bool, str]] = []


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def case(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail and not ok else ""))


def mutated_pack(mutate) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="l9vtest_"))
    dst = tmp / "pack"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("__pycache__", "test_validators.py"))
    reg = dst / "agent_registry.yaml"
    reg.write_text(mutate(reg.read_text(encoding="utf-8")), encoding="utf-8")
    return dst


def main() -> int:
    # T1 positive: real pack validates
    r = run([PY, str(TOOLS / "validate_agents.py"), "--root", str(ROOT)])
    case("T1 real pack passes validator", r.returncode == 0, r.stderr.strip())

    # T2 positive: principals render for all agents incl. planned
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        tokmap = out_dir / "tok.json"
        tokmap.write_text(
            json.dumps(
                {
                    a: f"tok_{a}_{'x' * 24}"
                    for a in ["cursor", "claude-code", "manus", "codex", "gemini"]
                }
            )
        )
        out = out_dir / "auth_tokens.json"
        r = run(
            [
                PY,
                str(TOOLS / "render_principals.py"),
                "--root",
                str(ROOT),
                "--out-dir",
                str(out_dir),
                "--registry",
                "agent_registry.yaml",
                "--tokens",
                "tok.json",
                "--out",
                "auth_tokens.json",
                "--include-planned",
            ]
        )
        ok = r.returncode == 0
        detail = r.stderr.strip()
        if ok:
            d = json.loads(out.read_text())
            ids = sorted(p["agent_id"] for p in d.values())
            gem = next(p for p in d.values() if p["agent_id"] == "gemini")
            man = next(p for p in d.values() if p["agent_id"] == "manus")
            ok = (
                ids == ["claude-code", "codex", "cursor", "gemini", "manus"]
                and gem["write_namespaces"]
                == ["cursor-governance.reviews", "l9-graphiti-memory.reviews"]
                and "igor-workspace" in man["write_namespaces"]
                and all(len(p["user_id"]) and p["user_id"].endswith("_agent") for p in d.values())
            )
            detail = f"agents={ids}"
        case("T2 principals render with role-correct grants", ok, detail)

        # T3 negative: shared token must fail render
        tokmap.write_text(
            json.dumps(
                {
                    a: "sharedsharedsharedsharedshared"
                    for a in ["cursor", "claude-code", "manus", "codex", "gemini"]
                }
            )
        )
        r = run(
            [
                PY,
                str(TOOLS / "render_principals.py"),
                "--root",
                str(ROOT),
                "--out-dir",
                str(out_dir),
                "--registry",
                "agent_registry.yaml",
                "--tokens",
                "tok.json",
                "--out",
                "auth_tokens.json",
                "--include-planned",
            ]
        )
        case(
            "T3 shared token rejected",
            r.returncode != 0 and "share a token" in r.stderr,
            r.stderr.strip(),
        )

        # T3b negative: absolute --tokens path rejected
        r = run(
            [
                PY,
                str(TOOLS / "render_principals.py"),
                "--root",
                str(ROOT),
                "--out-dir",
                str(out_dir),
                "--tokens",
                str(tokmap),  # absolute — must fail
                "--include-planned",
            ]
        )
        case(
            "T3b absolute --tokens rejected",
            r.returncode != 0 and ("relative" in r.stderr or "basename" in r.stderr),
            r.stderr.strip(),
        )

        # T3c negative: .. escape in --out rejected
        r = run(
            [
                PY,
                str(TOOLS / "render_principals.py"),
                "--root",
                str(ROOT),
                "--out-dir",
                str(out_dir),
                "--tokens",
                "tok.json",
                "--out",
                "../escape.json",
                "--include-planned",
            ]
        )
        case(
            "T3c --out path escape rejected",
            r.returncode != 0
            and (".." in r.stderr or "escape" in r.stderr or "basename" in r.stderr),
            r.stderr.strip(),
        )

    # T4 negative: duplicate user_id
    p = mutated_pack(lambda t: t.replace("user_id: manus_agent", "user_id: cursor_agent"))
    r = run([PY, str(TOOLS / "validate_agents.py"), "--root", str(p)])
    case(
        "T4 duplicate user_id rejected",
        r.returncode == 1 and ("duplicate" in r.stderr or "!=" in r.stderr),
        r.stderr.strip(),
    )
    shutil.rmtree(p.parent.parent if p.name == "pack" else p.parent, ignore_errors=True)

    # T5 negative: unknown role
    p = mutated_pack(lambda t: t.replace("role: researcher-builder", "role: superuser"))
    r = run([PY, str(TOOLS / "validate_agents.py"), "--root", str(p)])
    case(
        "T5 unknown role rejected",
        r.returncode == 1 and "unknown role" in r.stderr,
        r.stderr.strip(),
    )
    shutil.rmtree(p.parent, ignore_errors=True)

    # T6 negative: naming-law break (source != agent_id)
    p = mutated_pack(lambda t: t.replace("source: codex", "source: codex-bot"))
    r = run([PY, str(TOOLS / "validate_agents.py"), "--root", str(p)])
    case(
        "T6 naming-law violation rejected", r.returncode == 1 and "R3" in r.stderr, r.stderr.strip()
    )
    shutil.rmtree(p.parent, ignore_errors=True)

    # T7 negative: committed secret detected
    # Built at runtime so this file never contains a secret-like literal.
    fake = "AbCdEfGh" + "IjKlMnOp" + "QrStUvWxYz123456"
    p = mutated_pack(lambda t: t + f'\n# leaked\nleak_token: "{fake}"\n')
    r = run([PY, str(TOOLS / "validate_agents.py"), "--root", str(p)])
    case("T7 committed secret rejected", r.returncode == 1 and "S1" in r.stderr, r.stderr.strip())
    shutil.rmtree(p.parent, ignore_errors=True)

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} tests passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
