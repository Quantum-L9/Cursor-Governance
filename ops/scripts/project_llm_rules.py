#!/usr/bin/env python3
"""Project rules/*.mdc into Claude-facing .md under environment/generated/llm-rules/.

SSOT remains rules/*.mdc. Generated files are deterministic projections with
checksums in MANIFEST.json. Never hand-edit the generated tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lib.rule_frontmatter import activation_class, normalize_globs, parse_rule  # noqa: E402

CONFIG_REL = Path("ops/config/llm_rules_projection.yaml")
GENERATED_MARKER = "<!-- generated-from: rules/{stem}.mdc; do-not-edit -->"
README_MARKER = "<!-- generated-from: ops/scripts/project_llm_rules.py; do-not-edit -->"


def load_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_REL
    if not path.is_file():
        raise FileNotFoundError(f"missing projection config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("llm_rules_projection.yaml must be a mapping")
    return data


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def render_frontmatter(description: str, paths: list[str] | None) -> str:
    payload: dict[str, Any] = {"description": description}
    if paths:
        payload["paths"] = paths
    dumped = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=1000).rstrip()
    return f"---\n{dumped}\n---\n"


def build_projected_text(stem: str, description: str, body: str, paths: list[str] | None) -> str:
    marker = GENERATED_MARKER.format(stem=stem)
    # Ensure body starts with a newline separation after frontmatter.
    body_text = body if body.startswith("\n") or body == "" else f"\n{body}"
    if not body_text.endswith("\n"):
        body_text += "\n"
    return f"{render_frontmatter(description, paths)}{body_text}\n{marker}\n"


def readme_text() -> str:
    return (
        f"{README_MARKER}\n"
        "# Generated LLM rules (do not edit)\n"
        "\n"
        "Authoritative source: `rules/*.mdc`.\n"
        "Regenerate: `python3 ops/scripts/project_llm_rules.py "
        '--root "$HOME/.cursor-governance"`.\n'
        "Claude Code mounts this directory at `.claude/rules` via "
        "`ops/scripts/reconcile_llm_rule_adapters.py`.\n"
        "Cursor continues to load `.mdc` via the `l9-governance` plugin.\n"
    )


def project_entries(
    root: Path, config: dict[str, Any]
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Return {relative_output_name: content} and MANIFEST rule rows."""
    source_rel = str(config.get("source_relative") or "rules")
    rules_dir = root / source_rel
    deny = {str(item) for item in (config.get("deny_stems") or [])}
    aliases_raw = config.get("aliases") or {}
    if not isinstance(aliases_raw, dict):
        raise ValueError("aliases must be a mapping of stem -> filename")
    aliases = {str(k): str(v) for k, v in aliases_raw.items()}
    project_agent = bool(config.get("project_agent_requested", False))

    outputs: dict[str, str] = {}
    rows: list[dict[str, Any]] = []

    for path in sorted(rules_dir.glob("*.mdc"), key=lambda p: p.name):
        stem = path.stem
        if stem in deny:
            rows.append(
                {
                    "stem": stem,
                    "source": f"{source_rel}/{path.name}",
                    "class": "denied",
                    "output": None,
                    "alias": None,
                    "source_sha256": sha256_bytes(path.read_bytes()),
                    "output_sha256": None,
                }
            )
            continue

        parsed = parse_rule(path)
        globs = normalize_globs(parsed.metadata.get("globs"))
        klass = activation_class(parsed.metadata, globs)
        if klass == "agent_requested" and not project_agent:
            rows.append(
                {
                    "stem": stem,
                    "source": f"{source_rel}/{path.name}",
                    "class": "skipped_agent_requested",
                    "output": None,
                    "alias": None,
                    "source_sha256": sha256_bytes(path.read_bytes()),
                    "output_sha256": None,
                }
            )
            continue

        description = str(parsed.metadata.get("description") or "").strip()
        paths = globs if klass == "paths" else None
        out_name = aliases.get(stem, f"{stem}.md")
        if not out_name.endswith(".md"):
            out_name = f"{out_name}.md"
        if out_name in outputs:
            raise ValueError(f"duplicate projected output name: {out_name}")

        text = build_projected_text(stem, description, parsed.body, paths)
        outputs[out_name] = text
        rows.append(
            {
                "stem": stem,
                "source": f"{source_rel}/{path.name}",
                "class": klass,
                "output": out_name,
                "alias": aliases.get(stem),
                "source_sha256": sha256_bytes(path.read_bytes()),
                "output_sha256": sha256_text(text),
            }
        )

    outputs["README.md"] = readme_text()
    return outputs, rows


