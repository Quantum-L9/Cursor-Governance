"""Issue #641: check-yaml must skip Helm Go templates on consumer make pr."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".pre-commit-config.yaml"

HELM_REL = "infra/k8s/helm/enrichment-api/templates/deployment.yaml"
REAL_YAML = "ops/autonomy/surface_profile.yaml"


def _hook_exclude(hook_id: str) -> str:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    for repo in data["repos"]:
        for hook in repo.get("hooks") or []:
            if hook.get("id") == hook_id:
                return str(hook.get("exclude") or "")
    raise AssertionError(f"hook {hook_id} missing")


def test_check_yaml_excludes_helm_templates_but_not_real_yaml() -> None:
    exclude = _hook_exclude("check-yaml")
    rx = re.compile(exclude)
    assert rx.search(HELM_REL)
    assert not rx.search(REAL_YAML)
    assert rx.search("environment/generated/foo.yaml")
    assert rx.search("environment/program-execution/core/bar.yaml")
