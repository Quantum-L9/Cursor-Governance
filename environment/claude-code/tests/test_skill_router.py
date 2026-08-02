#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CLAUDE_DIR = HERE.parent
ROUTER_PATH = CLAUDE_DIR / "hooks" / "user_prompt_skill_router.py"
REGISTRY_PATH = CLAUDE_DIR / "generated" / "skill-registry.json"
CASES_PATH = HERE / "skill_routing_cases.json"


def load_router():
    spec = importlib.util.spec_from_file_location("l9_skill_router", ROUTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SkillRouterCases(unittest.TestCase):
    router: Any
    registry: dict[str, Any]
    cases: list[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.router = load_router()
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]

    def test_cases(self) -> None:
        for case in self.cases:
            with self.subTest(prompt=case["prompt"]):
                result = self.router.route_prompt(case["prompt"], self.registry)
                actual_primary = result["primary"] if result else None
                self.assertEqual(case.get("expected_primary"), actual_primary)
                if result:
                    self.assertEqual(case.get("expected_supporting", []), result["supporting"])
                    for forbidden in case.get("forbidden", []):
                        self.assertNotEqual(forbidden, result["primary"])
                        self.assertNotIn(forbidden, result["supporting"])


if __name__ == "__main__":
    unittest.main()
