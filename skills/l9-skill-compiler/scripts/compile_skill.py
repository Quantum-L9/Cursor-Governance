#!/usr/bin/env python3
"""Operator-facing terminal facade for the ``skill-compiler-v2`` DAG.

This module normalizes ergonomic operator input into the canonical
``CompileRequest`` and hands it to the DAG runner. It deliberately owns no
compilation semantics: it never imports a compiler stage module, never
sequences stages, and never decides a terminal state of its own. Every
compilation outcome in its output originates in the DAG.

    OPERATOR INPUT -> compile_skill.py -> CompileRequest -> skill-compiler-v2 DAG
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

PACK = pathlib.Path(__file__).resolve().parent.parent
REPO = PACK.parent.parent
RUNNER_MODULE = "workflows.dags.skill_compiler_runner"
RUNNER_PATH = REPO / "workflows" / "dags" / "skill_compiler_runner.py"

# Typed failure classes and their operator exit codes. 0 PASS, 2 invalid
# operator input, 3 BLOCKED, 4 compilation/runtime FAIL, 5 validation FAIL,
# 10 internal/unclassified.
ERRORS = {
    "INVALID_ARGUMENTS": (2, "FAIL"),
    "REQUEST_PARSE_FAILED": (2, "FAIL"),
    "REQUEST_SCHEMA_INVALID": (2, "FAIL"),
    "SOURCE_NOT_FOUND": (2, "FAIL"),
    "SKILL_NOT_FOUND": (2, "FAIL"),
    "TOPOLOGY_BLOCKED": (3, "BLOCKED"),
    "DAG_NOT_AVAILABLE": (3, "BLOCKED"),
    "DAG_EXECUTION_FAILED": (4, "FAIL"),
    "COMPILATION_BLOCKED": (3, "BLOCKED"),
    "COMPILATION_FAILED": (4, "FAIL"),
    "VALIDATION_FAILED": (5, "FAIL"),
    "UNKNOWN": (10, "FAIL"),
}

DEFAULT_PROFILES = ["portable", "l9"]


class OperatorError(Exception):
    """A typed failure with an operator-readable message and machine detail."""

    def __init__(self, code, message, detail=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


# --------------------------------------------------------------------------
# runner binding
# --------------------------------------------------------------------------


def load_runner():
    """Import the DAG runner, preferring the canonical package path."""
    try:
        return importlib.import_module(RUNNER_MODULE)
    except ImportError:
        pass
    if not RUNNER_PATH.exists():
        raise OperatorError(
            "DAG_NOT_AVAILABLE",
            "skill-compiler-v2 runner is not present at " + str(RUNNER_PATH),
        )
    spec = importlib.util.spec_from_file_location(RUNNER_MODULE, RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[RUNNER_MODULE] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - defensive
        raise OperatorError("DAG_NOT_AVAILABLE", "runner failed to load: " + str(exc)) from exc
    return module


# --------------------------------------------------------------------------
# operator input -> canonical CompileRequest
# --------------------------------------------------------------------------


def load_request_file(path):
    """Load a request from JSON or YAML into one canonical Python object.

    YAML is an input convenience only. Both formats produce the same object and
    are validated by the one canonical ``compile-request.schema.json`` inside
    the DAG's binding stage. There is no YAML-specific schema.
    """
    target = pathlib.Path(path)
    if not target.is_file():
        raise OperatorError("REQUEST_PARSE_FAILED", "request file not found: " + str(path))
    text = target.read_text(encoding="utf-8")
    suffix = target.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            import yaml

            loaded = yaml.safe_load(text)
        else:
            loaded = json.loads(text)
    except Exception as exc:
        raise OperatorError(
            "REQUEST_PARSE_FAILED", "could not parse " + str(path) + ": " + str(exc)
        ) from exc
    if not isinstance(loaded, dict):
        raise OperatorError(
            "REQUEST_PARSE_FAILED", "request must be a mapping, got " + type(loaded).__name__
        )
    return loaded


def skill_roots(extra=None):
    roots = [REPO / "skills"]
    for root in extra or []:
        roots.append(pathlib.Path(root))
    return [root for root in roots if root.is_dir()]


def resolve_skill(token, extra_roots=None):
    """Resolve an operator token to one live skill, using repository topology.

    Accepts ``l9-name``, ``skills/l9-name`` or a path. A basename that matches
    more than one live skill is never guessed: it is surfaced as BLOCKED with
    the candidates.
    """
    roots = skill_roots(extra_roots)
    if not roots:
        raise OperatorError("SKILL_NOT_FOUND", "no live skills root found under " + str(REPO))

    candidate_path = pathlib.Path(token)
    if candidate_path.is_dir() and (candidate_path / "SKILL.md").is_file():
        return candidate_path.resolve().name, str(candidate_path)

    name = candidate_path.name.rstrip("/") or token
    matches = []
    for root in roots:
        if (root / name / "SKILL.md").is_file():
            matches.append(str(root / name))
    if not matches:
        for root in roots:
            for entry in sorted(root.iterdir()):
                if entry.is_dir() and (entry / "SKILL.md").is_file() and entry.name.endswith(name):
                    matches.append(str(entry))
    if not matches:
        raise OperatorError(
            "SKILL_NOT_FOUND",
            "no live skill resolves from " + token,
            {"searched_roots": [str(root) for root in roots]},
        )
    if len(set(matches)) > 1:
        raise OperatorError(
            "TOPOLOGY_BLOCKED",
            "ambiguous skill resolution for " + token,
            {"candidates": sorted(set(matches))},
        )
    resolved = matches[0]
    return pathlib.Path(resolved).name, resolved


def skill_description(pack_dir):
    """Read the ``description`` field from a live pack's SKILL.md frontmatter.

    Operator-input derivation, not a compiler stage: it only supplies a default
    ``stated_objective`` when the operator did not pass ``--objective``.
    """
    skill_md = pathlib.Path(pack_dir) / "SKILL.md"
    if not skill_md.is_file():
        return ""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    try:
        import yaml

        parsed = yaml.safe_load(text[4:end]) or {}
    except Exception:
        return ""
    if not isinstance(parsed, dict):
        return ""
    description = parsed.get("description")
    if not description and isinstance(parsed.get("metadata"), dict):
        description = parsed["metadata"].get("description")
    return description or ""


def _profiles(selected):
    """Selected profiles, deduplicated, with the required pair ordered first."""
    if not selected:
        return list(DEFAULT_PROFILES)
    ordered = []
    for profile in list(DEFAULT_PROFILES) + list(selected):
        if profile in selected and profile not in ordered:
            ordered.append(profile)
    return ordered


def _request_id(args, fallback):
    return args.request_id or fallback


def normalize_request(args):
    """Build the canonical CompileRequest for a parsed operator invocation.

    Returns ``(request, context)`` where ``context`` carries resolution facts
    the machine output reports but the request itself does not carry.
    """
    context = {"resolved_skill": None, "resolved_pack": None, "source_refs": []}

    if args.command == "compile":
        request = load_request_file(args.request)
        if args.request_id:
            request["request_id"] = args.request_id
        if args.profile:
            request["target_profiles"] = _profiles(args.profile)
        if args.objective:
            request.setdefault("subject", {})["stated_objective"] = args.objective
        context["source_refs"] = [
            item.get("ref") for item in request.get("source_material", []) if isinstance(item, dict)
        ]
        subject = request.get("subject") if isinstance(request.get("subject"), dict) else {}
        named = subject.get("existing_skill") or subject.get("proposed_name")
        if named:
            try:
                context["resolved_skill"], context["resolved_pack"] = resolve_skill(
                    named, args.skills_root
                )
            except OperatorError as exc:
                if exc.code == "TOPOLOGY_BLOCKED":
                    raise
                # A request may legitimately name a Skill that does not exist
                # yet; the DAG's topology stage owns that decision, not the CLI.
                context["resolved_skill"] = None
        return request, context

    if args.command in ("optimize", "rebuild"):
        name, pack = resolve_skill(args.skill, args.skills_root)
        context["resolved_skill"] = name
        context["resolved_pack"] = pack
        context["source_refs"] = [os.path.relpath(pack, REPO)]
        intent = "evolve" if args.command == "optimize" else "rebuild"
        objective = args.objective or skill_description(pack)
        request = {
            "request_id": _request_id(args, args.command + ":" + name),
            "intent": intent,
            "subject": {
                "proposed_name": name,
                "existing_skill": name,
                "stated_objective": objective,
            },
            "source_material": [{"kind": "dir", "ref": os.path.relpath(pack, REPO)}],
            "target_profiles": _profiles(args.profile),
        }
        return request, context

    if args.command == "create":
        source = args.source
        located = pathlib.Path(source)
        if located.is_file():
            kind = "file"
        elif located.is_dir():
            kind = "dir"
        elif "://" in source:
            kind = "url"
        else:
            raise OperatorError(
                "SOURCE_NOT_FOUND",
                "source is neither an existing path nor a locator: " + source,
            )
        ref = str(located) if kind in ("file", "dir") else source
        context["source_refs"] = [ref]
        request = {
            "request_id": _request_id(args, "create:" + args.name),
            "intent": "create",
            "subject": {
                "proposed_name": args.name,
                "existing_skill": None,
                "stated_objective": args.objective or "",
            },
            "source_material": [{"kind": kind, "ref": ref}],
            "target_profiles": _profiles(args.profile),
        }
        return request, context

    raise OperatorError("INVALID_ARGUMENTS", "unsupported command " + str(args.command))


# --------------------------------------------------------------------------
# DAG invocation
# --------------------------------------------------------------------------


def _validation_nodes(dag):
    """Node ids the DAG itself classifies as validation nodes."""
    try:
        return {
            node.id
            for node in dag.SKILL_COMPILER_SESSION_DAG.nodes
            if getattr(node.node_type, "name", "") == "VALIDATE"
        }
    except AttributeError:  # pragma: no cover - defensive
        return set()


def _binding_nodes(dag):
    """Node ids the DAG declares as request binding/validation."""
    return {node["id"] for node in dag.NODES if node.get("impl") == "bind_and_validate_inputs"}


def classify_run(dag, result):
    """Map a DAG run outcome onto a typed CLI error class.

    Classification is read off the graph, not off a hand-written stage list.
    """
    if result.status == "PASS":
        return None
    failed = [record for record in result.stages if record.status == "fail"]
    if failed:
        node = failed[0].node
        if node in _binding_nodes(dag):
            return "REQUEST_SCHEMA_INVALID"
        if node in _validation_nodes(dag):
            if failed[0].exit_code == 3:
                return "COMPILATION_BLOCKED"
            return "VALIDATION_FAILED"
        return "COMPILATION_FAILED"
    if result.terminal_state in ("BOUNDED_LLM_REQUIRED", "BLOCKED"):
        return "COMPILATION_BLOCKED"
    if result.errors:
        return "DAG_EXECUTION_FAILED"
    return "UNKNOWN"


def invoke(args, request, resolution):
    runner = load_runner()
    workdir = (
        pathlib.Path(args.output_dir)
        if args.output_dir
        else pathlib.Path(tempfile.mkdtemp(prefix="skill-compiler-"))
    )
    workdir.mkdir(parents=True, exist_ok=True)
    request_path = workdir / "compile-request.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    render_outdir = str(workdir / "render")
    # The pack under validation is the live pack when one resolves, otherwise
    # the directory this run renders into. It is never allowed to fall back to
    # the compiler's own pack.
    pack = resolution.get("resolved_pack") or render_outdir
    context = runner.RunContext(
        request=str(request_path),
        ir=args.ir,
        ir_out=str(workdir / "skill-ir.json") if args.ir and not args.dry_run else None,
        render_outdir=render_outdir if not args.dry_run else None,
        pack=pack,
        skills_dir=str(REPO / "skills"),
        repo_root=str(REPO),
        target_profiles=list(request.get("target_profiles", [])),
        dry_run=bool(args.dry_run),
        skip_nodes=["PACKAGE"] if args.no_package else [],
    )
    dag, _, _ = runner.load_canonical_dag()
    return runner.run(context, dag=dag), dag, str(request_path), str(workdir)


# --------------------------------------------------------------------------
# machine output
# --------------------------------------------------------------------------


def build_output(args, request, resolution, result, request_path, workdir, dag):
    error_code = classify_run(dag, result) if result is not None else None
    receipt = None
    if args.receipt_path:
        receipt = {
            "path": args.receipt_path,
            "schema": "l9/skill-compiler/build-receipt",
            "build_receipt_complete": bool(result and result.build_succeeded),
            "reason": (
                None
                if result and result.build_succeeded
                else "run did not terminate in a completed build; no BuildReceipt is claimed"
            ),
        }
    output = {
        "request_id": request.get("request_id", "") if request else "",
        "command": args.command,
        "intent": request.get("intent", "") if request else "",
        "normalized_request": request or {},
        "normalized_request_path": request_path,
        "workdir": workdir,
        "resolution": resolution,
        "topology_decision": result.topology_decision if result else None,
        "skill_profile": result.skill_profile if result else None,
        "dag": {
            "id": dag.SKILL_COMPILER_V2["id"] if dag else "skill-compiler-v2",
            "terminal_state": result.terminal_state if result else None,
            "source": result.dag_source if result else None,
            "planned_order": result.planned_order if result else [],
        },
        "stages": [vars(record) for record in result.stages] if result else [],
        "pending_bounded_llm": result.pending_bounded_llm if result else [],
        "dry_run": bool(args.dry_run),
        "build_succeeded": bool(result.build_succeeded) if result else False,
        "receipt": receipt,
        "artifacts": result.artifacts if result else [],
        "unknowns": result.unknowns if result else [],
        "errors": list(result.errors) if result else [],
        "status": result.status if result else "FAIL",
    }
    if error_code:
        output["error_code"] = error_code
        output["status"] = ERRORS[error_code][1]
    return output, error_code


def _summary(output):
    lines = [
        "command: " + str(output.get("command")),
        "intent: " + str(output.get("intent")),
        "dag: "
        + str(output["dag"]["id"])
        + " terminal_state="
        + str(output["dag"]["terminal_state"]),
        "status: "
        + str(output.get("status"))
        + " build_succeeded="
        + str(output.get("build_succeeded")),
    ]
    decision = output.get("topology_decision") or {}
    if isinstance(decision, dict) and decision.get("decision"):
        lines.append("topology_decision: " + str(decision["decision"]))
    profile = output.get("skill_profile") or {}
    if isinstance(profile, dict) and isinstance(profile.get("profile"), dict):
        lines.append("skill_profile: " + str(profile["profile"].get("primary_family")))
    for pending in output.get("pending_bounded_llm", []):
        lines.append(
            "requires bounded LLM: " + pending["node"] + " -> " + str(pending.get("contract"))
        )
    if output.get("dry_run"):
        lines.append(
            "dry-run: planned only; no pack write, wiring, registration, or commit occurred"
        )
    if output.get("error_code"):
        lines.append("error_code: " + output["error_code"])
    return "\n".join(lines)


# --------------------------------------------------------------------------
# argument parsing
# --------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="compile_skill.py",
        description="Operator facade for the skill-compiler-v2 DAG.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(target):
        target.add_argument("--dry-run", action="store_true")
        target.add_argument("--output-json", action="store_true")
        target.add_argument("--request-id")
        target.add_argument(
            "--profile",
            action="append",
            choices=sorted(["portable", "l9", "cursor", "claude_code", "openai"]),
        )
        target.add_argument("--objective")
        target.add_argument("--receipt-path")
        target.add_argument("--output-dir")
        target.add_argument("--no-package", action="store_true")
        target.add_argument(
            "--ir",
            help="skill IR produced by the bounded-LLM stages, per contracts/skill-ir.schema.json",
        )
        target.add_argument("--skills-root", action="append")

    for name, help_text in (
        ("optimize", "evolve an existing live Skill"),
        ("rebuild", "rebuild an existing live Skill"),
    ):
        node = sub.add_parser(name, help=help_text)
        node.add_argument("skill", help="l9-skill-name or skills/l9-skill-name")
        common(node)

    node = sub.add_parser("compile", help="compile a canonical request file (JSON or YAML)")
    node.add_argument("request")
    common(node)

    node = sub.add_parser("create", help="compile a new Skill from source material")
    node.add_argument("--name", required=True)
    node.add_argument("--source", required=True)
    common(node)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    # Machine output must stay parseable. Importing the DAG registers it in the
    # session registry, which logs; every such side-effect goes to stderr and
    # only the result object reaches real stdout.
    machine_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        return _run(args, machine_stdout)
    finally:
        sys.stdout = machine_stdout


def _run(args, machine_stdout):
    # Only these two are read on the exception path below. result, dag,
    # request_path and workdir come back from invoke() and are read only after
    # it returns, so pre-initializing them would be dead.
    request, resolution = None, {}
    try:
        request, resolution = normalize_request(args)
        result, dag, request_path, workdir = invoke(args, request, resolution)
    except OperatorError as exc:
        exit_code, status = ERRORS[exc.code]
        output = {
            "request_id": (request or {}).get("request_id", ""),
            "command": args.command,
            "intent": (request or {}).get("intent", ""),
            "normalized_request": request or {},
            "topology_decision": None,
            "skill_profile": None,
            "dag": {"id": "skill-compiler-v2", "terminal_state": None},
            "receipt": None,
            "artifacts": [],
            "unknowns": [],
            "errors": [{"code": exc.code, "message": exc.message, "detail": exc.detail}],
            "status": status,
            "error_code": exc.code,
            "build_succeeded": False,
            "dry_run": bool(getattr(args, "dry_run", False)),
        }
        sys.stderr.write(exc.code + ": " + exc.message + "\n")
        if exc.detail:
            sys.stderr.write(json.dumps(exc.detail, indent=2, sort_keys=True) + "\n")
        if args.output_json:
            machine_stdout.write(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n")
        return exit_code

    output, error_code = build_output(args, request, resolution, result, request_path, workdir, dag)
    if args.receipt_path:
        receipt_file = pathlib.Path(args.receipt_path)
        receipt_file.parent.mkdir(parents=True, exist_ok=True)
        receipt_file.write_text(
            json.dumps(output, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )

    if args.output_json:
        machine_stdout.write(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n")
    else:
        machine_stdout.write(_summary(output) + "\n")
    if error_code:
        sys.stderr.write(error_code + ": see stage records for the failing node\n")
        return ERRORS[error_code][0]
    return 0


if __name__ == "__main__":
    sys.exit(main())
