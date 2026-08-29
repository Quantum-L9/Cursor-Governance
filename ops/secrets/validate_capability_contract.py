#!/usr/bin/env python3
"""Governance validator for the zero-static-secret contract (contract §23).

This is the regression barrier. The architecture in ``ops/secrets`` removes raw
secrets from model-controlled surfaces today; this validator is what stops a
future agent — or a future human in a hurry — from putting them back to make a
check go green.

It fails the build when:

1. An LLM adapter environment example assigns a prohibited credential
   (``GRAPHITI_MCP_TOKEN=REPLACE_...``, ``INFISICAL_CLIENT_SECRET=...``,
   ``SONAR_TOKEN=...``, an AWS key, a real ``GH_TOKEN``, ...). The literal
   ``proxy-injected`` is allowed for GitHub because it is not a credential.

2. LLM-facing code reaches for raw secret material — ``--export <secret>``,
   ``resolve_secret(...)``, a direct Infisical secret read, or an AWS secret
   bootstrap — without being explicitly marked trusted-operator-only.

The escape hatch is deliberate and narrow: a file may carry the marker

    L9-TRUSTED-OPERATOR-ONLY

which declares that its raw-secret paths are for humans/brokers and are guarded
by ``surface_trust.require_trusted``. The marker is a *declaration*, not a
bypass — the guard still runs at execution time. It exists so the validator can
tell "this is the operator CLI" apart from "an adapter grew a secret read", and
it makes such a file's status visible in review.

Usage:
  validate_capability_contract.py            # scan the repository
  validate_capability_contract.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

TRUSTED_MARKER = "L9-TRUSTED-OPERATOR-ONLY"

#: Credential names that must never be assigned in an agent surface environment.
#: GH_TOKEN is handled separately because one literal value is permitted.
PROHIBITED_ENV_ASSIGNMENTS = (
    "GITHUB_TOKEN",
    "GRAPHITI_MCP_TOKEN",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_TOKEN",
    "SONAR_TOKEN",
    "SONARCLOUD_TOKEN",
    "SEMGREP_APP_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)

#: The only GH_TOKEN value an adapter example may carry (contract S7).
ALLOWED_GH_TOKEN_VALUES = frozenset({"proxy-injected", ""})

#: Raw-secret code patterns that require the trusted-operator marker.
CODE_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "raw-export",
        re.compile(r"--export\s+[A-Z][A-Z0-9_]{3,}"),
        "requests a raw secret export by name",
    ),
    (
        "resolve-secret",
        re.compile(r"\bresolve_secret\s*\("),
        "calls the raw AWS secret resolver",
    ),
    (
        "infisical-raw-read",
        re.compile(r"viewSecretValue\s*[=:]\s*[\"']?true"),
        "reads Infisical secret values directly",
    ),
    (
        "aws-secret-bootstrap",
        re.compile(r"secretsmanager\s+get-secret-value|_aws_bootstrap\s*\("),
        "bootstraps credentials from AWS Secrets Manager",
    ),
    (
        "infisical-client-secret-read",
        re.compile(r"(getenv|environ(\.get)?)\s*[\(\[]\s*[\"']INFISICAL_CLIENT_SECRET"),
        "reads the Infisical Universal Auth client secret",
    ),
)

#: Directories whose code is model-facing by definition.
LLM_CODE_ROOTS = (
    "environment/agents/adapters",
    "skills",
    "ops/scripts",
    "ops/graphiti",
    "ops/secrets",
)

SKIP_PARTS = frozenset({".git", "node_modules", ".venv", "_archived", "WIP", "generated"})


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    rule: str
    detail: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.detail}"


def _skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def scan_env_examples(repo: Path) -> list[Violation]:
    """Rule 1 — no credential assignments in any adapter environment example."""
    violations: list[Violation] = []
    adapters = repo / "environment" / "agents" / "adapters"
    for path in sorted(adapters.rglob("*environment.env.example")):
        if _skip(path.relative_to(repo)):
            continue
        rel = str(path.relative_to(repo))
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip()
            if name == "GH_TOKEN" and value not in ALLOWED_GH_TOKEN_VALUES:
                violations.append(
                    Violation(
                        rel,
                        number,
                        "prohibited-credential",
                        "GH_TOKEN must be unset or the literal 'proxy-injected'; a real PAT "
                        "must not live in a model-controlled environment (S7)",
                    )
                )
            elif name in PROHIBITED_ENV_ASSIGNMENTS:
                violations.append(
                    Violation(
                        rel,
                        number,
                        "prohibited-credential",
                        f"{name} must not be assigned in an agent surface environment (S1/S2/S3); "
                        "register a capability in ops/secrets/capabilities.yaml instead",
                    )
                )
    return violations


def scan_code(repo: Path) -> list[Violation]:
    """Rule 2 — no raw-secret paths in LLM-facing code without the marker."""
    violations: list[Violation] = []
    for root in LLM_CODE_ROOTS:
        base = repo / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or path.suffix not in (".py", ".sh", ".md", ".json", ".yaml"):
                continue
            rel_path = path.relative_to(repo)
            if _skip(rel_path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if TRUSTED_MARKER in text:
                continue
            rel = str(rel_path)
            for number, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                # Documentation of the prohibition is not a violation of it.
                if stripped.startswith(("#", "//", "*", ">")) or "DENIED" in line:
                    continue
                for rule, pattern, detail in CODE_PATTERNS:
                    if pattern.search(line):
                        violations.append(
                            Violation(
                                rel,
                                number,
                                rule,
                                f"{detail}; mark the file {TRUSTED_MARKER} if it is genuinely "
                                "operator-only, otherwise route through the capability plane",
                            )
                        )
    return violations


_AWS_FALLBACK_RE = re.compile(
    r"falls back to AWS|fallback to AWS|falls back to\s+openclaw-igorbot", re.I
)


def scan_aws_fallback_docs(repo: Path) -> list[Violation]:
    """Adapter env examples must not teach an AWS secret fallback (contract S1)."""
    violations: list[Violation] = []
    adapters = repo / "environment" / "agents" / "adapters"
    if not adapters.is_dir():
        return violations
    for path in sorted(adapters.rglob("*environment.env.example")):
        if _skip(path.relative_to(repo)):
            continue
        rel = str(path.relative_to(repo))
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _AWS_FALLBACK_RE.search(raw):
                violations.append(
                    Violation(
                        rel,
                        number,
                        "aws-fallback-doc",
                        "adapter env example must not teach an AWS secret fallback; "
                        "model surfaces never receive raw secrets; the capability-broker experiment is retired",
                    )
                )
    return violations


def scan_inventory_refs(repo: Path) -> list[Violation]:
    """Every capabilities.yaml secret_ref must be listed in Infisical root_env_keys."""
    violations: list[Violation] = []
    caps = repo / "ops" / "secrets" / "capabilities.yaml"
    inventory = repo / "ops" / "secrets" / "infisical-cursor-governance.yaml"
    if not caps.is_file() or not inventory.is_file():
        return violations
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return violations
    caps_raw = yaml.safe_load(caps.read_text(encoding="utf-8")) or {}
    inv_raw = yaml.safe_load(inventory.read_text(encoding="utf-8")) or {}
    keys = set(inv_raw.get("root_env_keys") or [])
    for entry in caps_raw.get("capabilities") or []:
        cap_id = str((entry or {}).get("id") or "")
        for ref in entry.get("secret_refs") or []:
            if ref not in keys:
                violations.append(
                    Violation(
                        "ops/secrets/capabilities.yaml",
                        1,
                        "inventory-lag",
                        f"{cap_id} secret_ref {ref} is missing from "
                        "infisical-cursor-governance.yaml root_env_keys",
                    )
                )
    return violations


def validate(repo: Path | None = None) -> list[Violation]:
    target = repo or REPO
    return (
        scan_env_examples(target)
        + scan_code(target)
        + scan_aws_fallback_docs(target)
        + scan_inventory_refs(target)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the zero-static-secret contract.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args(argv)

    violations = validate(args.repo)
    if args.json:
        print(json.dumps([v.__dict__ for v in violations], indent=2))
    elif violations:
        print(f"capability contract: {len(violations)} VIOLATION(S)", file=sys.stderr)
        for violation in violations:
            print(f"  {violation.render()}", file=sys.stderr)
    else:
        print("capability contract: OK — no raw-secret paths on model-controlled surfaces")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
