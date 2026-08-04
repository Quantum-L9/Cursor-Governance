#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

from common import (
    TEXT_EXTENSIONS,
    iter_files,
    normalize_distribution,
    read_text,
    relative,
    run,
    stable_id,
    utc_now,
    write_json,
)

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".c": "c_cpp",
    ".h": "c_cpp",
    ".cpp": "c_cpp",
    ".hpp": "c_cpp",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
}

MANIFEST_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-ci.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "package.json",
    "pnpm-workspace.yaml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
}

LOCK_NAMES = {
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "Cargo.lock",
    "go.sum",
    "Gemfile.lock",
    "composer.lock",
}

CONFIG_NAMES = {
    "ruff.toml",
    ".ruff.toml",
    "mypy.ini",
    ".mypy.ini",
    "pytest.ini",
    "tox.ini",
    "noxfile.py",
    ".pre-commit-config.yaml",
    ".pre-commit-config.yml",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    ".eslintrc",
    ".eslintrc.json",
    "tsconfig.json",
    "vitest.config.ts",
    "jest.config.js",
    "jest.config.ts",
    "biome.json",
    "biome.jsonc",
    "Makefile",
    "Taskfile.yml",
    "justfile",
}

PY_STDLIB = set(getattr(sys, "stdlib_module_names", set()))
IMPORT_DIST_OVERRIDES = {
    "yaml": "pyyaml",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "attr": "attrs",
    "attrs": "attrs",
    "OpenSSL": "pyopenssl",
    "google": "google-api-python-client",
    "jwt": "pyjwt",
    "redis": "redis",
    "usb": "pyusb",
    "serial": "pyserial",
    "zmq": "pyzmq",
}

# Directory names that mark historical / non-active source. The Python import and
# first-party analyses skip these so archived code (e.g. an old flask API kept for
# reference) never manufactures a phantom undeclared-dependency finding.
ARCHIVE_DIR_NAMES = {
    "_archived",
    "_archive",
    "archive",
    "archived",
    "wip",
    "current_work",
    "c_gov_files",
    ".cursor",
    ".cursor-commands",
    "examples",
    "example",
    "fixtures",
    "vendor",
    "third_party",
    "site-packages",
}


def is_archived_rel(rel: str) -> bool:
    """True when a repo-relative path lies under a historical / non-active directory."""
    return any(part.lower() in ARCHIVE_DIR_NAMES for part in Path(rel).parts)


def is_test_content(path: Path) -> bool | None:
    """Structurally decide whether a Python file is real test content.

    Returns True when the module actually defines test functions / TestCase-style
    classes or imports a test framework, False when it merely matches a test_*
    naming convention (e.g. a `test_pipeline_dag.py` DAG module), and None when the
    file cannot be parsed. This replaces filename-only classification so an ignored
    non-test file is not reported as a hidden suite, and a genuinely test-bearing
    file that is *not* named test_* is still recognized.
    """
    text = read_text(path)
    if text is None:
        return None
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test"
        ):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            if any(
                isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                and member.name.startswith("test")
                for member in node.body
            ):
                return True
        if isinstance(node, ast.Import):
            if any(alias.name.split(".", 1)[0] in {"pytest", "unittest"} for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".", 1)[0] in {"pytest", "unittest"}:
                return True
    return False


def repo_python_modules(root: Path, files: list[Path]) -> set[str]:
    """Top-level importable names that resolve to first-party source in the repo.

    A name is first-party when the tree contains a package or module by that name:
    a top-level directory, a top-level `*.py` stem, a `src/<name>` package, or any
    `<name>/__init__.py`. Import roots resolving here are internal, never flagged as
    undeclared third-party dependencies.
    """
    names: set[str] = set()
    for child in root.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_dir():
            names.add(child.name.replace("-", "_"))
        elif child.suffix == ".py":
            names.add(child.stem.replace("-", "_"))
    src = root / "src"
    if src.is_dir():
        for child in src.iterdir():
            if child.is_dir() or child.suffix == ".py":
                names.add(child.stem.replace("-", "_"))
    for path in files:
        if path.suffix != ".py":
            continue
        names.add(path.stem.replace("-", "_"))
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        # Every directory on the path to a .py file is an importable first-party
        # package candidate — covers nested packages and modules reached through a
        # runtime sys.path root (e.g. environment/claude-code/memory, tools.validation).
        for part in rel.parts[:-1]:
            names.add(part.replace("-", "_"))
    return names


