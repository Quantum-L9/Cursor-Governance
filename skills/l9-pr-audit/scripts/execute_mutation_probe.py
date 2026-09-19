#!/usr/bin/env python3
"""Execute one deterministic mutation probe in an isolated temporary copy.

The audited repository is never edited in place. By default the test command is
parsed into argv and executed without a shell. Shell syntax requires explicit
``--allow-shell`` authorization. The temporary copy is filesystem isolation, not
an OS/process sandbox; execute only an authorized project validation command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - fail closed in unsupported runtimes
    raise SystemExit("jsonschema>=4 is required to validate mutation-probe results") from exc


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_candidate(path: Path, c: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    sl, sc, el, ec = c["line"] - 1, c["column"], c["end_line"] - 1, c["end_column"]
    if sl >= len(lines) or el >= len(lines):
        raise ValueError("candidate range outside source")
    if sl == el:
        current = lines[sl][sc:ec]
        if current != c["original_source"]:
            raise ValueError("candidate original_source does not match bound source range")
        lines[sl] = lines[sl][:sc] + c["mutant_source"] + lines[sl][ec:]
    else:
        current = lines[sl][sc:] + "".join(lines[sl + 1 : el]) + lines[el][:ec]
        if current != c["original_source"]:
            raise ValueError(
                "candidate original_source does not match bound multi-line source range"
            )
        lines[sl : el + 1] = [lines[sl][:sc] + c["mutant_source"] + lines[el][ec:]]
    path.write_text("".join(lines), encoding="utf-8")


def _hash_text(value: str | bytes | None) -> str:
    if value is None:
        data = b""
    elif isinstance(value, bytes):
        data = value
    else:
        data = value.encode()
    return hashlib.sha256(data).hexdigest()


def run(command: str, cwd: Path, timeout: int, *, allow_shell: bool) -> dict[str, Any]:
    if not command.strip():
        return {
            "exit_code": None,
            "timed_out": False,
            "execution_error": "EMPTY_COMMAND",
            "stdout_hash": _hash_text(""),
            "stderr_hash": _hash_text(""),
        }
    argv: str | list[str]
    if allow_shell:
        argv = command
    else:
        try:
            argv = shlex.split(command)
        except ValueError:
            return {
                "exit_code": None,
                "timed_out": False,
                "execution_error": "COMMAND_PARSE_ERROR",
                "stdout_hash": _hash_text(""),
                "stderr_hash": _hash_text(""),
            }
        if not argv:
            return {
                "exit_code": None,
                "timed_out": False,
                "execution_error": "EMPTY_COMMAND",
                "stdout_hash": _hash_text(""),
                "stderr_hash": _hash_text(""),
            }
    try:
        # nosec B602 - shell is opt-in and off by default. `--allow-shell` is
        # store_true, so the default path above is shlex.split with shell=False;
        # the string form is reached only when the operator asks for it for a
        # test command that needs a shell. The command is the operator's own
        # `--test-command`, run in a disposable copy of the tree by an operator
        # who already has a shell, so this is not a privilege boundary. The
        # choice is recorded in the probe output as execution_mode
        # SHELL_EXPLICIT / ARGV_NO_SHELL rather than left implicit.
        # Bytes, not text: only stable hashes of the output are ever recorded,
        # so decoding buys nothing and adds a failure mode. A test command that
        # emits bytes undecodable under the ambient locale would raise
        # UnicodeDecodeError here and the probe would die without writing a
        # schema-valid result. Hashing the raw bytes is also locale-independent,
        # which a deterministic probe needs.
        cp = subprocess.run(  # noqa: S602
            argv,
            shell=allow_shell,  # nosec B602
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "exit_code": cp.returncode,
            "timed_out": False,
            "execution_error": None,
            "stdout_hash": _hash_text(cp.stdout),
            "stderr_hash": _hash_text(cp.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "timed_out": True,
            "execution_error": None,
            "stdout_hash": _hash_text(exc.stdout),
            "stderr_hash": _hash_text(exc.stderr),
        }
    except OSError as exc:
        return {
            "exit_code": None,
            "timed_out": False,
            "execution_error": type(exc).__name__,
            "stdout_hash": _hash_text(""),
            "stderr_hash": _hash_text(""),
        }


def _validate_result(result: dict[str, Any]) -> None:
    schema_path = (
        Path(__file__).resolve().parent.parent / "schemas" / "mutation-probe-result.schema.json"
    )
    if not schema_path.is_file():
        raise RuntimeError("mutation-probe result schema is missing")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(result), key=lambda e: list(e.path))
    if errors:
        rendered = "; ".join(
            f"{'.'.join(str(x) for x in e.path) or '$'}: {e.message}" for e in errors
        )
        raise RuntimeError("mutation-probe result failed schema validation: " + rendered)


def _write_result(result: dict[str, Any], output: Path | None) -> None:
    _validate_result(result)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--test-command", required=True)
    ap.add_argument(
        "--allow-shell",
        action="store_true",
        help="explicitly permit shell parsing/operators for the authorized test command",
    )
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if a.timeout < 1:
        raise SystemExit("--timeout must be >= 1")

    c = json.loads(a.candidate.read_text(encoding="utf-8"))
    repo = a.repo_root.resolve()
    original = (repo / c["path"]).resolve()
    if repo not in original.parents:
        raise SystemExit("candidate path escapes repo root")
    if not original.is_file():
        raise SystemExit("candidate path is not a regular file")
    before = sha(original)
    if before != c["source_sha256"]:
        raise SystemExit("audited source hash does not match mutation candidate")

    result: dict[str, Any] = {
        "schema_version": "l9.pr-audit.mutation-probe-result.v2.0",
        "mutation_id": c["mutation_id"],
        "path": c["path"],
        "execution_mode": "SHELL_EXPLICIT" if a.allow_shell else "ARGV_NO_SHELL",
        "test_command_sha256": hashlib.sha256(a.test_command.encode()).hexdigest(),
        "original_repository_sha_before": before,
    }

    exit_code = 2
    try:
        with tempfile.TemporaryDirectory(prefix="l9-pr-audit-mut-") as td:
            tmp = Path(td) / "repo"
            shutil.copytree(
                repo,
                tmp,
                symlinks=True,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    # Large, regenerable, and never the subject of a mutation
                    # probe. Copying them makes the probe slow and disk-hungry
                    # for no discrimination value.
                    ".venv",
                    "venv",
                    "node_modules",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                    ".tox",
                    ".l9",
                ),
            )
            baseline = run(a.test_command, tmp, a.timeout, allow_shell=a.allow_shell)
            result["baseline"] = baseline
            if baseline["timed_out"]:
                result["result"] = "BASELINE_FAILED"
                result["reason"] = "baseline validation timed out"
            elif baseline["execution_error"]:
                result["result"] = "EXECUTION_ERROR"
                result["reason"] = f"baseline execution error: {baseline['execution_error']}"
            elif baseline["exit_code"] != 0:
                result["result"] = "BASELINE_FAILED"
                result["reason"] = "baseline validation did not pass"
            else:
                target = tmp / c["path"]
                # The disposable copy is the whole safety story of this probe,
                # and `symlinks=True` can undo it. The containment check on the
                # audited side resolves the *target* of a link, so a repo path
                # that is an absolute symlink (or sits under one) passes it —
                # and copytree then recreates that same absolute link inside
                # `tmp`. Writing through it would mutate the audited working
                # tree permanently, which is exactly what this probe promises
                # never to do. Re-check containment on the copy, after copying.
                resolved_target = target.resolve()
                if not resolved_target.is_relative_to(tmp.resolve()):
                    result["result"] = "EXECUTION_ERROR"
                    result["reason"] = (
                        "candidate path escapes the disposable copy via a link; "
                        "refusing to mutate outside the temporary tree"
                    )
                    # `finally` below writes the result and runs the audited-tree
                    # integrity check, so returning here still emits a
                    # schema-valid outcome.
                    return 2
                try:
                    apply_candidate(target, c)
                except (ValueError, OSError, UnicodeError) as exc:
                    # A candidate that will not apply is evidence about the
                    # candidate, not a reason to die without a result. Emitting
                    # a schema-valid EXECUTION_ERROR keeps the deterministic
                    # closure pipeline able to read an outcome for every probe.
                    result["result"] = "EXECUTION_ERROR"
                    result["reason"] = f"candidate application failed: {type(exc).__name__}"
                    return 2
                mutant = run(a.test_command, tmp, a.timeout, allow_shell=a.allow_shell)
                result["mutant"] = mutant
                if mutant["timed_out"]:
                    result["result"] = "EXECUTION_ERROR"
                    result["reason"] = "mutant validation timed out"
                elif mutant["execution_error"]:
                    result["result"] = "EXECUTION_ERROR"
                    result["reason"] = f"mutant execution error: {mutant['execution_error']}"
                elif mutant["exit_code"] != 0:
                    result["result"] = "KILLED"
                    exit_code = 0
                else:
                    result["result"] = "SURVIVED"
                    exit_code = 1
    finally:
        after = sha(original)
        result["original_repository_sha_after"] = after
        result["original_repository_unchanged"] = before == after
        if not result["original_repository_unchanged"]:
            result["result"] = "EXECUTION_ERROR"
            result["reason"] = "audited repository changed during mutation probe"
            exit_code = 3
        _write_result(result, a.output)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
