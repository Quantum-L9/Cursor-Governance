#!/usr/bin/env python3
"""Scan a repository for CANDIDATE underutilization gaps and entrypoints.

Advisory only. Output is a starting point for the human/agent to VERIFY with the
latent-capability reachability law (bidirectional evidence, dynamic dispatch and
registries, dormant_by_design). It deliberately errs toward FEWER candidates.

Method:
- Python: real AST reference index. A top-level def/class/async-def is a
  candidate only if its name is referenced NOWHERE in the repo (any file,
  including its own — same-file dispatch counts), it is not decorated (a
  decorator implies a framework/registry consumer), not dunder/underscore, and
  not defined in a test file. References include Name/Attribute nodes, imports,
  and identifier-valued string constants (so `__all__` and registry-by-string
  count).
- JS/TS: `\b`-anchored token references across other files (no stdlib parser).
- Feature flags: only NAMED off-by-default flags (enable/feature/flag = false).

Entrypoints power the router's `target_reachable` signal. Stdlib only.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
import sys

PY_EXT = {".py"}
JS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv", "coverage", ".mypy_cache", ".pytest_cache"}

JS_EXPORT = re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)")
JS_EXPORT_LIST = re.compile(r"\bexport\s*\{([^}]*)\}")
NAMED_FLAG_OFF = re.compile(r"""([A-Za-z_][\w]*(?:enable[d]?|feature|flag)[\w]*)\s*[:=]\s*(?:[Ff]alse|0)\b""")
IDENT = re.compile(r"^[A-Za-z_]\w*$")


def is_test_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (
        rel.startswith("test/") or rel.startswith("tests/") or "/tests/" in rel or "/test/" in rel
        or name.startswith("test_") or name.endswith("_test.py")
        or ".test." in name or ".spec." in name
    )


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in (PY_EXT | JS_EXT):
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        yield path, rel


def python_defs_and_refs(text: str):
    """Return (top_level_defs_without_decorators, referenced_names) for a module."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set(), set()
    defs = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.decorator_list:
                continue  # decorated → assume framework/registry consumer
            name = node.name
            if name.startswith("_") or len(name) < 3:
                continue
            defs.add(name)
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and IDENT.match(node.value):
            refs.add(node.value)  # __all__ / registry-by-string
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                refs.add((alias.asname or alias.name).split(".")[0])
    return defs, refs


def scan(root: Path) -> dict:
    files = list(iter_files(root))
    texts = {rel: path.read_text(encoding="utf-8", errors="ignore") for path, rel in files}

    # ---- Python: global reference index (all files, tests included as refs) ----
    py_defs = {}            # rel -> set of candidate-eligible defs
    py_refs_global = set()  # every referenced name anywhere
    for rel, text in texts.items():
        if not rel.endswith(".py"):
            continue
        defs, refs = python_defs_and_refs(text)
        py_refs_global |= refs
        if not is_test_file(rel):
            py_defs[rel] = defs

    candidates = []
    seen = set()

    def add(cls, path, symbol, evidence, verify):
        key = (cls, path, symbol)
        if key in seen:
            return
        seen.add(key)
        candidates.append({
            "utilization_gap_class": cls, "path": path, "symbol": symbol,
            "evidence": evidence, "confidence": "low", "verify": verify,
        })

    for rel, defs in py_defs.items():
        for symbol in sorted(defs - py_refs_global):
            add("inactive_component", rel, symbol,
                f"top-level '{symbol}' in {rel} is referenced nowhere in the repo (imports, calls, __all__, or registry strings)",
                "Confirm no reflection/getattr or external-package consumer before treating as inactive.")

    # ---- JS/TS: token-reference heuristic across other files ----
    for rel, text in texts.items():
        if not rel.endswith(tuple(JS_EXT)) or is_test_file(rel):
            continue
        exports = set(JS_EXPORT.findall(text))
        for group in JS_EXPORT_LIST.findall(text):
            exports |= {s.strip().split(" as ")[0].strip() for s in group.split(",") if s.strip()}
        for symbol in sorted(exports):
            if symbol.startswith("_") or len(symbol) < 3:
                continue
            pattern = re.compile(rf"\b{re.escape(symbol)}\b")
            referenced_elsewhere = any(
                other != rel and pattern.search(otext) for other, otext in texts.items()
            )
            if not referenced_elsewhere:
                add("inactive_component", rel, symbol,
                    f"exported '{symbol}' in {rel} has no \\b-matched reference in any other file",
                    "Confirm no dynamic import, registry, or config-driven consumer before treating as inactive.")

    # ---- Named off-by-default feature flags ----
    for rel, text in texts.items():
        if is_test_file(rel):
            continue
        for m in NAMED_FLAG_OFF.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            add("dormant_capability", rel, m.group(1),
                f"{rel}:{line_no}: named feature flag '{m.group(0).strip()}' defaults off",
                "Confirm the feature is complete and NOT dormant_by_design (an intentional staged-rollout flag is not underutilization).")

    return {
        "repo": str(root),
        "scanned_files": len(files),
        "entrypoints": find_entrypoints(root, texts),
        "candidates": candidates,
        "note": "CANDIDATE utilization gaps — advisory only. Verify each with the "
                "latent-capability reachability law before authoring a finding.",
    }


def find_entrypoints(root: Path, texts: dict) -> list:
    entrypoints = []
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            bin_field = data.get("bin")
            names = bin_field.keys() if isinstance(bin_field, dict) else ([bin_field] if bin_field else [])
            for name in names:
                entrypoints.append({"kind": "npm_bin", "name": str(name)})
            for name in (data.get("scripts") or {}):
                entrypoints.append({"kind": "npm_script", "name": name})
        except (ValueError, OSError):
            pass
    for rel, text in texts.items():  # reuse already-read text (no re-read from disk)
        if rel.endswith(".py") and "__main__" in text:
            entrypoints.append({"kind": "python_main", "name": rel})
        elif rel.startswith(("bin/", "scripts/")):
            entrypoints.append({"kind": "script_file", "name": rel})
    return entrypoints


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.repo.is_dir():
        print(f"FAIL: not a directory: {args.repo}", file=sys.stderr)
        return 2
    result = scan(args.repo)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