def conflict_marker_kind(line: str) -> str | None:
    """Classify a line as a real VCS conflict marker, or None.

    Git writes exactly seven `<`, `=`, or `>` followed by end-of-line or a label.
    A decorated `===...` docstring underline (any length other than seven, and never
    flanked by `<<<<<<<`/`>>>>>>>`) is not a marker — matching it was the source of
    the false-positive `critical` finding on archived banner comments.
    """
    stripped = line.rstrip("\r\n")
    if re.match(r"<<<<<<<(?:\s|$)", stripped):
        return "open"
    if re.match(r">>>>>>>(?:\s|$)", stripped):
        return "close"
    if re.fullmatch(r"={7}", stripped):
        return "sep"
    return None


def finding(
    finding_class: str,
    severity: str,
    summary: str,
    consequence: str,
    recommendation: str,
    evidence: list[dict[str, Any]],
    confidence: str = "high",
) -> dict[str, Any]:
    evidence_key = json.dumps(evidence, sort_keys=True)
    return {
        "id": stable_id(finding_class, summary, evidence_key),
        "class": finding_class,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "consequence": consequence,
        "recommendation": recommendation,
        "evidence": evidence,
    }


def parse_pyproject(path: Path) -> dict[str, Any]:
    if not path.exists() or tomllib is None:
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}


def parse_python_declared(root: Path, pyproject: dict[str, Any]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    project = pyproject.get("project", {}) if isinstance(pyproject, dict) else {}
    for dep in project.get("dependencies", []) or []:
        groups["project"].append(normalize_distribution(str(dep)))
    for name, deps in (project.get("optional-dependencies", {}) or {}).items():
        for dep in deps or []:
            groups[f"optional:{name}"].append(normalize_distribution(str(dep)))
    for name, deps in (pyproject.get("dependency-groups", {}) or {}).items():
        for dep in deps or []:
            if isinstance(dep, str):
                groups[f"group:{name}"].append(normalize_distribution(dep))
    for requirements in sorted(root.glob("requirements*.txt")):
        text = read_text(requirements) or ""
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            groups[f"file:{requirements.name}"].append(normalize_distribution(line))
    return {key: sorted(set(value)) for key, value in sorted(groups.items())}


def parse_node_declared(root: Path) -> dict[str, Any]:
    package_path = root / "package.json"
    if not package_path.exists():
        return {}
    try:
        data = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"parse_error": True}
    result: dict[str, Any] = {"scripts": data.get("scripts", {}) or {}}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        result[key] = sorted((data.get(key, {}) or {}).keys())
    result["package_manager"] = data.get("packageManager")
    result["workspaces"] = data.get("workspaces")
    return result


def python_imports(root: Path, files: list[Path]) -> tuple[list[str], list[dict[str, Any]]]:
    roots: Counter[str] = Counter()
    syntax_errors: list[dict[str, Any]] = []
    for path in files:
        if path.suffix not in {".py", ".pyi"}:
            continue
        text = read_text(path)
        if text is None:
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            syntax_errors.append(
                {
                    "path": relative(root, path),
                    "line": exc.lineno or 0,
                    "message": exc.msg,
                }
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots[alias.name.split(".", 1)[0]] += 1
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots[node.module.split(".", 1)[0]] += 1
    return sorted(roots), syntax_errors


def extract_pytest_ignores(pyproject: dict[str, Any]) -> list[str]:
    options = (
        pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})
        if isinstance(pyproject, dict)
        else {}
    )
    addopts = options.get("addopts", "")
    if isinstance(addopts, list):
        tokens = [str(item) for item in addopts]
    else:
        tokens = str(addopts).split()
    ignores: list[str] = []
    for index, token in enumerate(tokens):
        if token.startswith("--ignore="):
            ignores.append(token.split("=", 1)[1])
        elif token == "--ignore" and index + 1 < len(tokens):
            ignores.append(tokens[index + 1])
    return sorted(set(ignores))


def test_files_under(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        name = path.name
        return [path] if name.startswith("test_") or ".test." in name or ".spec." in name else []
    matches: list[Path] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        name = item.name
        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or ".test." in name
            or ".spec." in name
        ):
            matches.append(item)
    return matches


