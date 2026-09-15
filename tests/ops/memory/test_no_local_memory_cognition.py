"""INV-03b, cognition half: Cursor-Governance holds no memory cognition of
its own (ADR-0033 B5).

"Cognition" is anything that decides what memory *is* before ``MemoryService``
sees it: a provider / LLM client, a model id, a promotion rule, a local
distill knob, an S3 distill queue, or the deleted ``graphiti_memory_client``.
Cursor-Governance may gather, redact and latch session material; it may
build ``ContinuationCapsuleV2``; it may hand a redacted excerpt to
``l9-memory distill``. It may not extract, score or promote.

Two proofs:

* the real tree — an AST walk over every production module on a memory path
  for provider imports, plus the residue validator's ``local-memory-cognition``
  class over the same paths;
* synthetic trees — each finding class fires on a minimal offender and stays
  quiet on the allowed shapes, so the ratchet is known to bite.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "ops" / "scripts" / "validate_legacy_doctrine_residue.py"

PROVIDER_MODULES = frozenset(
    {
        "openai",
        "anthropic",
        "litellm",
        "cohere",
        "mistralai",
        "together",
        "groq",
        "vertexai",
        "boto3",
        "botocore",
    }
)
PROVIDER_PREFIXES = ("langchain", "google.generativeai")

#: Adjacent S3 chat archive — explicitly not memory (ADR-0033 "Consequences").
ALLOWED_S3 = {"ops/graphiti/hydration/archive_transcript.py"}


def _load():
    spec = importlib.util.spec_from_file_location("residue", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def residue():
    return _load()


def _memory_modules(residue) -> list[Path]:
    return [p for p in residue._memory_code_paths(ROOT) if p.suffix == ".py"]


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _is_provider(name: str) -> bool:
    head = name.split(".")[0]
    return head in PROVIDER_MODULES or name.startswith(PROVIDER_PREFIXES)


# --------------------------------------------------------------------------- #
# The real tree
# --------------------------------------------------------------------------- #


def test_no_production_memory_module_imports_a_provider_client(residue) -> None:
    offenders: list[str] = []
    for path in _memory_modules(residue):
        rel = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for name in sorted(_imports(tree)):
            if not _is_provider(name):
                continue
            if name.split(".")[0] in {"boto3", "botocore"} and rel in ALLOWED_S3:
                continue
            offenders.append(f"{rel}: import {name}")
    assert offenders == [], "\n".join(offenders)


def test_the_real_tree_holds_no_local_memory_cognition(residue) -> None:
    assert residue.local_cognition_findings(ROOT) == []


def test_the_deleted_cognition_modules_stay_deleted() -> None:
    for rel in (
        "ops/graphiti/hydration/openai_fixed_host.py",
        "ops/graphiti/hydration/openai_key.py",
        "ops/graphiti/hydration/promotion_rules.yaml",
        "ops/graphiti/hydration/resume_signal_scorer.py",
        "ops/graphiti/distill_queue",
        "ops/scripts/run_distiller.sh",
        ".github/workflows/memory-distill.yml",
        "ops/graphiti/graphiti_memory_client.py",
    ):
        assert not (ROOT / rel).exists(), f"{rel} is back"


def test_close_session_has_no_local_cognition_surface() -> None:
    text = (ROOT / "ops/graphiti/hydration/close_session.py").read_text(encoding="utf-8")
    for symbol in ("_distill_signal_packet", "_promote", "PHASE_B_BUDGET", "MEMORY_PHASE_B"):
        assert symbol not in text, symbol
    assert "client.distill(" in text, "the bounded canonical distill is the only distill"


def test_the_ratchet_runs_on_the_publish_path() -> None:
    """``validate_legacy_doctrine_residue`` is a pre-commit hook and a make pr step."""
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "validate_legacy_doctrine_residue" in precommit


# --------------------------------------------------------------------------- #
# Synthetic trees: every class fires, allowed shapes do not
# --------------------------------------------------------------------------- #


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


@pytest.mark.parametrize(
    ("rel", "body", "finding"),
    [
        ("ops/graphiti/hydration/x.py", "import openai\n", "provider-client-import"),
        ("ops/hooks/x.py", "from anthropic import Anthropic\n", "provider-client-import"),
        ("ops/memory/x.py", 'MODEL = "gpt-4o-mini"\n', "provider-model-id"),
        (
            "environment/agents/adapters/claude-code/hooks/x.py",
            'EMBED = "text-embedding-3-small"\n',
            "provider-model-id",
        ),
        ("ops/graphiti/hydration/x.py", "load('promotion_rules.yaml')\n", "promotion-rules"),
        ("ops/graphiti/hydration/x.py", "if os.environ.get('MEMORY_PHASE_B'):\n", "phase-b-knob"),
        (
            "ops/graphiti/hydration/x.py",
            "os.environ.get('MEMORY_DISTILL_S3_BUCKET')\n",
            "local-distill-knob",
        ),
        ("ops/graphiti/hydration/x.py", "os.environ.get('MEMORY_DISTILL')\n", "local-distill-knob"),
        ("ops/graphiti/hydration/x.py", "import boto3\n", "s3-on-memory-path"),
        ("ops/hooks/x.sh", "aws s3api put-object --bucket b\n", "s3-on-memory-path"),
        ("ops/hooks/x.py", "from ops.graphiti import graphiti_memory_client\n", "retired-client"),
    ],
)
def test_each_cognition_class_fires(tmp_path: Path, rel: str, body: str, finding: str) -> None:
    _write(tmp_path, rel, body)
    rc, out = _run(tmp_path)
    assert rc == 1, out
    assert f"[local-memory-cognition/{finding}]" in out, out


@pytest.mark.parametrize(
    ("rel", "body"),
    [
        # The canonical kill switch is not the retired local knob.
        ("ops/graphiti/hydration/x.py", "os.environ.get('L9_MEMORY_DISTILL', '1')\n"),
        # A retirement notice may name what is gone.
        ("ops/memory/x.py", "# graphiti_memory_client.py was retired at C11 and deleted at C15\n"),
        # The adjacent chat archive keeps its S3 client.
        ("ops/graphiti/hydration/archive_transcript.py", "import boto3\n"),
        # Outside the memory paths the class does not apply.
        ("ops/scripts/x.py", "import openai\n"),
        # Tests are not production.
        ("ops/memory/tests/test_x.py", "import openai\n"),
        # claude-code is a surface id, not a model id.
        ("ops/hooks/x.py", "SURFACE = 'claude-code'\n"),
    ],
)
def test_allowed_shapes_do_not_fire(tmp_path: Path, rel: str, body: str) -> None:
    _write(tmp_path, rel, body)
    rc, out = _run(tmp_path)
    assert "[local-memory-cognition/" not in out, out
    assert rc == 0, out
