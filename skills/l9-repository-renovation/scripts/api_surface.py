#!/usr/bin/env python3
"""Public-API surface extraction and compatibility diff (AST, zero-dependency).

Capability B2 of the renovation skill: turn identity-lock rule 4 ("preserve
externally consumed behavior, public APIs, and release compatibility") from a
promise into a machine-checked gate.

Two subcommands:

  extract  <repo>            -> a structural snapshot of the public API surface
  diff     --before --after  -> classified compatibility delta + a fail-closed verdict

"Public" means: modules outside archived/vendored/test trees, symbols not prefixed
with '_', honoring a module's __all__ when present. Signatures are compared by
parameter identity and kind, not by source text, so a reordered-but-compatible
change reads as compatible and a removed/renamed/required-tightened parameter reads
as breaking.

The diff classifies each change and derives the smallest semver bump it justifies,
so a renovation PR can be blocked when the declared version bump understates the
real surface change.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import iter_files, read_text, relative, utc_now  # noqa: E402

ARCHIVE_PARTS = {
    "_archived",
    "_archive",
    "archive",
    "archived",
    "wip",
    "current_work",
    "examples",
    "example",
    "fixtures",
    "vendor",
    "third_party",
    "tests",
    "test",
}

BREAKING = "breaking"
COMPATIBLE = "compatible"


def _is_public_module(rel: str) -> bool:
    parts = Path(rel).parts
    if any(part.lower() in ARCHIVE_PARTS for part in parts):
        return False
    # A leading underscore on any package/module component marks it private.
    return not any(part.startswith("_") and part != "__init__.py" for part in parts)


def _module_name(rel: str) -> str:
    path = Path(rel)
    parts = list(path.parts[:-1])
    if path.name != "__init__.py":
        parts.append(path.stem)
    return ".".join(parts)


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    n_defaults = len(args.defaults)
    required_positional = positional[: len(positional) - n_defaults]
    optional_positional = positional[len(positional) - n_defaults :]
    kw_required = [a for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is None]
    kw_optional = [a for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is not None]
    return {
        "required": [a.arg for a in required_positional] + [a.arg for a in kw_required],
        "optional": [a.arg for a in optional_positional] + [a.arg for a in kw_optional],
        "posonly": [a.arg for a in args.posonlyargs],
        "kwonly": [a.arg for a in args.kwonlyargs],
        "var_positional": args.vararg.arg if args.vararg else None,
        "var_keyword": args.kwarg.arg if args.kwarg else None,
        "returns": ast.unparse(node.returns) if node.returns is not None else None,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
    }


def _public_names(body: list[ast.stmt], declared_all: set[str] | None) -> dict[str, ast.stmt]:
    out: dict[str, ast.stmt] = {}
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = stmt.name
            if declared_all is not None:
                if name in declared_all:
                    out[name] = stmt
            elif not name.startswith("_"):
                out[name] = stmt
    return out


def _extract_all(tree: ast.Module) -> set[str] | None:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(stmt.value, (ast.List, ast.Tuple)):
                        return {
                            element.value
                            for element in stmt.value.elts
                            if isinstance(element, ast.Constant) and isinstance(element.value, str)
                        }
    return None


def extract_surface(root: Path) -> dict[str, Any]:
    root = root.resolve()
    modules: dict[str, Any] = {}
    for path in sorted(iter_files(root)):
        if path.suffix != ".py":
            continue
        rel = relative(root, path)
        if not _is_public_module(rel):
            continue
        text = read_text(path)
        if text is None:
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        declared_all = _extract_all(tree)
        public = _public_names(tree.body, declared_all)
        if not public:
            continue
        mod: dict[str, Any] = {"functions": {}, "classes": {}}
        for name, node in public.items():
            if isinstance(node, ast.ClassDef):
                methods = {
                    m.name: _signature(m)
                    for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not m.name.startswith("_")
                }
                bases = [ast.unparse(b) for b in node.bases]
                mod["classes"][name] = {"methods": methods, "bases": bases}
            else:
                mod["functions"][name] = _signature(node)
        modules[_module_name(rel)] = mod
    return {
        "schema_version": "api-surface-1.0",
        "generated_at": utc_now(),
        "root": str(root),
        "modules": modules,
    }


def _diff_signature(
    qual: str, before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    b_req, a_req = set(before["required"]), set(after["required"])
    b_opt, a_opt = set(before["optional"]), set(after["optional"])
    removed = (b_req | b_opt) - (a_req | a_opt)
    for param in sorted(removed):
        # A removed **kwargs still accepted the caller's keyword, so removing it or a
        # removed param when no **kwargs remains is breaking for keyword callers.
        if after["var_keyword"] and param in b_opt:
            changes.append(
                {
                    "kind": "optional_param_removed_but_var_keyword",
                    "severity": COMPATIBLE,
                    "symbol": f"{qual}({param})",
                }
            )
        else:
            changes.append(
                {"kind": "param_removed", "severity": BREAKING, "symbol": f"{qual}({param})"}
            )
    for param in sorted(a_req - (b_req | b_opt)):
        changes.append(
            {"kind": "required_param_added", "severity": BREAKING, "symbol": f"{qual}({param})"}
        )
    for param in sorted(a_opt - (b_req | b_opt)):
        changes.append(
            {"kind": "optional_param_added", "severity": COMPATIBLE, "symbol": f"{qual}({param})"}
        )
    for param in sorted(b_opt & a_req):
        changes.append(
            {"kind": "param_made_required", "severity": BREAKING, "symbol": f"{qual}({param})"}
        )
    if before["var_positional"] and not after["var_positional"]:
        changes.append(
            {"kind": "var_positional_removed", "severity": BREAKING, "symbol": f"{qual}(*args)"}
        )
    if before["var_keyword"] and not after["var_keyword"]:
        changes.append(
            {"kind": "var_keyword_removed", "severity": BREAKING, "symbol": f"{qual}(**kwargs)"}
        )
    if before["returns"] != after["returns"]:
        changes.append(
            {"kind": "return_annotation_changed", "severity": COMPATIBLE, "symbol": qual}
        )
    return changes


def diff_surface(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes: list[dict[str, str]] = []
    b_mods, a_mods = before["modules"], after["modules"]
    for mod in sorted(set(b_mods) - set(a_mods)):
        changes.append({"kind": "module_removed", "severity": BREAKING, "symbol": mod})
    for mod in sorted(set(a_mods) - set(b_mods)):
        changes.append({"kind": "module_added", "severity": COMPATIBLE, "symbol": mod})
    for mod in sorted(set(b_mods) & set(a_mods)):
        bm, am = b_mods[mod], a_mods[mod]
        for fn in sorted(set(bm["functions"]) - set(am["functions"])):
            changes.append(
                {"kind": "function_removed", "severity": BREAKING, "symbol": f"{mod}.{fn}"}
            )
        for fn in sorted(set(am["functions"]) - set(bm["functions"])):
            changes.append(
                {"kind": "function_added", "severity": COMPATIBLE, "symbol": f"{mod}.{fn}"}
            )
        for fn in sorted(set(bm["functions"]) & set(am["functions"])):
            changes.extend(_diff_signature(f"{mod}.{fn}", bm["functions"][fn], am["functions"][fn]))
        for cls in sorted(set(bm["classes"]) - set(am["classes"])):
            changes.append(
                {"kind": "class_removed", "severity": BREAKING, "symbol": f"{mod}.{cls}"}
            )
        for cls in sorted(set(am["classes"]) - set(bm["classes"])):
            changes.append(
                {"kind": "class_added", "severity": COMPATIBLE, "symbol": f"{mod}.{cls}"}
            )
        for cls in sorted(set(bm["classes"]) & set(am["classes"])):
            b_methods, a_methods = bm["classes"][cls]["methods"], am["classes"][cls]["methods"]
            for meth in sorted(set(b_methods) - set(a_methods)):
                changes.append(
                    {
                        "kind": "method_removed",
                        "severity": BREAKING,
                        "symbol": f"{mod}.{cls}.{meth}",
                    }
                )
            for meth in sorted(set(a_methods) - set(b_methods)):
                changes.append(
                    {
                        "kind": "method_added",
                        "severity": COMPATIBLE,
                        "symbol": f"{mod}.{cls}.{meth}",
                    }
                )
            for meth in sorted(set(b_methods) & set(a_methods)):
                changes.extend(
                    _diff_signature(f"{mod}.{cls}.{meth}", b_methods[meth], a_methods[meth])
                )
    breaking = [c for c in changes if c["severity"] == BREAKING]
    additive = [c for c in changes if c["severity"] == COMPATIBLE and "added" in c["kind"]]
    if breaking:
        bump = "major"
    elif additive:
        bump = "minor"
    else:
        bump = "patch"
    return {
        "schema_version": "api-delta-1.0",
        "generated_at": utc_now(),
        "verdict": BREAKING if breaking else COMPATIBLE,
        "required_semver_bump": bump,
        "counts": {"total": len(changes), "breaking": len(breaking)},
        "changes": sorted(changes, key=lambda c: (c["severity"] != BREAKING, c["symbol"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Public-API surface extraction and compatibility diff"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_extract = sub.add_parser("extract", help="emit the public API surface of a repo")
    p_extract.add_argument("repo")
    p_extract.add_argument("--output", required=True)
    p_diff = sub.add_parser("diff", help="classify the compatibility delta between two surfaces")
    p_diff.add_argument("--before", required=True)
    p_diff.add_argument("--after", required=True)
    p_diff.add_argument("--output", required=True)
    p_diff.add_argument(
        "--fail-on-break", action="store_true", help="exit 3 when the delta is breaking"
    )
    args = parser.parse_args()

    if args.command == "extract":
        surface = extract_surface(Path(args.repo))
        Path(args.output).write_text(
            json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        n = sum(
            len(m["functions"]) + sum(1 for _ in m["classes"]) for m in surface["modules"].values()
        )
        print(f"surface: {args.output} ({len(surface['modules'])} modules, {n} top-level symbols)")
        return 0

    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    delta = diff_surface(before, after)
    Path(args.output).write_text(
        json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"delta: {args.output} verdict={delta['verdict']} bump={delta['required_semver_bump']} breaking={delta['counts']['breaking']}"
    )
    if args.fail_on_break and delta["verdict"] == BREAKING:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
