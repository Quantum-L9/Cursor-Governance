#!/usr/bin/env python3
"""Deterministic closure seed generation for l9-pr-audit v2.0.

This module owns deterministic closure seed generation, including producer/consumer
closure, mutation candidates, review-thread semantic closure, and no-orphan-artifact
reachability. Mutation execution itself occurs only in an isolated temporary copy via
``execute_mutation_probe.py``; the audited repository remains read-only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")
WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FAILURE_PATTERNS = {
    "EXCEPTION_PATH": re.compile(r"\b(?:try|except|raise)\b"),
    "TIMEOUT": re.compile(r"\btimeout\b", re.I),
    "RETRY": re.compile(r"\bretr(?:y|ies|ied|ying)\b|\bbackoff\b", re.I),
    "SUBPROCESS_RETURN": re.compile(r"\bsubprocess\b|\breturncode\b|\bcheck_call\b|\brun\(", re.I),
    "NULLABLE_GUARD": re.compile(
        r"\b(?:is\s+None|is\s+not\s+None|if\s+not\s+\w+|if\s+\w+\s*:)", re.I
    ),
    "CLEANUP_FINALLY": re.compile(r"\bfinally\b|\bcleanup\b|\bclose\(", re.I),
    "AUTH_FAILURE": re.compile(r"\b(?:auth|unauthori[sz]ed|forbidden|permission)\b", re.I),
    "ROLLBACK": re.compile(r"\brollback\b|\btransaction\b", re.I),
    "EXTERNAL_IO": re.compile(
        r"\b(?:requests\.|httpx\.|urllib\.|socket\.|open\(|read\(|write\()", re.I
    ),
}


def stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(p) for p in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:12]}"


def seed_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    return (
        ast.dump(node.args, include_attributes=False)
        + ":"
        + (ast.unparse(node.returns) if node.returns else "")
    )


def _route_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    routes: list[str] = []
    for dec in node.decorator_list:
        call = dec if isinstance(dec, ast.Call) else None
        fn = call.func if call else dec
        name = ""
        if isinstance(fn, ast.Attribute):
            name = fn.attr.lower()
        elif isinstance(fn, ast.Name):
            name = fn.id.lower()
        if name not in {
            "route",
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "options",
            "head",
            "api_route",
        }:
            continue
        route = "<dynamic>"
        if (
            call
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            route = call.args[0].value
        routes.append(f"{name.upper()} {route}")
    return routes


def python_public_surfaces(content: str) -> dict[tuple[str, str], str]:
    tree = ast.parse(content)
    out: dict[tuple[str, str], str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            out[("EXPORTED_FUNCTION", node.name)] = _signature(node)
            for route in _route_decorators(node):
                out[("API_ROUTE", route)] = _signature(node)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods: list[str] = []
            for child in node.body:
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not child.name.startswith("_"):
                    methods.append(child.name + "=" + _signature(child))
            bases = [ast.dump(base, include_attributes=False) for base in node.bases]
            out[("EXPORTED_CLASS", node.name)] = repr((bases, sorted(methods)))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets: list[ast.expr] = (
                list(node.targets) if isinstance(node, ast.Assign) else [node.target]
            )
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id.isupper()
                    and not target.id.startswith("_")
                ):
                    annotation = (
                        ast.dump(node.annotation, include_attributes=False)
                        if isinstance(node, ast.AnnAssign) and node.annotation
                        else ""
                    )
                    value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
                    value_sig = (
                        ast.dump(value, include_attributes=False) if value is not None else ""
                    )
                    out[("PUBLIC_CONSTANT", target.id)] = annotation + ":" + value_sig
    return out


def public_surface_deltas(
    raw: dict[str, Any], pr: int, classification: str
) -> list[dict[str, Any]]:
    path = str(raw.get("path") or "")
    patch = str(raw.get("patch") or "")
    base = raw.get("base_content")
    head = raw.get("head_content")
    out: list[dict[str, Any]] = []
    if path.endswith(".py") and isinstance(base, str) and isinstance(head, str):
        try:
            before = python_public_surfaces(base)
            after = python_public_surfaces(head)
            for key in sorted(set(before) | set(after)):
                if key not in before:
                    change = "ADDED"
                elif key not in after:
                    change = "REMOVED"
                elif before[key] != after[key]:
                    change = "MODIFIED"
                else:
                    continue
                kind, name = key
                payload = {
                    "pr_number": pr,
                    "path": path,
                    "surface_kind": kind,
                    "surface_name": name,
                    "change_type": change,
                }
                payload["surface_id"] = stable_id("PUB", pr, path, kind, name)
                out.append(payload)
        except SyntaxError:
            pass
    if classification in {"CONFIGURATION", "SCHEMA", "WORKFLOW"}:
        added: set[str] = set()
        removed: set[str] = set()
        for line in patch.splitlines():
            if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
                continue
            m = re.search(r'^[+-]\s*["\']?([A-Za-z_][A-Za-z0-9_.-]*)["\']?\s*[:=]', line)
            if m:
                (added if line.startswith("+") else removed).add(m.group(1))
        for key in sorted(added | removed):
            change = (
                "MODIFIED"
                if key in added and key in removed
                else "ADDED"
                if key in added
                else "REMOVED"
            )
            payload = {
                "pr_number": pr,
                "path": path,
                "surface_kind": "CONFIG_OR_SCHEMA_KEY",
                "surface_name": key,
                "change_type": change,
            }
            payload["surface_id"] = stable_id("PUB", pr, path, "CONFIG_OR_SCHEMA_KEY", key)
            out.append(payload)
    return out


def additional_symbol_deltas(
    raw: dict[str, Any], pr: int, classification: str
) -> list[dict[str, Any]]:
    mapping = {
        "EXPORTED_FUNCTION": "FUNCTION",
        "EXPORTED_CLASS": "CLASS",
        "PUBLIC_CONSTANT": "CONSTANT",
        "API_ROUTE": "API_ROUTE",
        "CONFIG_OR_SCHEMA_KEY": "SCHEMA_FIELD" if classification == "SCHEMA" else "CONFIG_KEY",
    }
    return [
        {
            "symbol_id": stable_id(
                "SYM",
                pr,
                d["path"],
                mapping[d["surface_kind"]],
                d["surface_name"],
                d["change_type"],
            ),
            "pr_number": pr,
            "path": d["path"],
            "symbol_name": d["surface_name"],
            "symbol_kind": mapping[d["surface_kind"]],
            "change_type": d["change_type"],
            "detection_method": "PUBLIC_SURFACE_STATIC",
            "detection_confidence": "EXACT_STATIC"
            if d["surface_kind"] != "CONFIG_OR_SCHEMA_KEY"
            else "HEURISTIC",
            "deterministic_state": "REQUIRES_JUDGMENT",
        }
        for d in public_surface_deltas(raw, pr, classification)
    ]


def patch_hunks(path: str, patch: str, pr: int) -> list[dict[str, Any]]:
    hunks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in patch.splitlines():
        m = HUNK_RE.match(line)
        if m:
            if current:
                current["text_hash"] = hashlib.sha256(
                    "\n".join(current.pop("lines")).encode()
                ).hexdigest()
                hunks.append(current)
            current = {
                "hunk_id": stable_id("HUNK", pr, path, m.group(1), m.group(3)),
                "path": path,
                "old_start": int(m.group(1)),
                "new_start": int(m.group(3)),
                "lines": [line],
            }
        elif current is not None:
            current["lines"].append(line)
    if current:
        current["text_hash"] = hashlib.sha256("\n".join(current.pop("lines")).encode()).hexdigest()
        hunks.append(current)
    return hunks


def failure_edges(path: str, patch: str, pr: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    line_no = 0
    in_hunk = False
    for raw in patch.splitlines():
        m = HUNK_RE.match(raw)
        if m:
            line_no = int(m.group(3))
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        prefix = raw[:1]
        text = raw[1:] if prefix in {"+", "-", " "} else raw
        if prefix == "-":
            continue
        if prefix in {"+", " "}:
            if prefix == "+":
                for kind, rx in FAILURE_PATTERNS.items():
                    if rx.search(text):
                        out.append(
                            {
                                "edge_id": stable_id("EDGE", pr, path, line_no, kind, text),
                                "pr_number": pr,
                                "path": path,
                                "line": line_no,
                                "edge_kind": kind,
                                "text_hash": hashlib.sha256(text.encode()).hexdigest(),
                            }
                        )
            line_no += 1
    return list({x["edge_id"]: x for x in out}.values())


def _repository_files(doc: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    complete = doc.get("repository_files_complete") is True
    files: list[dict[str, str]] = []
    for item in doc.get("repository_files") or []:
        if isinstance(item, dict) and item.get("path") and isinstance(item.get("content"), str):
            files.append({"path": str(item["path"]), "content": item["content"]})
    return complete, files


def code_token_present(path: str, content: str, token: str) -> bool:
    if not token:
        return False
    if path.endswith(".py") and WORD_RE.fullmatch(token):
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == token:
                    return True
                if isinstance(node, ast.Attribute) and node.attr == token:
                    return True
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and node.name == token
                ):
                    return True
            return False
        except SyntaxError:
            return False
    return token in content


def reference_candidates(
    name: str, files: Iterable[dict[str, str]], owner_path: str
) -> list[dict[str, Any]]:
    if not name or name == "<dynamic>":
        return []
    token = (
        name.split()[-1]
        if name.startswith(
            ("GET ", "POST ", "PUT ", "PATCH ", "DELETE ", "OPTIONS ", "HEAD ", "API_ROUTE ")
        )
        else name
    )
    pattern = re.escape(token) if not WORD_RE.fullmatch(token) else rf"\b{re.escape(token)}\b"
    rx = re.compile(pattern)
    out: list[dict[str, Any]] = []
    for item in files:
        if rx.search(item["content"]):
            out.append(
                {
                    "path": item["path"],
                    "owner_path": owner_path,
                    "same_file": item["path"] == owner_path,
                }
            )
    return out


def classify_reference_path(path: str) -> str:
    p = path.lower()
    if any(x in p.split("/") for x in ("docs", "doc")) or p.endswith((".md", ".rst", ".txt")):
        return "DOC_ONLY"
    if "test" in p.split("/") or "/tests/" in f"/{p}/" or p.startswith("tests/"):
        return "TEST_ONLY"
    if any(x in p for x in ("generated", "dist/", "build/", ".lock")):
        return "GENERATED"
    return "LIVE"


def dependency_delta_lines(path: str, patch: str, pr: int) -> list[dict[str, Any]]:
    name = Path(path).name.lower()
    if name not in {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pdm.lock",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "go.mod",
        "go.sum",
        "cargo.toml",
        "cargo.lock",
    }:
        return []
    out = []
    for raw in patch.splitlines():
        if not raw.startswith(("+", "-")) or raw.startswith(("+++", "---")):
            continue
        text = raw[1:].strip()
        if not text or text.startswith(("#", "//")):
            continue
        out.append(
            {
                "dependency_delta_id": stable_id("DEP", pr, path, raw[0], text),
                "path": path,
                "direction": "ADDED_OR_CHANGED" if raw[0] == "+" else "REMOVED_OR_CHANGED",
                "text_hash": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    return out


def _changed_added_line_numbers(patch: str) -> set[int]:
    out: set[int] = set()
    line_no = 0
    in_hunk = False
    for raw in patch.splitlines():
        m = HUNK_RE.match(raw)
        if m:
            line_no = int(m.group(3))
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        prefix = raw[:1]
        if prefix == "-":
            continue
        if prefix in {"+", " "}:
            if prefix == "+":
                out.add(line_no)
            line_no += 1
    return out


def _mutated_expr(node: ast.AST) -> tuple[str, str] | None:
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        swaps = {
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Is: ast.IsNot,
            ast.IsNot: ast.Is,
            ast.Lt: ast.GtE,
            ast.LtE: ast.Gt,
            ast.Gt: ast.LtE,
            ast.GtE: ast.Lt,
        }
        op = node.ops[0]
        repl = swaps.get(type(op))
        if repl:
            clone = ast.Compare(left=node.left, ops=[repl()], comparators=node.comparators)
            return "COMPARE_OPERATOR_SWAP", ast.unparse(ast.fix_missing_locations(clone))
    if isinstance(node, ast.BoolOp):
        repl = ast.Or if isinstance(node.op, ast.And) else ast.And
        clone = ast.BoolOp(op=repl(), values=node.values)
        return "BOOLEAN_OPERATOR_SWAP", ast.unparse(ast.fix_missing_locations(clone))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return "NEGATION_REMOVE", ast.unparse(node.operand)
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return "BOOLEAN_LITERAL_FLIP", "False" if node.value else "True"
    return None


def mutation_candidates(raw: dict[str, Any], pr: int) -> list[dict[str, Any]]:
    path = str(raw.get("path") or "")
    head = raw.get("head_content")
    patch = str(raw.get("patch") or "")
    if not path.endswith(".py") or not isinstance(head, str):
        return []
    changed = _changed_added_line_numbers(patch)
    if not changed:
        return []
    try:
        tree = ast.parse(head)
    except SyntaxError:
        return []
    out: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not hasattr(node, "lineno") or int(getattr(node, "lineno")) not in changed:
            continue
        mutated = _mutated_expr(node)
        if not mutated or not hasattr(node, "end_lineno") or not hasattr(node, "end_col_offset"):
            continue
        kind, replacement = mutated
        original = ast.get_source_segment(head, node)
        if not original or replacement == original:
            continue
        payload = {
            "pr_number": pr,
            "path": path,
            "line": int(node.lineno),
            "column": int(node.col_offset),
            "end_line": int(node.end_lineno),
            "end_column": int(node.end_col_offset),
            "mutation_kind": kind,
            "original_source": original,
            "mutant_source": replacement,
            "source_sha256": hashlib.sha256(head.encode()).hexdigest(),
        }
        payload["mutation_id"] = stable_id(
            "MUT", pr, path, node.lineno, node.col_offset, kind, original, replacement
        )
        out.append(payload)
    return list({x["mutation_id"]: x for x in out}.values())


def _artifact_reference_tokens(raw: dict[str, Any]) -> list[str]:
    path = str(raw.get("path") or "")
    stem = Path(path).stem
    tokens = {stem} if stem and stem not in {"__init__", "index", "main"} else set()
    head = raw.get("head_content")
    if path.endswith(".py") and isinstance(head, str):
        try:
            tree = ast.parse(head)
            for node in tree.body:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ) and not node.name.startswith("_"):
                    tokens.add(node.name)
        except SyntaxError:
            pass
    return sorted(t for t in tokens if t)


def producer_consumer_seeds(
    doc: dict[str, Any], artifact_inventory: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    pr = int(doc["pr_number"])
    complete, repo_files = _repository_files(doc)
    class_by_path = {item["path"]: item["classification"] for item in artifact_inventory}
    seeds: list[dict[str, Any]] = []
    for raw in doc.get("files") or []:
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        path = str(raw["path"])
        classification = class_by_path.get(path, "OTHER")
        for delta in public_surface_deltas(raw, pr, classification):
            refs = [
                r
                for r in reference_candidates(delta["surface_name"], repo_files, path)
                if r["path"] != path
            ]
            seeds.append(
                make_seed(
                    pr,
                    "PRODUCER_CONSUMER",
                    f"{delta['surface_id']}:<coverage>",
                    {
                        "surface_id": delta["surface_id"],
                        "surface_name": delta["surface_name"],
                        "producer_path": path,
                        "consumer_path": "<coverage>",
                        "coverage_only": True,
                        "consumer_count": len(refs),
                        "repository_files_complete": complete,
                    },
                )
            )
            for ref in refs:
                seeds.append(
                    make_seed(
                        pr,
                        "PRODUCER_CONSUMER",
                        f"{delta['surface_id']}:{ref['path']}",
                        {
                            "surface_id": delta["surface_id"],
                            "surface_name": delta["surface_name"],
                            "producer_path": path,
                            "consumer_path": ref["path"],
                            "coverage_only": False,
                            "repository_files_complete": complete,
                        },
                    )
                )
    return seeds


def review_thread_seeds(doc: dict[str, Any]) -> list[dict[str, Any]]:
    pr = int(doc["pr_number"])
    out = []
    for thread in doc.get("review_threads") or []:
        if not isinstance(thread, dict):
            continue
        tid = str(thread.get("thread_id") or thread.get("id") or "UNKNOWN")
        payload = {
            "thread_id": tid,
            "is_resolved": bool(thread.get("is_resolved") is True),
            "author": str(thread.get("author") or "UNKNOWN"),
            "path": thread.get("path"),
            "body_hash": hashlib.sha256(str(thread.get("body") or "").encode()).hexdigest(),
        }
        out.append(make_seed(pr, "REVIEW_THREAD_SEMANTIC", tid, payload))
    return out


def orphan_artifact_seeds(
    doc: dict[str, Any], artifact_inventory: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    pr = int(doc["pr_number"])
    complete, repo_files = _repository_files(doc)
    class_by_path = {item["path"]: item["classification"] for item in artifact_inventory}
    eligible = {"SOURCE", "CONFIGURATION", "SCHEMA", "WORKFLOW", "OTHER"}
    out = []
    for raw in doc.get("files") or []:
        if (
            not isinstance(raw, dict)
            or str(raw.get("status") or "").lower() != "added"
            or not raw.get("path")
        ):
            continue
        path = str(raw["path"])
        classification = class_by_path.get(path, "OTHER")
        if classification not in eligible or is_test_path(path):
            continue
        tokens = _artifact_reference_tokens(raw)
        refs = []
        for token in tokens:
            for ref in reference_candidates(token, repo_files, path):
                if ref["path"] != path:
                    refs.append(ref["path"])
        refs = sorted(set(refs))
        out.append(
            make_seed(
                pr,
                "ORPHAN_ARTIFACT",
                path,
                {
                    "path": path,
                    "classification": classification,
                    "reference_tokens": tokens,
                    "consumer_candidates": refs,
                    "consumer_count": len(refs),
                    "repository_files_complete": complete,
                },
            )
        )
    return out


def is_test_path(path: str) -> bool:
    p = path.lower()
    parts = Path(p).parts
    return (
        "tests" in parts
        or "test" in parts
        or Path(p).name.startswith("test_")
        or ".test." in p
        or ".spec." in p
    )


def make_seed(pr: int, kind: str, subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    immutable = {"pr_number": pr, "closure_kind": kind, "subject": subject, "payload": payload}
    return {
        "closure_id": stable_id("CLOSE", pr, kind, subject),
        "pr_number": pr,
        "closure_kind": kind,
        "subject": subject,
        "seed_hash": seed_hash(immutable),
        "payload": payload,
    }


def build_closure_seeds(
    doc: dict[str, Any],
    artifact_inventory: list[dict[str, Any]],
    deterministic_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pr = int(doc["pr_number"])
    complete, repo_files = _repository_files(doc)
    seeds: list[dict[str, Any]] = []
    public_deltas: list[dict[str, Any]] = []
    hunk_count = edge_count = dep_count = 0
    class_by_path = {item["path"]: item["classification"] for item in artifact_inventory}

    for raw in doc.get("files") or []:
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        path = str(raw["path"])
        classification = class_by_path.get(path, "OTHER")
        patch = str(raw.get("patch") or "")
        deltas = public_surface_deltas(raw, pr, classification)
        public_deltas.extend(deltas)
        for d in deltas:
            seeds.append(
                make_seed(
                    pr,
                    "PUBLIC_CONTRACT",
                    d["surface_id"],
                    {**d, "repository_files_complete": complete},
                )
            )
            refs = [
                r
                for r in reference_candidates(d["surface_name"], repo_files, path)
                if r["path"] != path
            ]
            seeds.append(
                make_seed(
                    pr,
                    "SSOT_UNIQUENESS",
                    f"{d['surface_id']}:<coverage>",
                    {
                        "surface_id": d["surface_id"],
                        "surface_name": d["surface_name"],
                        "owner_path": path,
                        "candidate_path": "<coverage>",
                        "coverage_only": True,
                        "candidate_count": len(refs),
                        "repository_files_complete": complete,
                    },
                )
            )
            for ref in refs:
                seeds.append(
                    make_seed(
                        pr,
                        "SSOT_UNIQUENESS",
                        f"{d['surface_id']}:{ref['path']}",
                        {
                            "surface_id": d["surface_id"],
                            "surface_name": d["surface_name"],
                            "owner_path": path,
                            "candidate_path": ref["path"],
                            "coverage_only": False,
                            "repository_files_complete": complete,
                        },
                    )
                )
        for h in patch_hunks(path, patch, pr):
            hunk_count += 1
            seeds.append(make_seed(pr, "DIFF_HUNK", h["hunk_id"], h))
        for edge in failure_edges(path, patch, pr):
            edge_count += 1
            seeds.append(make_seed(pr, "FAILURE_EDGE", edge["edge_id"], edge))
        for dep in dependency_delta_lines(path, patch, pr):
            dep_count += 1
            seeds.append(make_seed(pr, "DEPENDENCY_CAUSALITY", dep["dependency_delta_id"], dep))
        if classification == "GENERATED" or raw.get("generated") is True:
            payload = {
                "path": path,
                "generator_path": raw.get("generator_path"),
                "source_inputs": raw.get("source_inputs") or [],
                "generation_command": raw.get("generation_command"),
                "generated_head_sha": raw.get("generated_head_sha"),
                "regenerated_sha": raw.get("regenerated_sha"),
            }
            seeds.append(make_seed(pr, "GENERATED_PROVENANCE", path, payload))

    # Optional architecture-control inputs are normalized evidence, not model-invented paths.
    for ctrl in doc.get("architecture_controls") or []:
        if not isinstance(ctrl, dict) or not ctrl.get("boundary_id"):
            continue
        boundary_id = str(ctrl["boundary_id"])
        required_token = str(ctrl.get("required_token") or "")
        protected = [str(x) for x in ctrl.get("protected_tokens") or [] if x]
        candidates = []
        for item in repo_files:
            if any(code_token_present(item["path"], item["content"], tok) for tok in protected):
                has_required = (
                    code_token_present(item["path"], item["content"], required_token)
                    if required_token
                    else False
                )
                candidates.append({"path": item["path"], "required_token_present": has_required})
        seeds.append(
            make_seed(
                pr,
                "BYPASS_PATH",
                f"{boundary_id}:<coverage>",
                {
                    "boundary_id": boundary_id,
                    "required_token": required_token,
                    "protected_tokens": protected,
                    "candidate_path": "<coverage>",
                    "coverage_only": True,
                    "candidate_count": len(candidates),
                    "required_token_present": False,
                    "repository_files_complete": complete,
                },
            )
        )
        for cand in candidates:
            seeds.append(
                make_seed(
                    pr,
                    "BYPASS_PATH",
                    f"{boundary_id}:{cand['path']}",
                    {
                        "boundary_id": boundary_id,
                        "required_token": required_token,
                        "protected_tokens": protected,
                        "candidate_path": cand["path"],
                        "coverage_only": False,
                        "required_token_present": cand["required_token_present"],
                        "repository_files_complete": complete,
                    },
                )
            )

    for sup in doc.get("supersessions") or []:
        if not isinstance(sup, dict) or not sup.get("old_token"):
            continue
        old = str(sup["old_token"])
        sid = str(sup.get("supersession_id") or stable_id("SUP", pr, old))
        refs = reference_candidates(old, repo_files, "")
        if not refs:
            seeds.append(
                make_seed(
                    pr,
                    "SUPERSESSION_LIVENESS",
                    f"{sid}:<none>",
                    {
                        "supersession_id": sid,
                        "old_token": old,
                        "candidate_path": "<none>",
                        "machine_classification": "DEAD",
                        "repository_files_complete": complete,
                    },
                )
            )
        for ref in refs:
            seeds.append(
                make_seed(
                    pr,
                    "SUPERSESSION_LIVENESS",
                    f"{sid}:{ref['path']}",
                    {
                        "supersession_id": sid,
                        "old_token": old,
                        "candidate_path": ref["path"],
                        "machine_classification": classify_reference_path(ref["path"]),
                        "repository_files_complete": complete,
                    },
                )
            )

    for cfg in doc.get("configuration_keys") or []:
        if not isinstance(cfg, dict) or not cfg.get("key"):
            continue
        key = str(cfg["key"])
        sources = []
        for s in cfg.get("sources") or []:
            if isinstance(s, dict) and s.get("path"):
                sources.append(
                    {
                        "path": str(s["path"]),
                        "authority_kind": str(s.get("authority_kind") or "UNKNOWN"),
                        "precedence": s.get("precedence"),
                    }
                )
        seeds.append(
            make_seed(
                pr,
                "CONFIG_PRECEDENCE",
                key,
                {"key": key, "sources": sources, "repository_files_complete": complete},
            )
        )

    dep_paths = {str(x.get("path")) for x in doc.get("files") or [] if isinstance(x, dict)}
    manifest_lock_pairs = [
        ("pyproject.toml", {"poetry.lock", "pdm.lock", "uv.lock"}),
        ("package.json", {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}),
        ("go.mod", {"go.sum"}),
        ("Cargo.toml", {"Cargo.lock"}),
    ]
    for manifest, locks in manifest_lock_pairs:
        if manifest in dep_paths or any(l in dep_paths for l in locks):
            seeds.append(
                make_seed(
                    pr,
                    "DEPENDENCY_PAIRING",
                    manifest,
                    {
                        "manifest": manifest,
                        "locks": sorted(locks),
                        "changed_paths": sorted(dep_paths & ({manifest} | locks)),
                    },
                )
            )

    for candidate in deterministic_candidates:
        kind = candidate.get("kind")
        if isinstance(kind, str) and (
            kind.startswith("NEW_") or kind in {"COMPATIBILITY_LAYER", "FEATURE_FLAG"}
        ):
            seeds.append(
                make_seed(pr, "ARCHITECTURE_ECONOMY", candidate["candidate_id"], candidate)
            )

    for failure in doc.get("ci_failures") or []:
        if isinstance(failure, dict):
            name = str(failure.get("name") or "UNKNOWN")
            seeds.append(
                make_seed(
                    pr,
                    "CI_CAUSALITY",
                    name,
                    {
                        "name": name,
                        "required": bool(failure.get("required") is True),
                        "conclusion": str(failure.get("conclusion") or "UNKNOWN"),
                    },
                )
            )

    # v2.0 deterministic closures.
    pc = producer_consumer_seeds(doc, artifact_inventory)
    seeds.extend(pc)
    rt = review_thread_seeds(doc)
    seeds.extend(rt)
    orphan = orphan_artifact_seeds(doc, artifact_inventory)
    seeds.extend(orphan)
    mut = []
    for raw in doc.get("files") or []:
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        if is_test_path(str(raw["path"])):
            continue
        for candidate in mutation_candidates(raw, pr):
            mut.append(candidate)
            seeds.append(make_seed(pr, "MUTATION_EXECUTION", candidate["mutation_id"], candidate))

    return seeds, {
        "repository_files_complete": complete,
        "public_contract_delta_count": len(public_deltas),
        "diff_hunk_count": hunk_count,
        "failure_edge_count": edge_count,
        "dependency_delta_count": dep_count,
        "producer_consumer_seed_count": len(pc),
        "review_thread_seed_count": len(rt),
        "orphan_artifact_seed_count": len(orphan),
        "mutation_candidate_count": len(mut),
        "closure_seed_count": len(seeds),
    }
