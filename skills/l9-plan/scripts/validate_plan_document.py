#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"jsonschema required: {exc}")

PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME|maybe|should)\b", re.I)
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "plan-document.schema.json"


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("plan root must be an object")
    return data


def has_cycle(deps: dict[str, list[str]]) -> bool:
    indeg = {k: 0 for k in deps}
    adj: dict[str, list[str]] = {k: [] for k in deps}
    for node, parents in deps.items():
        for parent in parents:
            if parent not in indeg:
                return True
            indeg[node] += 1
            adj[parent].append(node)
    queue = [k for k, v in indeg.items() if v == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in adj.get(n, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return bool(deps) and seen != len(deps)


def semantic_errors(plan: dict) -> list[str]:
    errors: list[str] = []
    scope = plan.get("scope") or {}
    if not scope.get("out"):
        errors.append("G_SCOPE_OUT: scope.out is empty")

    criteria = [str(c).strip() for c in (plan.get("success_criteria") or [])]
    if not criteria or all(not c for c in criteria):
        errors.append("G_SUCCESS: success_criteria missing or empty")
    weak = {"success", "done", "works", "ok", "fine"}
    if criteria and all(c.lower() in weak for c in criteria):
        errors.append("G_SUCCESS: success_criteria not falsifiable")

    todos = [t for t in (plan.get("todos") or []) if isinstance(t, dict)]
    todo_ids = {t.get("id") for t in todos}
    deps = {t["id"]: list(t.get("dependencies") or []) for t in todos if t.get("id")}
    for todo in todos:
        tid = todo.get("id", "?")
        files = todo.get("files") or []
        blocker = str(todo.get("blocker") or "").strip()
        if not files and not blocker:
            errors.append(f"G_TODO_GROUND: todo {tid} lacks files and blocker")
        blob = " ".join([str(todo.get("task", "")), " ".join(map(str, files)), blocker])
        if PLACEHOLDER_RE.search(blob) and not blocker:
            errors.append(f"G_PLACEHOLDER: todo {tid} has placeholder without blocker")
        for dep in todo.get("dependencies") or []:
            if dep not in todo_ids:
                errors.append(f"G_DEPS_ACYCLIC: unknown dependency {dep} on {tid}")

    if has_cycle(deps):
        errors.append("G_DEPS_ACYCLIC: dependency cycle detected")

    critical = plan.get("critical_path") or []
    if not critical:
        errors.append("G_CRITICAL_PATH: critical_path empty")
    for cid in critical:
        if cid not in todo_ids:
            errors.append(f"G_CRITICAL_PATH: unknown todo id {cid}")

    stress = plan.get("stress_test") or {}
    if not stress.get("disconfirming_questions"):
        errors.append("G_STRESS: disconfirming_questions empty")
    if not str(stress.get("blast_radius") or "").strip():
        errors.append("G_STRESS: blast_radius missing")

    high = any(t.get("risk") in {"high", "irreversible"} for t in todos)
    if high and not str(stress.get("rollback") or "").strip():
        errors.append("G_ROLLBACK: high/irreversible risk without rollback")

    impacts = plan.get("doc_root_surface_impact") or []
    if not impacts:
        errors.append("G_DOC_SURFACE: doc_root_surface_impact missing")
    for row in impacts:
        if not isinstance(row, dict):
            continue
        surface = row.get("surface")
        if row.get("action") == "n_a" and not str(row.get("reason") or "").strip():
            errors.append(f"G_DOC_SURFACE: N/A without reason for {surface}")
        if row.get("action") == "update" and not (row.get("todo_ids") or []):
            errors.append(f"G_DOC_SURFACE: update without todo_ids for {surface}")

    if not plan.get("pre_validation") or not plan.get("final_validation"):
        errors.append("G_PRE_FINAL: pre_validation or final_validation missing")

    if plan.get("code_in_scope"):
        commands = " ".join(str(x.get("command", "")) for x in plan.get("final_validation") or [])
        if "make pr-check" not in commands and re.search(r"\bmake\s+pr\b", commands) is None:
            errors.append("G_PR_CHECK: code_in_scope true but final_validation lacks make pr-check")
        handoff = plan.get("gmp_handoff") or {}
        if not handoff.get("may_modify") or not handoff.get("must_not_modify"):
            errors.append("G_GMP_LOCK: code_in_scope requires may_modify and must_not_modify")

    leverage = plan.get("leverage") or {}
    if not leverage.get("ranked_todo_ids"):
        errors.append("G_LEVERAGE: leverage.ranked_todo_ids empty")

    if any(str(t.get("blocker") or "").strip() for t in todos) and not plan.get("unknowns"):
        if (plan.get("convergence") or {}).get("status") == "converged":
            errors.append("G_UNKNOWN_HONESTY: blockers present but unknowns empty while converged")

    if (plan.get("convergence") or {}).get("status") == "converged":
        for section_name in ("pre_validation", "final_validation"):
            for item in plan.get(section_name) or []:
                if item.get("status") in {"pending", "failed", "unknown"}:
                    item_id = item.get("id")
                    status = item.get("status")
                    errors.append(
                        f"G_CONVERGENCE: converged while {section_name}.{item_id} is {status}"
                    )
    return errors


def validate_path(path: Path) -> list[str]:
    try:
        plan = load_json(path)
    except Exception as exc:
        return [f"G_SCHEMA: cannot load JSON: {exc}"]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [
        f"G_SCHEMA: {'.'.join(str(x) for x in err.path) or '<root>'}: {err.message}"
        for err in sorted(
            jsonschema.Draft202012Validator(schema).iter_errors(plan),
            key=lambda e: list(e.path),
        )
    ]
    errors.extend(semantic_errors(plan))
    out: list[str] = []
    seen: set[str] = set()
    for e in errors:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_plan_document.py <plan.json> [more.json]", file=sys.stderr)
        return 2
    rc = 0
    for arg in argv[1:]:
        path = Path(arg)
        errs = validate_path(path)
        if errs:
            rc = 1
            print(f"FAIL: {path}")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"PASS: {path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
