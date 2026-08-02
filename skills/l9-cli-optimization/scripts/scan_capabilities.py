#!/usr/bin/env python3
"""Scan a repository for CANDIDATE underutilization, dead-wiring, and breakage.

Advisory only. Output is a starting point for the human/agent to VERIFY with the
latent-capability reachability law (bidirectional evidence, dynamic dispatch and
registries, dormant_by_design). Detectors err toward MORE candidates than the
prior symbol-only scan, but each carries a `verify` note and a `confidence` tier
and every candidate is ranked; nothing here is a finding until verified.

Detectors (comprehensive sweep):
- inactive_component: a top-level Python def/class (AST) or JS/TS export whose
  name is referenced NOWHERE else in the repo. Undecorated, non-dunder, not in a
  test/migration file, not a setuptools entry-point target.
- broken_partial_wiring (unwired executable): a runnable tool — a Python module
  with `__main__`, or a shell script — that NO wiring surface invokes (Makefile,
  CI YAML, pre-commit, hooks, package.json scripts, or any non-doc file). This is
  the dead-end-wiring case: the capability exists but nothing reaches it. When the
  only references are in docs, `doc_only` is set (declared-active-but-unwired).
  Each carries `suggested_wiring` — a ready-to-paste Makefile target.
- dangling_reference (broken/phantom import): an `import X`/`from X import ...`
  or `python -m X` whose root module is neither stdlib, nor a declared dependency
  (pyproject/requirements), nor resolvable in-repo — OR resolves ONLY under an
  `_archived/` path. Catches phantom modules and imports of archived code.
- syntax_error (cracked): a `.py` file that fails to parse — it cannot import or
  run at all.

Framework awareness (suppresses false positives):
- Click/decorated commands (decorator skip); setuptools/PEP 621 entry_points
  (module:symbol targets count as referenced); Alembic upgrade/downgrade in
  migration dirs; pytest_* plugin hooks.

dormant_by_design filtering (Identity-Lock #1 — do NOT activate intentional
retirement): anything under `_archived/_archive/archive/archived/` is excluded
from reactivation candidates (still visible via twins). A flag or script named
beside a staged-rollout / "wave N" / "leave broken" / "do not restore" marker in
docs/config gets intent=staged_rollout, recommended_verdict=do_not_activate.

Feature flags: only NAMED off-by-default flags (enable/feature/flag = false).

Twin visibility (partial): a candidate whose name is ALSO defined in another file
gets `twin_definitions`; same-name twins are listed in `duplicate_twins`.
LIMITATION: same-name only.

Ranking: each candidate carries a numeric `score` and a `confidence` tier;
candidates are sorted highest-first. Entrypoints power the router's
`target_reachable` signal. Stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

PY_EXT = {".py"}
JS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SH_EXT = {".sh", ".bash", ".zsh"}
DOC_EXT = {".md", ".rst", ".txt", ".mdc"}
# Files that can INVOKE a script (the "wiring surface"), plus code/config that
# would reference one. Read broadly so unwired-executable detection is real.
WIRE_EXT = (
    PY_EXT
    | JS_EXT
    | SH_EXT
    | DOC_EXT
    | {
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".mk",
        ".env",
    }
)
WIRE_NAMES = {
    "Makefile",
    "makefile",
    "GNUmakefile",
    "Justfile",
    "justfile",
    "Taskfile.yml",
    "Dockerfile",
    ".pre-commit-config.yaml",
    "tox.ini",
    "noxfile.py",
}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    "coverage",
    ".mypy_cache",
    ".pytest_cache",
}
# Well-known scratch/work-in-progress dir names. Still read for references, but
# their own contents are not flagged as reactivation candidates (not production).
SCRATCH_DIRS = {"wip", "scratch", "sandbox", "playground", "examples", "fixtures"}
# Modules that are effectively always importable / runnable even when undeclared.
ALWAYS_AVAILABLE = {"pip", "setuptools", "wheel", "ensurepip", "venv", "pipx", "pkg_resources"}
ARCHIVE_SEG = re.compile(r"(^|/)_?archi(?:ve|ved)(/|$)", re.IGNORECASE)
# Intent signals that mark an off-by-default flag / dormant file as intentional
# staged rollout or deliberate retirement (dormant_by_design) — Identity-Lock #1.
STAGED_MARKER = re.compile(
    r"dormant_by_design|staged[\s_-]?rollout|\bwave\s*\d+|"
    r"do[\s_-]?not[\s_-]?(?:restore|reactivate|activate|wire)|leave[\s_-]?broken|"
    r"not[\s_-]?yet[\s_-]?(?:wired|enabled|active|implemented|shipped)|"
    r"\bplanned\b|\broadmap\b|\bdeferred\b|\bdormant\b|\bsuperseded\b|\bretired\b",
    re.IGNORECASE,
)
INTENT_EXT = {".md", ".rst", ".txt", ".yaml", ".yml", ".py", ".cfg", ".toml", ".mdc"}
FLAGISH = re.compile(r"[A-Za-z_][\w]*(?:enable[d]?|feature|flag)[\w]*")

JS_EXPORT = re.compile(
    r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)"
)
JS_EXPORT_LIST = re.compile(r"\bexport\s*\{([^}]*)\}")
NAMED_FLAG_OFF = re.compile(
    r"""([A-Za-z_][\w]*(?:enable[d]?|feature|flag)[\w]*)\s*[:=]\s*(?:[Ff]alse|0)\b"""
)
IDENT = re.compile(r"^[A-Za-z_]\w*$")
PYTHON_M = re.compile(r"\bpython[0-9.]*\s+-m\s+([A-Za-z_][\w.]*)")
# Common import-name -> distribution-name aliases (import root differs from the
# name declared in pyproject/requirements). Keeps dep-backed imports from being
# mis-flagged as phantom.
IMPORT_ALIAS = {
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "PIL": "pillow",
    "cv2": "opencv_python",
    "dotenv": "python_dotenv",
    "sklearn": "scikit_learn",
    "dateutil": "python_dateutil",
    "jose": "python_jose",
    "attr": "attrs",
    "OpenSSL": "pyopenssl",
    "git": "gitpython",
}


def is_test_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (
        rel.startswith("test/")
        or rel.startswith("tests/")
        or "/tests/" in rel
        or "/test/" in rel
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
    )


def is_archived(rel: str) -> bool:
    return bool(ARCHIVE_SEG.search("/" + rel))


def is_scratch(rel: str) -> bool:
    return any(p.lower() in SCRATCH_DIRS for p in rel.split("/"))


def is_excluded(rel: str) -> bool:
    """A path whose OWN contents should not be flagged as candidates (archived or
    scratch). Such files are still read for reference/wiring analysis."""
    return is_archived(rel) or is_scratch(rel)


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
            if name.startswith("pytest_"):
                continue  # pytest plugin hook — framework-invoked, not dead
            defs.add(name)
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and IDENT.match(node.value)
        ):
            refs.add(node.value)  # __all__ / registry-by-string
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                refs.add((alias.asname or alias.name).split(".")[0])
    return defs, refs


def python_import_modules(text: str) -> list[str]:
    """Full dotted module names imported by a module (best-effort; AST)."""
    mods: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import — resolves within the package
            if node.module:
                mods.append(node.module)
    return mods


ENTRYPOINT_TARGET = re.compile(r":([A-Za-z_]\w*)")
MIGRATION_DIR = re.compile(r"(^|/)(versions|alembic|migrations)/")


def is_migration_file(rel: str) -> bool:
    """Alembic/migration modules are invoked by the framework via file path;
    their top-level upgrade/downgrade defs are never referenced by name."""
    return bool(MIGRATION_DIR.search("/" + rel))


INTENT_TOKEN = re.compile(r"[A-Za-z_][\w.\-]{2,}")


def intent_scan(root: Path) -> tuple[set[str], set[str]]:
    """Single pass over docs/config/code for lines carrying a staged-rollout /
    do-not-restore / leave-broken / retired marker (dormant_by_design intent).
    Returns (flag_tokens, marked_names):
    - flag_tokens: flag-like names on a marked line (for off-by-default flags).
    - marked_names: all identifiers and their basenames on a marked line (to mark
      unwired scripts and flags the maintainers deliberately retired), so the
      skill does not propose reactivating dormant_by_design capability."""
    flag_tokens: set[str] = set()
    marked_names: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in INTENT_EXT:
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            if STAGED_MARKER.search(line):
                flag_tokens.update(FLAGISH.findall(line))
                for m in INTENT_TOKEN.findall(line):
                    marked_names.add(m)
                    marked_names.add(m.rsplit("/", 1)[-1])  # basename form
    return flag_tokens, marked_names


def entrypoint_symbols(root: Path) -> set[str]:
    """Terminal symbols of setuptools/PEP 621 console-script and entry-point
    targets (module:symbol) — framework consumers. Text parse (stdlib-only)."""
    symbols: set[str] = set()
    for name in ("pyproject.toml", "setup.cfg", "setup.py"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if ":" not in line or "=" not in line and "'" not in line and '"' not in line:
                continue
            for match in ENTRYPOINT_TARGET.findall(line):
                if IDENT.match(match):
                    symbols.add(match)
    return symbols


def _norm(name: str) -> str:
    return re.sub(r"[-.]", "_", name.strip().lower())


def declared_dependencies(root: Path) -> set[str]:
    """Normalized distribution names from pyproject/setup/requirements. Import
    roots are compared against these (via IMPORT_ALIAS) to avoid flagging a
    dep-backed import as a phantom module."""
    names: set[str] = set()
    for fn in ("pyproject.toml", "setup.cfg", "setup.py"):
        p = root / fn
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.findall(r'["\']([A-Za-z0-9][A-Za-z0-9_.\-]+)\s*(?:[<>=!~;\[].*?)?["\']', text):
            names.add(_norm(m))
    for req in list(root.glob("requirements*.txt")) + list(root.glob("requirements/*.txt")):
        try:
            for line in req.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-")):
                    names.add(_norm(re.split(r"[<>=!~;\[ ]", line)[0]))
        except OSError:
            continue
    return names


def local_module_roots(root: Path) -> set[str]:
    """Top-level importable roots in the repo (a dir with a .py or __init__.py, or
    a top-level .py file). Used to tell a local import from a third-party one."""
    tops: set[str] = set()
    try:
        for child in root.iterdir():
            if child.name in SKIP_DIRS:
                continue
            if child.is_dir():
                if (child / "__init__.py").exists() or any(child.glob("*.py")):
                    tops.add(child.name)
            elif child.suffix == ".py":
                tops.add(child.stem)
    except OSError:
        # Directory listing failed (permissions/race) — return whatever we collected.
        pass
    return tops


def module_resolution(root: Path, module: str) -> str:
    """Resolve a dotted module against the repo tree.
    Returns one of: 'local' (a real file under root), 'archived_only' (resolves
    only under an _archived path), or 'absent'."""
    parts = module.split(".")
    base = root.joinpath(*parts)
    if base.with_suffix(".py").exists() or (base / "__init__.py").exists():
        return "local"
    # Does the ROOT package/module exist anywhere, and only under _archived?
    root_name = parts[0]
    hits = []
    for cand in root.rglob(root_name + ".py"):
        hits.append(cand.relative_to(root).as_posix())
    for cand in root.rglob(root_name + "/__init__.py"):
        hits.append(cand.parent.relative_to(root).as_posix())
    hits = [h for h in hits if not any(p in SKIP_DIRS for p in h.split("/"))]
    if hits:
        # A module that exists anywhere non-archived in the repo is reachable
        # (commonly via a runtime sys.path.insert), so it is NOT a phantom.
        if any(not is_archived(h) for h in hits):
            return "local"
        return "archived_only"
    return "absent"


def find_entrypoints(root: Path, texts: dict) -> list:
    entrypoints = []
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            bin_field = data.get("bin")
            names = (
                bin_field.keys()
                if isinstance(bin_field, dict)
                else ([bin_field] if bin_field else [])
            )
            for name in names:
                entrypoints.append({"kind": "npm_bin", "name": str(name)})
            for name in data.get("scripts") or {}:
                entrypoints.append({"kind": "npm_script", "name": name})
        except (ValueError, OSError):
            # Unreadable or invalid package.json — continue with other entrypoint sources.
            pass
    for rel, text in texts.items():
        if rel.endswith(".py") and "__main__" in text:
            entrypoints.append({"kind": "python_main", "name": rel})
        elif rel.startswith(("bin/", "scripts/")):
            entrypoints.append({"kind": "script_file", "name": rel})
    return entrypoints


def read_wire_corpus(root: Path) -> dict:
    """All non-huge files that could reference/invoke a script (code, config,
    CI, hooks, docs). Keyed by rel path. Used for unwired-executable detection."""
    texts: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        if path.suffix.lower() in WIRE_EXT or path.name in WIRE_NAMES:
            try:
                if path.stat().st_size > 512 * 1024:
                    continue
                texts[rel] = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
    return texts


def scan(root: Path) -> dict:
    files = list(iter_files(root))
    texts = {rel: path.read_text(encoding="utf-8", errors="ignore") for path, rel in files}
    wire = read_wire_corpus(root)

    # ---- Python: global reference index (all files, tests included as refs) ----
    py_defs = {}  # rel -> set of candidate-eligible defs
    py_refs_global = set()  # every referenced name anywhere
    syntax_errors = []
    for rel, text in texts.items():
        if not rel.endswith(".py"):
            continue
        try:
            ast.parse(text)
        except SyntaxError as exc:
            if not is_excluded(rel):
                syntax_errors.append({"path": rel, "line": exc.lineno, "error": str(exc.msg)})
        defs, refs = python_defs_and_refs(text)
        py_refs_global |= refs
        if not is_test_file(rel):
            py_defs[rel] = defs

    py_refs_global |= entrypoint_symbols(root)

    name_to_files: dict[str, list[str]] = {}
    for rel, defs in py_defs.items():
        for symbol in defs:
            name_to_files.setdefault(symbol, []).append(rel)
    duplicate_twins = [
        {"symbol": name, "files": sorted(fs)}
        for name, fs in sorted(name_to_files.items())
        if len(fs) > 1
    ]

    staged_flags, retired_names = intent_scan(root)
    deps = declared_dependencies(root)
    local_roots = local_module_roots(root)
    stdlib = set(getattr(sys, "stdlib_module_names", set())) | {"__future__"}
    entrypoints = find_entrypoints(root, texts)
    entrypoint_pkgs = {
        str(e.get("name", "")).split("/")[0]
        for e in entrypoints
        if e.get("kind") in {"python_main", "script_file"}
    }

    candidates = []
    seen = set()

    def add(
        cls,
        path,
        symbol,
        evidence,
        verify,
        flag_bonus=0,
        intent=None,
        recommended_verdict=None,
        extra=None,
    ):
        key = (cls, path, symbol)
        if key in seen:
            return
        seen.add(key)
        score = 1 + flag_bonus
        if path.split("/")[0] in entrypoint_pkgs:
            score += 1
        twins = sorted(f for f in name_to_files.get(symbol, []) if f != path)
        if twins:
            score += 1
        confidence = "high" if score >= 3 else "medium" if score == 2 else "low"
        entry = {
            "utilization_gap_class": cls,
            "path": path,
            "symbol": symbol,
            "evidence": evidence,
            "score": score,
            "confidence": confidence,
            "verify": verify,
        }
        if twins:
            entry["twin_definitions"] = twins
        if intent:
            entry["intent"] = intent
        if recommended_verdict:
            entry["recommended_verdict"] = recommended_verdict
        if extra:
            entry.update(extra)
        candidates.append(entry)

    # ---- inactive_component: Python top-level defs referenced nowhere ----
    for rel, defs in py_defs.items():
        if is_excluded(rel):
            continue
        for symbol in sorted(defs - py_refs_global):
            if symbol in ("upgrade", "downgrade") and is_migration_file(rel):
                continue
            add(
                "inactive_component",
                rel,
                symbol,
                f"top-level '{symbol}' in {rel} is referenced nowhere in the repo (imports, calls, __all__, or registry strings)",
                "Confirm no reflection/getattr or external-package consumer before treating as inactive.",
            )

    # ---- inactive_component: JS/TS exports referenced nowhere ----
    for rel, text in texts.items():
        if not rel.endswith(tuple(JS_EXT)) or is_test_file(rel) or is_excluded(rel):
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
                add(
                    "inactive_component",
                    rel,
                    symbol,
                    f"exported '{symbol}' in {rel} has no \\b-matched reference in any other file",
                    "Confirm no dynamic import, registry, or config-driven consumer before treating as inactive.",
                )

    # ---- broken_partial_wiring: unwired executables (dead-end wiring) ----
    unwired_executables = []
    executables: list[str] = []
    for rel, text in texts.items():
        if rel.endswith(".py") and "__main__" in text and not is_test_file(rel):
            executables.append(rel)
    for rel in wire:
        if Path(rel).suffix.lower() in SH_EXT:
            executables.append(rel)
    for rel in sorted(set(executables)):
        if is_excluded(rel):
            continue
        base = rel.rsplit("/", 1)[-1]
        # Reference forms an invoker might use: the filename, the repo-relative
        # path, and (for Python) the dotted module path — `python -m pkg.mod`
        # names neither the basename nor the path.
        ref_tokens = [base, rel]
        if rel.endswith(".py"):
            dotted = rel[:-3].replace("/", ".")
            ref_tokens.append(dotted)
            if dotted.endswith(".__main__"):
                ref_tokens.append(dotted[: -len(".__main__")])  # `python -m pkg`
        code_refs, doc_refs = [], []
        for other, otext in wire.items():
            if other == rel:
                continue
            if any(tok in otext for tok in ref_tokens):
                (doc_refs if Path(other).suffix.lower() in DOC_EXT else code_refs).append(other)
        if code_refs:
            continue  # something in code/config/CI references it — treat as wired
        intent = "staged_rollout" if (base in retired_names or rel in retired_names) else None
        verdict = "do_not_activate" if intent else None
        evidence = (
            f"executable '{rel}' is invoked by no wiring surface "
            f"(Makefile, CI, pre-commit, hook, package.json, or any non-doc file)"
        )
        if doc_refs:
            evidence += f"; referenced only in docs: {', '.join(sorted(doc_refs)[:3])} (declared-active but unwired)"
        if rel.endswith(".py"):
            target = base[:-3].replace("_", "-")
            wiring = f"{target}:\n\tpython3 {rel} $(ARGS)"
        else:
            target = base.rsplit(".", 1)[0].replace("_", "-")
            wiring = f"{target}:\n\tbash {rel}"
        extra = {"suggested_wiring": wiring}
        if doc_refs:
            extra["doc_only_refs"] = sorted(doc_refs)[:8]
        add(
            "broken_partial_wiring",
            rel,
            base,
            evidence,
            "Confirm the executable is repository-owned, runnable, and NOT dormant_by_design; "
            "if it should run automatically, add the suggested Makefile/CI/hook target. If it "
            "mutates files, wire it read-only or opt-in, never as an unattended auto-fix.",
            flag_bonus=1,
            intent=intent,
            recommended_verdict=verdict,
            extra=extra,
        )
        unwired_executables.append(
            {
                "path": rel,
                "doc_only": bool(doc_refs) and not code_refs,
                "suggested_wiring": wiring,
                "recommended_verdict": verdict,
            }
        )

    # ---- dangling_reference: broken / phantom / archived-only imports ----
    dangling_references = []

    def _phantom_check(mod_root: str, mod_full: str, rel: str, kind: str):
        if mod_root in stdlib or mod_root in ALWAYS_AVAILABLE:
            return
        norm = _norm(mod_root)
        if norm in deps or IMPORT_ALIAS.get(mod_root, norm) in deps:
            return
        if mod_root in local_roots:
            res = module_resolution(root, mod_full)
            if res == "local":
                return
            if res == "archived_only":
                add(
                    "dangling_reference",
                    rel,
                    mod_full,
                    f"{rel} {kind} '{mod_full}', which resolves only under an _archived/ path",
                    "The referenced module was archived. Repoint to the live replacement or remove the reference; "
                    "do not un-archive dormant_by_design code.",
                    flag_bonus=2,
                )
                dangling_references.append(
                    {"path": rel, "module": mod_full, "reason": "archived_only", "via": kind}
                )
                return
            # local root exists but the dotted submodule file does not
            add(
                "dangling_reference",
                rel,
                mod_full,
                f"{rel} {kind} '{mod_full}', but that submodule does not exist under the local '{mod_root}' package",
                "Broken intra-repo import. Fix the path or implement the missing module; verify it is not a "
                "deliberately-deferred gap (leave-broken) before acting.",
                flag_bonus=2,
            )
            dangling_references.append(
                {"path": rel, "module": mod_full, "reason": "missing_local_submodule", "via": kind}
            )
            return
        res = module_resolution(root, mod_full)
        if res == "local":
            return
        if res == "archived_only":
            add(
                "dangling_reference",
                rel,
                mod_full,
                f"{rel} {kind} '{mod_full}', which resolves only under an _archived/ path",
                "Archived-module reference. Repoint to the live replacement or remove it.",
                flag_bonus=2,
            )
            dangling_references.append(
                {"path": rel, "module": mod_full, "reason": "archived_only", "via": kind}
            )
            return
        # not stdlib, not a declared dep, not local, not archived → phantom/undeclared
        add(
            "dangling_reference",
            rel,
            mod_full,
            f"{rel} {kind} '{mod_full}': root '{mod_root}' is not stdlib, not a declared dependency "
            "(pyproject/requirements), and does not resolve in-repo",
            "Verify the module is actually installed (an undeclared 3rd-party dep with a different import name) "
            "OR is a phantom/never-created module. If phantom, remove or implement it; do not treat as latent capability.",
            flag_bonus=1,
        )
        dangling_references.append(
            {"path": rel, "module": mod_full, "reason": "unresolved_phantom", "via": kind}
        )

    for rel, text in texts.items():
        if not rel.endswith(".py") or is_excluded(rel):
            continue
        for mod in python_import_modules(text):
            _phantom_check(mod.split(".")[0], mod, rel, "imports")
    # `python -m MODULE` invocations hidden in strings / shell (e.g. subprocess).
    for rel, text in wire.items():
        if is_excluded(rel):
            continue
        for mod in PYTHON_M.findall(text):
            _phantom_check(mod.split(".")[0], mod, rel, "invokes `python -m`")

    # ---- syntax_error candidates (cracked; cannot import/run) ----
    for se in syntax_errors:
        add(
            "miswired_file",
            se["path"],
            se["path"].rsplit("/", 1)[-1],
            f"{se['path']} fails to parse (SyntaxError at line {se.get('line')}: {se.get('error')})",
            "The file cannot be imported or executed as-is. Fix the syntax before any wiring or activation.",
            flag_bonus=2,
        )

    # ---- Named off-by-default feature flags ----
    for rel, text in texts.items():
        if is_test_file(rel) or is_excluded(rel):
            continue
        lines = text.splitlines()
        for m in NAMED_FLAG_OFF.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            flag_name = m.group(1)
            context = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else ""
            staged = flag_name in staged_flags or bool(STAGED_MARKER.search(context))
            if staged:
                add(
                    "dormant_capability",
                    rel,
                    flag_name,
                    f"{rel}:{line_no}: named feature flag '{m.group(0).strip()}' defaults off, "
                    "but repo intent signals mark it as staged rollout / dormant_by_design",
                    "Identity-Lock #1 forbids activating dormant_by_design capability — treat as do_not_activate unless the rollout intent is proven complete and retired.",
                    flag_bonus=0,
                    intent="staged_rollout",
                    recommended_verdict="do_not_activate",
                )
            else:
                add(
                    "dormant_capability",
                    rel,
                    flag_name,
                    f"{rel}:{line_no}: named feature flag '{m.group(0).strip()}' defaults off",
                    "Confirm the feature is complete and NOT dormant_by_design (an intentional staged-rollout flag is not underutilization).",
                    flag_bonus=1,
                )

    def _dedupe(rows, keys):
        out, seen_rows = [], set()
        for r in rows:
            k = tuple(r.get(x) for x in keys)
            if k in seen_rows:
                continue
            seen_rows.add(k)
            out.append(r)
        return out

    dangling_references = _dedupe(dangling_references, ("path", "module", "reason"))
    unwired_executables = _dedupe(unwired_executables, ("path",))

    candidates.sort(key=lambda c: (-c["score"], c["utilization_gap_class"], c["path"], c["symbol"]))

    class_counts: dict[str, int] = {}
    for c in candidates:
        class_counts[c["utilization_gap_class"]] = (
            class_counts.get(c["utilization_gap_class"], 0) + 1
        )

    return {
        "repo": str(root),
        "scanned_files": len(files),
        "wire_corpus_files": len(wire),
        "entrypoints": entrypoints,
        "candidates": candidates,
        "candidate_counts_by_class": class_counts,
        "unwired_executables": unwired_executables,
        "dangling_references": dangling_references,
        "syntax_errors": syntax_errors,
        "duplicate_twins": duplicate_twins,
        "note": "CANDIDATE gaps — advisory only, ranked by suspicion (score). Verify each with "
        "the latent-capability reachability law before authoring a finding. Classes: "
        "inactive_component (dead symbol), broken_partial_wiring (unwired executable — see "
        "suggested_wiring to add a Makefile/CI/hook target), dangling_reference (broken/phantom/"
        "archived import), miswired_file (syntax-broken), dormant_capability (off-by-default flag). "
        "A same-name twin usually means one copy is live — activating the orphan reintroduces "
        "duplication. intent=staged_rollout / recommended_verdict=do_not_activate is "
        "dormant_by_design (Identity-Lock #1) — do NOT activate. Anything under _archived/ is "
        "excluded from reactivation candidates by design. This scan does NOT cover registry/manifest "
        "inventory drift (e.g. a skill/plugin folder on disk missing from its manifest) or "
        "config/doc path references to deleted files — run those diffs manually per SKILL.md Diagnosis.",
    }


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