def build_manifest(
    root: Path, config: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    projected = [row for row in rows if row.get("output")]
    return {
        "schema": "l9.llm-rules-projection/v1",
        "generator": "ops/scripts/project_llm_rules.py",
        "source_relative": str(config.get("source_relative") or "rules"),
        "output_relative": str(config.get("output_relative") or "environment/generated/llm-rules"),
        "summary": {
            "source_mdc": len(rows),
            "projected": len(projected),
            "denied": sum(1 for row in rows if row.get("class") == "denied"),
            "skipped_agent_requested": sum(
                1 for row in rows if row.get("class") == "skipped_agent_requested"
            ),
        },
        "rules": rows,
        "tree_sha256": sha256_text(
            json.dumps(
                {row["output"]: row["output_sha256"] for row in projected if row.get("output")},
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
    }


def output_dir(root: Path, config: dict[str, Any]) -> Path:
    return root / str(config.get("output_relative") or "environment/generated/llm-rules")


def is_managed_file(path: Path) -> bool:
    if path.name == "MANIFEST.json":
        return True
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "do-not-edit -->" in text or "generated-from:" in text


def write_tree(
    out: Path,
    outputs: dict[str, str],
    manifest: dict[str, Any],
    *,
    force: bool,
) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    managed_names = set(outputs) | {"MANIFEST.json"}
    unknown: list[str] = []
    for existing in sorted(out.iterdir()):
        if not existing.is_file():
            if existing.is_dir():
                unknown.append(f"{existing.name}/")
            continue
        if existing.name in managed_names:
            continue
        if is_managed_file(existing):
            existing.unlink()
            continue
        unknown.append(existing.name)
    if unknown and not force:
        raise RuntimeError(
            "unknown non-generated files in llm-rules output "
            f"(pass --force to wipe unmanaged): {', '.join(unknown)}"
        )
    if unknown and force:
        for name in unknown:
            target = out / name.rstrip("/")
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()

    wrote: list[str] = []
    for name, content in sorted(outputs.items()):
        path = out / name
        if path.is_file() and path.read_text(encoding="utf-8") == content:
            continue
        path.write_text(content, encoding="utf-8")
        wrote.append(name)

    manifest_text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    manifest_path = out / "MANIFEST.json"
    if not (manifest_path.is_file() and manifest_path.read_text(encoding="utf-8") == manifest_text):
        manifest_path.write_text(manifest_text, encoding="utf-8")
        wrote.append("MANIFEST.json")
    return wrote


def materialize(root: Path, *, force: bool = False) -> dict[str, Any]:
    config = load_config(root)
    outputs, rows = project_entries(root, config)
    manifest = build_manifest(root, config, rows)
    out = output_dir(root, config)
    wrote = write_tree(out, outputs, manifest, force=force)
    return {
        "output": str(out),
        "wrote": wrote,
        "summary": manifest["summary"],
    }


def check_projection(root: Path) -> list[str]:
    config = load_config(root)
    outputs, rows = project_entries(root, config)
    manifest = build_manifest(root, config, rows)
    out = output_dir(root, config)
    errors: list[str] = []
    if not out.is_dir():
        return [f"missing generated tree: {out.relative_to(root)}"]

    expected_names = set(outputs) | {"MANIFEST.json"}
    for existing in sorted(p.name for p in out.iterdir() if p.is_file()):
        if existing not in expected_names and not is_managed_file(out / existing):
            errors.append(f"unknown non-generated file: {existing}")

    for name, content in sorted(outputs.items()):
        path = out / name
        if not path.is_file():
            errors.append(f"missing projected file: {name}")
            continue
        if path.read_text(encoding="utf-8") != content:
            errors.append(f"drift: {name}")

    manifest_path = out / "MANIFEST.json"
    expected_manifest = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if not manifest_path.is_file():
        errors.append("missing MANIFEST.json")
    elif manifest_path.read_text(encoding="utf-8") != expected_manifest:
        errors.append("drift: MANIFEST.json")

    # Temp rebuild parity (memory already compared; keep for API symmetry).
    with tempfile.TemporaryDirectory() as temp:
        temp_out = Path(temp) / "llm-rules"
        write_tree(temp_out, outputs, manifest, force=True)
        for name in expected_names:
            a = out / name
            b = temp_out / name
            if a.is_file() and b.is_file() and a.read_bytes() != b.read_bytes():
                if f"drift: {name}" not in errors:
                    errors.append(f"temp-parity drift: {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true", help="Fail if generated tree is stale")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove unknown non-generated files in the output directory",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        if args.check:
            errors = check_projection(root)
            if errors:
                for error in errors:
                    print(f"FAIL: {error}", file=sys.stderr)
                print(f"RESULT: FAIL ({len(errors)} errors)", file=sys.stderr)
                return 1
            if not args.quiet:
                print("RESULT: PASS - llm-rules projection matches rules/*.mdc")
            return 0

        result = materialize(root, force=args.force)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        summary = result["summary"]
        label = "GENERATED" if result["wrote"] else "CURRENT"
        print(
            f"{label}: projected={summary['projected']} "
            f"denied={summary['denied']} skipped={summary['skipped_agent_requested']}"
        )
        for name in result["wrote"]:
            print(f"  wrote: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
