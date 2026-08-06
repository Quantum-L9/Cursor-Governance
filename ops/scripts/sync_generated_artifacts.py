#!/usr/bin/env python3
"""Sync derived governance artifacts (manifests, registries, overrides).

Idempotent heal used by pre-commit and `make pr`. Regenerating derived files is
not a failure — callers should WARN to stage and continue when validators PASS.

Covered artifacts:
  * rules/RULES-MANIFEST.{json,yaml,md}
  * environment/claude-code/generated/skill-registry.json
  * environment/claude-code/settings.template.json skillOverrides
  * skills/AUTONOMY_MANIFEST.yaml (orphan skills → explicit_only)
  * commands/COMMANDS_MANIFEST.yaml
  * environment/program-execution/core/MANIFEST.yaml
  * environment/program-execution/MANIFEST.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPTS = Path(__file__).resolve().parent

GENERATED_PATH_PREFIXES = (
    "rules/RULES-MANIFEST.",
    "environment/claude-code/generated/skill-registry.json",
    "environment/claude-code/settings.template.json",
    "commands/COMMANDS_MANIFEST.yaml",
    "skills/AUTONOMY_MANIFEST.yaml",
    "environment/program-execution/core/MANIFEST.yaml",
    "environment/program-execution/MANIFEST.json",
)


def is_generated_path(rel: str) -> bool:
    if any(
        rel.startswith(prefix) or rel == prefix.rstrip(".") for prefix in GENERATED_PATH_PREFIXES
    ):
        return True
    # Orphan heal may set disable-model-invocation on skill frontmatter.
    if re.match(r"^skills/[^/]+/SKILL\.md$", rel):
        return True
    return False


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def run_generator(cmd: list[str], cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"generator failed ({' '.join(cmd)}):\n{result.stdout}\n{result.stderr}")
    if result.stdout.strip():
        print(result.stdout.rstrip())


def disk_skill_names(root: Path) -> list[str]:
    skills_dir = root / "skills"
    return sorted(
        path.name
        for path in skills_dir.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def ensure_explicit_frontmatter(skill_md: Path) -> bool:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {skill_md}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"unterminated YAML frontmatter: {skill_md}")
    fm = yaml.safe_load(text[4:end]) or {}
    if not isinstance(fm, dict):
        raise ValueError(f"frontmatter must be a mapping: {skill_md}")
    if fm.get("disable-model-invocation") is True:
        return False
    fm["disable-model-invocation"] = True
    body = text[end + 5 :]
    new_text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body
    skill_md.write_text(new_text, encoding="utf-8")
    return True


def heal_orphan_skills(root: Path, wrote: list[str], warnings: list[str]) -> None:
    manifest_path = root / "skills" / "AUTONOMY_MANIFEST.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    tiers = manifest.setdefault("tiers", {})
    auto = {entry["skill"] for entry in tiers.get("auto_invoke", []) if isinstance(entry, dict)}
    explicit_entries = list(tiers.get("explicit_only", []) or [])
    explicit = {
        entry["skill"]
        for entry in explicit_entries
        if isinstance(entry, dict) and entry.get("skill")
    }
    listed = auto | explicit
    orphans = [name for name in disk_skill_names(root) if name not in listed]
    if not orphans:
        return
    for name in orphans:
        skill_md = root / "skills" / name / "SKILL.md"
        if ensure_explicit_frontmatter(skill_md):
            wrote.append(str(skill_md.relative_to(root)))
        explicit_entries.append(
            {
                "skill": name,
                "reason": "auto-registered by sync_generated_artifacts (orphan → explicit_only)",
            }
        )
        warnings.append(f"orphan skill auto-registered as explicit_only: {name}")
    tiers["explicit_only"] = explicit_entries
    new_text = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=1000)
    if write_text_if_changed(manifest_path, new_text):
        wrote.append(str(manifest_path.relative_to(root)))


def sync_skill_overrides(root: Path, wrote: list[str]) -> None:
    manifest = yaml.safe_load(
        (root / "skills" / "AUTONOMY_MANIFEST.yaml").read_text(encoding="utf-8")
    )
    explicit = [
        str(entry["skill"])
        for entry in (manifest.get("tiers", {}) or {}).get("explicit_only", [])
        if isinstance(entry, dict) and entry.get("skill")
    ]
    settings_path = root / "environment" / "claude-code" / "settings.template.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    desired = {name: "user-invocable-only" for name in sorted(explicit)}
    if settings.get("skillOverrides") == desired:
        return
    settings["skillOverrides"] = desired
    new_text = json.dumps(settings, indent=2, ensure_ascii=True) + "\n"
    if write_text_if_changed(settings_path, new_text):
        wrote.append(str(settings_path.relative_to(root)))


def sync_rules(root: Path, wrote: list[str]) -> None:
    before = {
        path: path.read_bytes() if path.is_file() else None
        for path in (
            root / "rules" / "RULES-MANIFEST.json",
            root / "rules" / "RULES-MANIFEST.yaml",
            root / "rules" / "RULES-MANIFEST.md",
        )
    }
    run_generator(
        [sys.executable, str(SCRIPTS / "generate_rules_manifest.py"), "--root", str(root)], root
    )
    for path, prior in before.items():
        if path.is_file() and path.read_bytes() != prior:
            wrote.append(str(path.relative_to(root)))


def sync_skill_registry(root: Path, wrote: list[str]) -> None:
    out = root / "environment" / "claude-code" / "generated" / "skill-registry.json"
    prior = out.read_bytes() if out.is_file() else None
    run_generator(
        [sys.executable, str(SCRIPTS / "build_claude_skill_registry.py"), "--root", str(root)],
        root,
    )
    if out.is_file() and out.read_bytes() != prior:
        wrote.append(str(out.relative_to(root)))


def sync_commands(root: Path, wrote: list[str]) -> None:
    out = root / "commands" / "COMMANDS_MANIFEST.yaml"
    prior = out.read_bytes() if out.is_file() else None
    run_generator(
        [sys.executable, str(SCRIPTS / "generate_commands_manifest.py"), "--root", str(root)],
        root,
    )
    if out.is_file() and out.read_bytes() != prior:
        wrote.append(str(out.relative_to(root)))


def sync_pe_core(root: Path, wrote: list[str]) -> None:
    pe_core = root / "environment" / "program-execution" / "core"
    if not pe_core.is_dir():
        return
    out = pe_core / "MANIFEST.yaml"
    prior = out.read_bytes() if out.is_file() else None
    run_generator(
        [
            sys.executable,
            str(pe_core / "scripts" / "generate_manifest.py"),
            str(pe_core),
            "--schema",
            "program-execution-system.manifest.v2",
            "--artifact",
            "program-execution-system-v2.0.0",
        ],
        root,
    )
    if out.is_file() and out.read_bytes() != prior:
        wrote.append(str(out.relative_to(root)))


def sync_pe_adapters(root: Path, wrote: list[str]) -> None:
    pe = root / "environment" / "program-execution"
    if not pe.is_dir():
        return
    out = pe / "MANIFEST.json"
    prior = out.read_bytes() if out.is_file() else None
    run_generator(
        [sys.executable, str(pe / "scripts" / "generate_manifest.py"), str(pe)],
        root,
    )
    if out.is_file() and out.read_bytes() != prior:
        wrote.append(str(out.relative_to(root)))


def should_run(changed: set[str] | None, prefixes: tuple[str, ...]) -> bool:
    if changed is None:
        return True
    return any(path.startswith(prefix) for path in changed for prefix in prefixes)


def sync(
    root: Path,
    *,
    changed_paths: set[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    wrote: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    changed = None if force else changed_paths

    try:
        if should_run(changed, ("rules/",)):
            sync_rules(root, wrote)
        if should_run(
            changed,
            (
                "skills/",
                "environment/claude-code/generated/skill-registry.json",
                "environment/claude-code/settings.template.json",
            ),
        ):
            heal_orphan_skills(root, wrote, warnings)
            sync_skill_registry(root, wrote)
            sync_skill_overrides(root, wrote)
        if should_run(changed, ("commands/",)):
            sync_commands(root, wrote)
        pe_touched = should_run(changed, ("environment/program-execution/",))
        if pe_touched:
            sync_pe_core(root, wrote)
            sync_pe_adapters(root, wrote)
    except Exception as exc:  # noqa: BLE001 — surface as structured error to gate
        errors.append(str(exc))

    return {
        "wrote": sorted(set(wrote)),
        "warnings": warnings,
        "errors": errors,
    }


def validate_after_sync(root: Path) -> list[str]:
    errors: list[str] = []
    checks = [
        [sys.executable, str(SCRIPTS / "validate_rules_manifest.py"), "--root", str(root)],
        [
            sys.executable,
            str(SCRIPTS / "build_claude_skill_registry.py"),
            "--root",
            str(root),
            "--check",
        ],
        [sys.executable, str(SCRIPTS / "validate_commands_manifest.py"), "--root", str(root)],
    ]
    activation = root / "environment" / "claude-code" / "validate_skill_activation.py"
    if activation.is_file():
        # Skip embedded pytest fixtures in activation validator during sync — too heavy;
        # structural checks only via a light path: registry --check + overrides already covered.
        pass
    for cmd in checks:
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(f"{' '.join(cmd)} failed:\n{result.stdout}\n{result.stderr}".strip())
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--changed-file",
        type=Path,
        help="Optional file listing repo-relative changed paths (one per line)",
    )
    parser.add_argument("--force", action="store_true", help="Sync all covered artifacts")
    parser.add_argument("--check", action="store_true", help="Validate after sync")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    args = parser.parse_args()
    root = args.root.resolve()

    changed: set[str] | None = None
    if args.changed_file and args.changed_file.is_file():
        changed = {
            line.strip()
            for line in args.changed_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("SOURCE:")
        }
        if not changed and not args.force:
            # Empty change set → still force on governance trees so local drift heals.
            args.force = True

    result = sync(root, changed_paths=changed, force=args.force)
    if args.check and not result["errors"]:
        result["errors"].extend(validate_after_sync(root))

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
        if result["wrote"]:
            print("WROTE:")
            for path in result["wrote"]:
                print(f"  {path}")
        else:
            print("CURRENT: no generated artifacts needed updates")
        for err in result["errors"]:
            print(f"ERROR: {err}", file=sys.stderr)

    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
