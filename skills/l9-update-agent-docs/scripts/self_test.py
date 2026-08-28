#!/usr/bin/env python3
"""Prove l9-update-agent-docs cites both kernels and does not wrap them."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

PACK = Path(__file__).resolve().parents[1]
SKILL = PACK / "SKILL.md"
MAP = PACK / "references" / "pointer-heading-map.yaml"
VALIDATOR = PACK / "scripts" / "validate_pointer_headings.py"
# Split so a pack-wide grep for the wrap tokens stays empty (SP-02).
FORBIDDEN = (
    "Ker" + "nel bind",
    "artifact" + "_type:",
    "ai_coding" + "_alignment_kernel",
    "ai_coding" + "_execution_kernel",
)
DONOR_SECTIONS = ("overview", "airules", "apisurface", "datamodels", "components")


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    errors: list[str] = []
    repo = PACK.parents[1]
    for token in FORBIDDEN:
        if token in text:
            errors.append(f"forbidden kernel wrap token: {token}")
    if "kernels/Recursive Alignment.md" not in text:
        errors.append("missing path citation to kernels/Recursive Alignment.md")
    if "kernels/Validate & Repair.md" not in text:
        errors.append("missing path citation to kernels/Validate & Repair.md")
    for token in ("Passed", "Failed", "Skipped", "Unknown", "NotApplicable"):
        if token not in text:
            errors.append(f"missing honest-validation status: {token}")
    if "authority pointer" not in text.lower() and "load pointer" not in text.lower():
        errors.append("CLAUDE.md pointer role not stated")
    if "c-required-section-validation" not in text:
        errors.append("missing harvest nugget c-required-section-validation")
    if "c-bind-before-write" not in text:
        errors.append("missing harvest nugget c-bind-before-write")
    if "references/pointer-heading-map.yaml" not in text:
        errors.append("missing pointer-heading-map citation")
    if "validate_pointer_headings.py" not in text:
        errors.append("missing validate_pointer_headings.py citation")
    if "scripts/generate_subsystem_readmes.py" not in text:
        errors.append("missing generate_subsystem_readmes.py citation")
    if "readme-pipeline-v1" not in text:
        errors.append("missing readme-pipeline-v1 citation")
    if "config/subsystems/readme_config.yaml" not in text:
        errors.append("missing readme_config.yaml citation")
    if "SessionRunner.run" in text:
        errors.append("SessionRunner.run is not a live API; cite get_session_dag")
    if "get_session_dag" not in text:
        errors.append("missing get_session_dag citation")
    if "--gaps" not in text:
        errors.append("missing --gaps citation")
    if "Never invent a root file" not in text and "never invent" not in text.lower():
        errors.append("missing bind-before-write never-invent rule")
    # Prohibition mentions are allowed; a Write-table destination is not.
    write_section = ""
    if "### Step 3 — Write" in text:
        write_section = text.split("### Step 3 — Write", 1)[1]
        if "### Step 4" in write_section:
            write_section = write_section.split("### Step 4", 1)[0]
    for invented in ("ARCHITECTURE.md", "INVARIANTS.md"):
        for line in write_section.splitlines():
            if line.startswith("|") and f"`{invented}`" in line:
                errors.append(f"invented write target: {invented}")
    if not MAP.is_file():
        errors.append("missing references/pointer-heading-map.yaml")
    else:
        mapping = yaml.safe_load(MAP.read_text(encoding="utf-8"))
        required = set()
        for spec in (mapping.get("files") or {}).values():
            required.update(h.lower() for h in (spec.get("required_headings") or []))
        leaked = [name for name in DONOR_SECTIONS if name in required]
        if leaked:
            errors.append(f"donor sections required in heading map: {leaked}")
        forbidden = {n.lower() for n in mapping.get("forbidden_donor_sections") or []}
        if not set(DONOR_SECTIONS).issubset(forbidden):
            errors.append("heading map must forbid donor section names")
    if not VALIDATOR.is_file():
        errors.append("missing scripts/validate_pointer_headings.py")
    else:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(repo)],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append(f"validate_pointer_headings failed:\n{proc.stdout}{proc.stderr}")
        missing = subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(PACK / "scripts")],
            check=False,
            capture_output=True,
            text=True,
        )
        if missing.returncode != 0:
            errors.append("missing mapped files must be Unknown, not FAIL")
        elif "Unknown" not in missing.stdout:
            errors.append("missing mapped files did not report Unknown")
        dishonest = Path(PACK / "scripts" / "_heading_fixture")
        try:
            dishonest.mkdir(exist_ok=True)
            (dishonest / "README.md").write_text(
                "# Index\n\nNo required pointers.\n", encoding="utf-8"
            )
            (dishonest / "CLAUDE.md").write_text("# note\n", encoding="utf-8")
            (dishonest / "AGENTS.md").write_text("# ops\n", encoding="utf-8")
            bad = subprocess.run(
                [sys.executable, str(VALIDATOR), "--root", str(dishonest)],
                check=False,
                capture_output=True,
                text=True,
            )
            if bad.returncode == 0:
                errors.append("dishonest README headings must FAIL")
        finally:
            for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
                path = dishonest / name
                if path.exists():
                    path.unlink()
            if dishonest.exists():
                dishonest.rmdir()
    generator = repo / "scripts" / "generate_subsystem_readmes.py"
    config = repo / "config" / "subsystems" / "readme_config.yaml"
    dag = repo / "workflows" / "dags" / "readme_pipeline_dag.py"
    if not generator.is_file():
        errors.append("missing scripts/generate_subsystem_readmes.py")
    if not config.is_file():
        errors.append("missing config/subsystems/readme_config.yaml")
    if not dag.is_file():
        errors.append("missing workflows/dags/readme_pipeline_dag.py")
    else:
        dag_text = dag.read_text(encoding="utf-8")
        if "scripts/generate_subsystem_readmes.py" not in dag_text:
            errors.append("DAG no longer names generate_subsystem_readmes.py")
        if "memory/README.md" in dag_text:
            errors.append("DAG still spots donor memory/README.md")
        if "66+" in dag_text:
            errors.append("DAG still claims donor 66+ README outputs")
        if "DORA header" in dag_text:
            errors.append("DAG still requires DORA headers")
        if "--gaps" not in dag_text:
            errors.append("DAG gap_analysis does not call --gaps")
    if generator.is_file() and config.is_file():
        listed = subprocess.run(
            [sys.executable, str(generator), "--root", str(repo), "--list"],
            check=False,
            capture_output=True,
            text=True,
        )
        if listed.returncode != 0:
            errors.append(f"generator --list failed:\n{listed.stdout}{listed.stderr}")
        elif "ops_autonomy" not in listed.stdout:
            errors.append("generator --list did not emit ops_autonomy")
        valid = subprocess.run(
            [sys.executable, str(generator), "--root", str(repo), "--validate"],
            check=False,
            capture_output=True,
            text=True,
        )
        if valid.returncode != 0:
            errors.append(f"generator --validate failed:\n{valid.stdout}{valid.stderr}")
        gaps = subprocess.run(
            [sys.executable, str(generator), "--root", str(repo), "--gaps"],
            check=False,
            capture_output=True,
            text=True,
        )
        if gaps.returncode != 0:
            errors.append(f"generator --gaps failed:\n{gaps.stdout}{gaps.stderr}")
        cfg_text = config.read_text(encoding="utf-8")
        if "commands:" in cfg_text and "skip: true" not in cfg_text.split("commands:", 1)[1][:400]:
            errors.append("commands module must be skip: true (handwritten slash index)")
    if errors:
        print("FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