def line_evidence(root: Path, path: Path, line_number: int, text: str) -> dict[str, Any]:
    return {"path": relative(root, path), "line": line_number, "text": text.strip()[:500]}


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = sorted(iter_files(root))
    rel_files = [relative(root, path) for path in files]
    language_counts: Counter[str] = Counter()
    for path in files:
        language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower())
        if language:
            language_counts[language] += 1

    manifests = sorted(path for path in rel_files if Path(path).name in MANIFEST_NAMES)
    locks = sorted(path for path in rel_files if Path(path).name in LOCK_NAMES)
    configs = sorted(path for path in rel_files if Path(path).name in CONFIG_NAMES)
    ci_files = sorted(
        path
        for path in rel_files
        if path.startswith(".github/workflows/")
        or path in {".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"}
    )
    test_files = sorted(
        path
        for path in rel_files
        if Path(path).name.startswith("test_")
        or Path(path).name.endswith("_test.py")
        or ".test." in Path(path).name
        or ".spec." in Path(path).name
    )
    executable_candidates = sorted(
        path
        for path in rel_files
        if path.startswith(("scripts/", "ops/scripts/", "bin/"))
        and Path(path).suffix.lower() in {".py", ".sh", ".bash", ".zsh", ".js", ".ts"}
    )

    pyproject = parse_pyproject(root / "pyproject.toml")
    python_declared = parse_python_declared(root, pyproject)
    node_declared = parse_node_declared(root)
    # Analyze imports only over active source: archived / example / vendored trees
    # are excluded so their imports never register as undeclared runtime dependencies.
    source_files = [path for path in files if not is_archived_rel(relative(root, path))]
    import_roots, syntax_errors = python_imports(root, source_files)
    local_roots = repo_python_modules(root, source_files)
    third_party_imports = sorted(
        root_name
        for root_name in import_roots
        if root_name not in PY_STDLIB
        and root_name not in local_roots
        and root_name not in {"__future__"}
    )

    findings: list[dict[str, Any]] = []
    for error in syntax_errors:
        findings.append(
            finding(
                "syntax_or_parse_failure",
                "high",
                f"Python source does not parse: {error['path']}",
                "The file cannot be reliably imported, tested, or analyzed.",
                "Repair the syntax or remove the file from the active source boundary with explicit evidence.",
                [error],
            )
        )

    pytest_ignores = extract_pytest_ignores(pyproject)
    wiring_text = "\n".join(
        filter(
            None,
            [
                read_text(root / "Makefile") or "",
                *(read_text(root / path) or "" for path in ci_files),
                *(read_text(root / path) or "" for path in executable_candidates),
            ],
        )
    )
    for ignored in pytest_ignores:
        ignored_path = (root / ignored).resolve()
        try:
            ignored_path.relative_to(root)
        except ValueError:
            continue
        # Keep only files that are structurally test content — a name-matched module
        # with no test functions or framework import (e.g. a DAG named test_*.py) is
        # not a hidden suite and must not be flagged.
        tests = [
            candidate for candidate in test_files_under(ignored_path) if is_test_content(candidate)
        ]
        if tests and ignored not in wiring_text:
            findings.append(
                finding(
                    "test_topology_gap",
                    "high",
                    f"Ignored active test content has no proven canonical runner: {ignored}",
                    "The repository can report green while this suite never executes.",
                    "Register the suite in one repository-owned runner or prove and document that it is not active test content.",
                    [
                        {"path": "pyproject.toml", "text": f"--ignore={ignored}"},
                        {
                            "path": relative(root, tests[0]),
                            "text": "test content under ignored path",
                        },
                    ],
                )
            )

    ad_hoc_patterns = [
        re.compile(r"\bpip(?:3)?\s+install\b"),
        re.compile(r"\buv\s+pip\s+install\b"),
        re.compile(r"\bnpm\s+install\s+-g\b"),
        re.compile(r"\bpnpm\s+add\s+-g\b"),
        re.compile(r"\bcargo\s+install\b"),
    ]
    pip_family = re.compile(r"\b(?:pip(?:3)?|uv\s+pip)\s+install\b")
    # Bootstrapping the installer/toolchain itself is not "installing dependencies
    # outside the lock": these package names ARE the bootstrap layer, not project
    # dependencies. A floating install of any other package still drifts, and a
    # locked sync (uv sync --locked / pip -r <lock> / npm ci) then owns the real deps.
    bootstrap_targets = {"pip", "setuptools", "wheel", "uv"}

    def strip_inline_comment(raw: str) -> str:
        # Drop a shell/YAML comment beginning at an unquoted '#' so that "pip install"
        # appearing in explanatory prose is never matched as an executable install.
        in_single = in_double = False
        for index, char in enumerate(raw):
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            elif char == "#" and not in_single and not in_double:
                if index == 0 or raw[index - 1].isspace():
                    return raw[:index]
        return raw

    def install_targets(command: str) -> list[str]:
        # Package names requested by a pip / uv pip install, with flags and version
        # or extras specifiers stripped ("ruff==0.16.0" -> "ruff").
        match = pip_family.search(command)
        if not match:
            return []
        names: list[str] = []
        for token in command[match.end() :].split():
            if token.startswith("-"):
                continue
            name = re.split(r"[<>=!~\[]", token, maxsplit=1)[0].strip().lower()
            if name:
                names.append(name)
        return names

    for ci_path in ci_files:
        path = root / ci_path
        text = read_text(path) or ""
        for line_number, line in enumerate(text.splitlines(), start=1):
            code = strip_inline_comment(line)
            if not any(pattern.search(code) for pattern in ad_hoc_patterns):
                continue
            # Exempt a pure installer/toolchain bootstrap (pip/setuptools/wheel/uv);
            # real project dependencies never fall entirely within that set.
            if pip_family.search(code):
                targets = install_targets(code)
                if targets and set(targets) <= bootstrap_targets:
                    continue
            lock_based = any(
                token in code
                for token in (
                    "-r requirements",
                    "-e .",
                    "npm ci",
                    "--frozen-lockfile",
                )
            )
            severity = "medium" if lock_based else "high"
            findings.append(
                finding(
                    "dependency_authority_drift",
                    severity,
                    f"CI installs dependencies outside an explicit locked synchronization path in {ci_path}",
                    "CI can resolve a different toolchain from local development and the committed lock state.",
                    "Declare required tools in the canonical manifest and make CI use the repository's locked bootstrap.",
                    [line_evidence(root, path, line_number, line)],
                )
            )

    tool_uv = pyproject.get("tool", {}).get("uv", {}) if isinstance(pyproject, dict) else {}
    if tool_uv.get("package") is False and pyproject.get("build-system"):
        findings.append(
            finding(
                "package_boundary_ambiguity",
                "medium",
                "pyproject declares a non-package uv project and a build backend",
                "Maintainers and automation can disagree about whether the repository should be installed as a package.",
                "Prove the actual bootstrap and consumer contract, then retain or remove build metadata as one recorded authority decision.",
                [
                    {"path": "pyproject.toml", "text": "[tool.uv] package = false"},
                    {"path": "pyproject.toml", "text": "[build-system] present"},
                ],
                confidence="medium",
            )
        )

    makefile_text = read_text(root / "Makefile") or ""
    canonical_runner_names = re.findall(
        r"(?:bash|python\S*)\s+([^\s]*run[^\s]*(?:test|suite)[^\s]*)", makefile_text, re.I
    )
    for ci_path in ci_files:
        ci_text = read_text(root / ci_path) or ""
        duplicates_pytest = "pytest" in makefile_text and "pytest" in ci_text
        delegates = any(Path(name).name in ci_text for name in canonical_runner_names)
        if duplicates_pytest and canonical_runner_names and not delegates:
            findings.append(
                finding(
                    "local_ci_divergence",
                    "high",
                    f"CI duplicates test orchestration instead of invoking the repository runner in {ci_path}",
                    "Suite registration and execution semantics can drift between local and CI paths.",
                    "Make CI install through the locked bootstrap and invoke the repository-owned canonical runner.",
                    [
                        {"path": "Makefile", "text": canonical_runner_names[0]},
                        {"path": ci_path, "text": "independent pytest orchestration"},
                    ],
                    confidence="medium",
                )
            )

    declared_flat = {item for values in python_declared.values() for item in values}
    missing_imports: list[str] = []
    for import_root in third_party_imports:
        distribution = normalize_distribution(IMPORT_DIST_OVERRIDES.get(import_root, import_root))
        if distribution not in declared_flat:
            missing_imports.append(import_root)
    if missing_imports:
        findings.append(
            finding(
                "dependency_authority_drift",
                "medium",
                "Python imports are not represented in discovered dependency declarations",
                "Fresh environments may fail or rely on undeclared transitive dependencies.",
                "Map each import root to its distribution and declare it in the correct runtime or development group, or prove it is optional/dynamic.",
                [{"path": "repository", "text": ", ".join(missing_imports[:30])}],
                confidence="medium",
            )
        )

    markers: list[dict[str, Any]] = []
    conflict_kinds: dict[str, set[str]] = defaultdict(set)
    conflict_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    path_references: list[dict[str, Any]] = []
    relative_path_pattern = re.compile(
        r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+)(?![\w./-])"
    )
    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in CONFIG_NAMES:
            continue
        text = read_text(path)
        if text is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line):
                if len(markers) < 100:
                    markers.append(line_evidence(root, path, line_number, line))
            marker_kind = conflict_marker_kind(line)
            if marker_kind is not None:
                rel = relative(root, path)
                conflict_kinds[rel].add(marker_kind)
                if len(conflict_evidence[rel]) < 10:
                    conflict_evidence[rel].append(line_evidence(root, path, line_number, line))
            if path.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".toml"}:
                for match in relative_path_pattern.finditer(line):
                    candidate = match.group(1)
                    if candidate.startswith(("http/", "https/")):
                        continue
                    if any(token in candidate for token in ("${", "{{", "<", ">")):
                        continue
                    resolved = root / candidate
                    if not resolved.exists() and not candidate.startswith(
                        ("examples/", "example/")
                    ):
                        if len(path_references) < 100:
                            path_references.append(
                                {
                                    "source": relative(root, path),
                                    "line": line_number,
                                    "target": candidate,
                                }
                            )

    # A real conflict hunk carries an opening `<<<<<<<` and a closing `>>>>>>>`
    # marker (the separator alone is ambiguous). Require both before reporting.
    conflicts: list[dict[str, Any]] = []
    for rel, kinds in conflict_kinds.items():
        if "open" in kinds and "close" in kinds:
            conflicts.extend(conflict_evidence[rel])
    if conflicts:
        findings.append(
            finding(
                "repository_integrity_failure",
                "critical",
                "Unresolved merge-conflict markers exist in active text files",
                "Source, configuration, or documentation may be corrupt and automation can behave unpredictably.",
                "Resolve every conflict marker and add a repository-wide tripwire.",
                conflicts[:20],
            )
        )
    if path_references:
        findings.append(
            finding(
                "documentation_code_drift",
                "low",
                "Configuration or documentation contains repository-relative paths that do not exist",
                "Operators may follow stale wiring or automation may reference deleted files.",
                "Verify each reference, repair active paths, and classify historical examples explicitly.",
                path_references[:20],
                confidence="low",
            )
        )

    git_head = run(["git", "rev-parse", "HEAD"], cwd=root, timeout=10)
    git_branch = run(["git", "branch", "--show-current"], cwd=root, timeout=10)
    git_status = run(["git", "status", "--porcelain=v1"], cwd=root, timeout=10)
    repository = {
        "root": str(root),
        "git_head": git_head["output"].strip() if git_head["exit_code"] == 0 else None,
        "git_branch": git_branch["output"].strip() if git_branch["exit_code"] == 0 else None,
        "dirty": bool(git_status["output"].strip()) if git_status["exit_code"] == 0 else None,
    }
    audit_id = stable_id(
        repository.get("git_head") or str(root), "\n".join(rel_files), prefix="AUDIT"
    )
    findings.sort(
        key=lambda item: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}[item["severity"]],
            item["id"],
        )
    )
    return {
        "schema_version": "repository-audit-1.0",
        "audit_id": audit_id,
        "generated_at": utc_now(),
        "repository": repository,
        "inventory": {
            "file_count": len(files),
            "languages": dict(sorted(language_counts.items())),
            "manifests": manifests,
            "lockfiles": locks,
            "configuration": configs,
            "ci": ci_files,
            "tests": test_files,
            "executable_candidates": executable_candidates,
            "python": {
                "declared_dependencies": python_declared,
                "import_roots": import_roots,
                "third_party_import_roots": third_party_imports,
                "pytest_ignores": pytest_ignores,
            },
            "node": node_declared,
            "maintenance_markers": markers,
        },
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "by_severity": dict(Counter(item["severity"] for item in findings)),
            "by_class": dict(Counter(item["class"] for item in findings)),
        },
        "limitations": [
            "Static discovery cannot prove dynamic reachability, external consumers, or organizational intent.",
            "Import-root to distribution mapping is heuristic and requires repository verification.",
            "Missing path references may include illustrative documentation and require manual classification.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a repository control plane and emit evidence-backed findings."
    )
    parser.add_argument("repo", type=Path)
    parser.add_argument("--output", type=Path, default=Path("repository-audit.json"))
    args = parser.parse_args()
    if not args.repo.exists() or not args.repo.is_dir():
        parser.error(f"repository directory does not exist: {args.repo}")
    payload = audit(args.repo)
    write_json(args.output, payload)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
