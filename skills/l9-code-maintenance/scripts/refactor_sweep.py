#!/usr/bin/env python3
"""Deterministic read-only refactor-sweep analyzer for l9-code-maintenance.

Purpose: discovery → classification → impact → governance decision → report.
Never mutates the repository. Always dry-run.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PROTECTED_EXACT = {
    "CANONICAL_LAW.md",
    "AGENTS.md",
    "ORG_INVARIANTS.yaml",
    "ops/hooks/session_start_bootstrap.sh",
    "ops/scripts/resolve_governance_paths.sh",
    "ops/scripts/backup_to_github.sh",
    "core/agents/executor.py",
    "runtime/websocket_orchestrator.py",
    "memory/substrate_service.py",
    "docker-compose.yml",
    "Dockerfile",
}

PROTECTED_PREFIXES = (
    "environment/program-execution/core/shared/",
    "autonomy/",
    "environment/claude-code/autonomy/",
)

NON_MECHANICAL_MARKERS = (
    "relocate",
    "move ",
    "rename program",
    "program→campaign",
    "program->campaign",
    "schema",
    "$id",
    "coding/campaigns",
    "layout",
    "ownership",
    "authority",
    "bridge",
    "folder",
    "directory",
    "contract",
)


@dataclass
class Hit:
    file: str
    line: int
    match: str
    layer: str
    protected: bool


@dataclass
class SweepResult:
    intent: str
    files_affected: int
    instances_found: int
    layers_touched: list[str]
    protected_files: list[str]
    mechanical_only: bool
    async_boundary_affected: bool
    import_graph_change: bool
    public_contract_change: bool
    autonomy_do_not_move: bool
    governance_decision: str
    next_step: str
    hits: list[Hit] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _classify_layer(path: str) -> str:
    if path.startswith("ops/hooks/") or path.startswith("ops/scripts/"):
        return "bootstrap"
    if path.startswith("environment/program-execution/"):
        return "program-execution"
    if path.startswith("autonomy/") or path.startswith("environment/claude-code/autonomy/"):
        return "autonomy"
    if path.startswith("skills/") or path.startswith("commands/") or path.startswith("rules/"):
        return "governance"
    if path.startswith("workflows/"):
        return "runtime"
    if path in {"CANONICAL_LAW.md", "AGENTS.md", "ORG_INVARIANTS.yaml"}:
        return "law"
    return "other"


def _is_protected(path: str) -> bool:
    if path in PROTECTED_EXACT:
        return True
    if any(path.startswith(p) for p in PROTECTED_PREFIXES):
        return True
    if "/schemas/" in path and "program-execution" in path:
        return True
    if path.endswith(".schema.json") and "program-execution" in path:
        return True
    return False


def _intent_tokens(intent: str) -> list[str]:
    tokens: list[str] = []
    lower = intent.lower()
    # Always search high-signal markers when present in intent.
    mapping = [
        ("program-execution", r"program-execution"),
        ("execution-governance", r"execution-governance"),
        ("generated-data", r"generated-data|subagent-generated-data"),
        ("coding/campaigns", r"coding/campaigns"),
        ("campaign", r"\bcampaign\b"),
        ("program lock", r"Program Lock|program_lock|program-lock"),
        ("autonomy", r"\bautonomy\b"),
    ]
    for key, pattern in mapping:
        if key in lower or key.replace("-", " ") in lower or key.split("/")[-1] in lower:
            tokens.append(pattern)
    # Generic quoted phrases
    tokens.extend(re.findall(r'"([^"]+)"', intent))
    tokens.extend(re.findall(r"'([^']+)'", intent))
    if not tokens:
        # fallback: significant words length>=5
        tokens = [re.escape(w) for w in re.findall(r"[A-Za-z0-9_./-]{5,}", intent)][:8]
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:12]


_SKIP_DIR_NAMES = {".git", ".venv", "node_modules", "__pycache__", "WIP"}


def _should_skip_path(path: Path) -> bool:
    return any(part in _SKIP_DIR_NAMES for part in path.parts)


def _rg_python(pattern: str, root: Path) -> list[tuple[str, int, str]]:
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)
    hits: list[tuple[str, int, str]] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file() or _should_skip_path(file_path.relative_to(root)):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = str(file_path.relative_to(root))
        for line_no, content in enumerate(lines, start=1):
            if regex.search(content):
                hits.append((rel, line_no, content.strip()[:200]))
    return hits


def _rg(pattern: str, root: Path) -> list[tuple[str, int, str]]:
    if shutil.which("rg") is None:
        return _rg_python(pattern, root)
    cmd = [
        "rg",
        "-n",
        "--no-heading",
        "-S",
        pattern,
        str(root),
        "--glob",
        "!**/.venv/**",
        "--glob",
        "!**/node_modules/**",
        "--glob",
        "!**/.git/**",
        "--glob",
        "!**/__pycache__/**",
        "--glob",
        "!**/WIP/**",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode not in (0, 1):
        return _rg_python(pattern, root)
    hits: list[tuple[str, int, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, ln, content = parts[0], parts[1], parts[2]
        try:
            line_no = int(ln)
        except ValueError:
            continue
        try:
            rel = str(Path(path).resolve().relative_to(root))
        except Exception:
            rel = path.replace(str(root) + "/", "")
        hits.append((rel, line_no, content.strip()[:200]))
    return hits


def analyze(intent: str, root: Path | None = None) -> SweepResult:
    root = root or REPO_ROOT
    intent_l = intent.lower()
    mechanical = not any(m in intent_l for m in NON_MECHANICAL_MARKERS)
    public_contract = any(
        x in intent_l
        for x in (
            "schema",
            "$id",
            "contract",
            "program→campaign",
            "program->campaign",
            "rename program",
        )
    )
    import_graph = any(x in intent_l for x in ("relocate", "move ", "coding/campaigns", "import"))
    autonomy_keep = "autonomy" in intent_l and (
        "keep" in intent_l
        or "callable" in intent_l
        or "do not move" in intent_l
        or "don't move" in intent_l
        or "remain" in intent_l
        or "calls root" in intent_l
        or "call root" in intent_l
    )

    hits: list[Hit] = []
    for token in _intent_tokens(intent):
        for rel, line_no, content in _rg(token, root)[:200]:
            hits.append(
                Hit(
                    file=rel,
                    line=line_no,
                    match=content,
                    layer=_classify_layer(rel),
                    protected=_is_protected(rel),
                )
            )

    # Deduplicate by file:line
    uniq: dict[tuple[str, int], Hit] = {}
    for h in hits:
        uniq[(h.file, h.line)] = h
    hits = list(uniq.values())

    protected = sorted({h.file for h in hits if h.protected})
    # Also mark protected if intent targets known protected trees even with few hits
    if "program-execution" in intent_l:
        for p in (
            "environment/program-execution/core/shared/AUTHORIZATION_MODEL.yaml",
            "CANONICAL_LAW.md",
            "AGENTS.md",
        ):
            if (root / p).exists() and p not in protected:
                protected.append(p)
                hits.append(
                    Hit(
                        file=p,
                        line=0,
                        match="(path in scope)",
                        layer=_classify_layer(p),
                        protected=True,
                    )
                )

    if any(h.protected for h in hits) or protected:
        mechanical = False

    layers = sorted({h.layer for h in hits})
    files = sorted({h.file for h in hits})

    if protected or not mechanical or public_contract or import_graph:
        decision = "GMP REQUIRED"
        next_step = "Run /gmp (Phase 0 lock). Do NOT use sed migrate or direct /refactor."
    elif not hits:
        decision = "NO-OP"
        next_step = "STOP — no instances found; refine intent."
    else:
        decision = "Eligible for /harvest-use"
        next_step = "Run /harvest-plan → /harvest-use (mechanical only)."

    notes: list[str] = []
    if autonomy_keep:
        notes.append("Root autonomy/ classified do-not-move; campaign-scoped bridge may call it.")
    if "execution-governance" in intent_l:
        notes.append("execution-governance is archived; fold only, do not revive as live SSOT.")
    if not mechanical:
        notes.append("Intent marked NON-MECHANICAL (path move, rename, or contract change).")

    return SweepResult(
        intent=intent,
        files_affected=len(files),
        instances_found=len(hits),
        layers_touched=layers,
        protected_files=sorted(protected),
        mechanical_only=mechanical and not protected and not public_contract,
        async_boundary_affected=False,
        import_graph_change=import_graph,
        public_contract_change=public_contract,
        autonomy_do_not_move=autonomy_keep,
        governance_decision=decision,
        next_step=next_step,
        hits=hits[:100],
        notes=notes,
    )


def render_markdown(result: SweepResult) -> str:
    mech = "✅" if result.mechanical_only else "❌"
    async_b = "✅" if result.async_boundary_affected else "❌"
    imports = "✅" if result.import_graph_change else "❌"
    prot = ", ".join(result.protected_files[:12]) if result.protected_files else "none"
    if len(result.protected_files) > 12:
        prot += f", … (+{len(result.protected_files) - 12})"
    layers = ", ".join(result.layers_touched) if result.layers_touched else "none"
    lines = [
        "## REFACTOR SWEEP REPORT",
        "",
        f"**Intent:** {result.intent}",
        "",
        "### Summary",
        "| Metric | Value |",
        "|------|------|",
        f"| Files affected | {result.files_affected} |",
        f"| Instances found | {result.instances_found} |",
        f"| Layers touched | {layers} |",
        f"| Protected files | {prot} |",
        "",
        "### Impact Classification",
        f"- Mechanical only: {mech}",
        f"- Async boundary affected: {async_b}",
        f"- Import graph change: {imports}",
        f"- Public contract change: {'✅' if result.public_contract_change else '❌'}",
        f"- Autonomy do-not-move: {'✅' if result.autonomy_do_not_move else '❌'}",
        "",
        "### Governance Decision",
        f"**{result.governance_decision}**",
        "",
        "### Next Step",
        result.next_step,
    ]
    if result.notes:
        lines.extend(["", "### Notes", *[f"- {n}" for n in result.notes]])
    lines.extend(["", "### STOP", "Analysis only. No code changes applied."])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only refactor-sweep analyzer")
    parser.add_argument("intent", help="Refactor intent description")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root")
    args = parser.parse_args(argv)
    result = analyze(args.intent, root=args.root.resolve())
    if args.json:
        payload = asdict(result)
        print(json.dumps(payload, indent=2))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
