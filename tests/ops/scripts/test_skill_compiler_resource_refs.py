"""validate_skill_pack.py fails a SKILL.md that names a pack file the pack lacks.

The validator used to check only markdown `[text](link)` links. The compiler's
own resource map lists files as backticked paths, so five policy files deleted
in #341 stayed listed and the pack still validated PASS.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "skills" / "l9-skill-compiler"
SCRIPT = PACK / "scripts" / "validate_skill_pack.py"

GOOD_DESC = (
    "compile, rebuild, and validate reusable agent skill packs from prompts, SOPs, "
    "and existing skills. use when creating a reusable skill, making one portable "
    "across agents, or producing a validated archive for install."
)


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_skill_pack_refs", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _pack(tmp_path: Path, body: str, files: tuple[str, ...] = ()) -> Path:
    root = tmp_path / "l9-demo"
    root.mkdir()
    (root / "SKILL.md").write_text(
        f"---\nname: l9-demo\ndescription: {GOOD_DESC}\n---\n\n# Demo\n\n{body}\n",
        encoding="utf-8",
    )
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n", encoding="utf-8")
    return root


def _missing(errors: list[str]) -> list[str]:
    prefix = "SKILL.md references a pack file that does not exist: "
    return [e.removeprefix(prefix) for e in errors if e.startswith(prefix)]


def test_missing_backticked_resource_fails(tmp_path: Path) -> None:
    root = _pack(
        tmp_path,
        "- `references/present.md`\n- `policies/gone.yaml`\n- `scripts/run.py <arg>`",
        files=("references/present.md",),
    )
    assert _missing(validator.validate(root)) == ["policies/gone.yaml", "scripts/run.py"]


def test_root_release_file_reference_is_checked(tmp_path: Path) -> None:
    root = _pack(tmp_path, "See `VALIDATION.md` and `README.md`.", files=("README.md",))
    assert _missing(validator.validate(root)) == ["VALIDATION.md"]


def test_present_resources_pass(tmp_path: Path) -> None:
    root = _pack(
        tmp_path,
        "- `references/a.md`\n- `scripts/b.py` (helpers: `scripts/c.py`)",
        files=("references/a.md", "scripts/b.py", "scripts/c.py"),
    )
    assert validator.validate(root) == []


def test_non_resource_tokens_are_not_paths(tmp_path: Path) -> None:
    body = "\n".join(
        [
            "Keys: `name`, `metadata:`, `disable-model-invocation: true`.",
            "Globs and templates: `scripts/validate_*.py`, `references/<topic>.md`.",
            "Directories as conventions: `references/`, `adapters/`.",
            "Host repo paths: `ops/scripts/x.py`, `AGENTS.md`, `../other/SKILL.md`.",
            "URL: `https://example.com/scripts/a.py`.",
            "Archive name: `skill.zip`.",
        ]
    )
    assert validator.validate(_pack(tmp_path, body)) == []


def test_fenced_code_and_prohibitions_are_exempt(tmp_path: Path) -> None:
    body = "\n".join(
        [
            "```bash",
            "python `scripts/not_shipped.py`",
            "```",
            "- Do not include `agents/openai.yaml` unless ChatGPT packaging is requested.",
        ]
    )
    assert validator.validate(_pack(tmp_path, body)) == []


def test_path_into_the_host_repository_is_not_a_missing_pack_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "shared.py").write_text("x\n", encoding="utf-8")
    skills = repo / "skills"
    skills.mkdir()
    root = _pack(skills, "Run `scripts/shared.py` then `scripts/absent.py`.")
    assert _missing(validator.validate(root)) == ["scripts/absent.py"]


def test_the_compiler_pack_lists_only_files_it_ships() -> None:
    assert _missing(validator.validate(PACK)) == []


def test_main_branch_dangling_policies_would_have_failed(tmp_path: Path) -> None:
    """The exact v3.8.0 resource map line that validated PASS before this check."""
    body = (
        "Policies: `policies/skill-families.yaml`, `policies/runtime-routing.yaml`,\n"
        "`policies/capability-closure.yaml`, `policies/target-profiles.yaml`,\n"
        "`policies/behavior-evals.yaml`, `policies/topology-ownership.yaml`"
    )
    root = _pack(tmp_path, body, files=("policies/topology-ownership.yaml",))
    assert _missing(validator.validate(root)) == [
        "policies/skill-families.yaml",
        "policies/runtime-routing.yaml",
        "policies/capability-closure.yaml",
        "policies/target-profiles.yaml",
        "policies/behavior-evals.yaml",
    ]


def test_cli_reports_the_missing_file(tmp_path: Path) -> None:
    root = _pack(tmp_path, "- `references/gone.md`")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 1
    assert "references a pack file that does not exist: references/gone.md" in proc.stderr
