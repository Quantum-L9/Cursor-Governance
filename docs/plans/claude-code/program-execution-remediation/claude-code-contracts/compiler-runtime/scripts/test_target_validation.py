#!/usr/bin/env python3
"""Regression suite for v2.7.0 target-aware validation and same-branch contract chaining."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    import yaml
except ImportError as exc:  # pragma: no cover - packaging environment must provide PyYAML
    raise SystemExit("PyYAML required for regression suite") from exc

ROOT = Path(__file__).resolve().parent.parent
COMPILER = ROOT / "scripts" / "compile_contract.py"
NODE_EXAMPLE = ROOT / "examples" / "campaign-spec.example.yaml"
PY_EXAMPLE = ROOT / "examples" / "campaign-spec.python.example.yaml"
GO_EXAMPLE = ROOT / "examples" / "campaign-spec.go.example.yaml"


def run(cmd, *, cwd=None, expect=0):
    cp = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if cp.returncode != expect:
        raise AssertionError(
            f"command returned {cp.returncode}, expected {expect}: {' '.join(map(str, cmd))}\n{cp.stdout}"
        )
    return cp


def compile_spec(spec_path: Path, out: Path, *, expect=0, emit=True):
    cmd = [sys.executable, str(COMPILER), "--spec", str(spec_path), "--out", str(out), "--validate"]
    if emit:
        cmd.append("--emit-artifacts")
    return run(cmd, expect=expect)


def load_contracts(out: Path):
    return [json.loads(p.read_text()) for p in sorted(out.glob("PR-*.contract.json"))]


def tiny_spec(items=2):
    base_item = {
        "title": "fixture",
        "allowed_files": [{"deliverable": "fixture", "path": "src/fixture.txt"}],
        "forbidden_capabilities": ["remote deployment"],
        "verify_proof": "true",
        "sizing": {"new_files": 1, "modified_files": 0, "test_cases": 1, "commits": 1},
        "readiness": {
            "categories": {
                "repo_clarity": 10, "arch_mapping": 15, "local_reproducibility": 10,
                "test_eval_coverage": 15, "security_boundaries": 10,
                "observability_integrity": 10, "deploy_rollback": 10, "transition_clarity": 15,
            }
        },
    }
    rows = []
    for i in range(1, items + 1):
        row = copy.deepcopy(base_item)
        row["key"] = f"{i:03d}"
        row["title"] = f"fixture {i}"
        row["allowed_files"] = [{"deliverable": f"fixture {i}", "path": f"src/fixture{i}.txt"}]
        row["verify_proof"] = f"test -f proof{i}"
        rows.append(row)
    return {
        "campaign": {
            "id_prefix": "SHELL-TEST",
            "contract_version": "2.7.0",
            "target_repo": "ExampleOrg/shell-test",
            "target_branch": "claude/shared-chain",
            "validation": {
                "cold_resume": {"commands": ["true"]},
                "commit_gate": {"commands": ["true"]},
            },
            "dpk": {
                "rollback_target": "git revert HEAD",
                "has_ai_feature": False,
                "manifest": {
                    "schema_version": "dpk-1.0",
                    "repository": {
                        "id": "shell-test", "name": "shell-test", "type": "test",
                        "lifecycle": "beta", "criticality": "tier-3",
                    },
                    "ownership": {
                        "accountable_team": "ExampleOrg", "technical_owner": "platform",
                        "operational_owner": "platform",
                    },
                    "boundaries": {"owns": ["src/**"], "does_not_own": ["remote deployment"]},
                    "interfaces": {"inbound": [], "outbound": []},
                },
            },
        },
        "items": rows,
    }


class TargetValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ccc-v270-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_spec(self, spec, name="spec.yaml"):
        p = self.tmp / name
        p.write_text(yaml.safe_dump(spec, sort_keys=False))
        return p

    def test_node_explicit_npm_is_preserved(self):
        out = self.tmp / "node"
        compile_spec(NODE_EXAMPLE, out)
        text = "\n".join(p.read_text() for p in out.glob("PR-*.contract.json"))
        self.assertIn("npm run validate", text)
        first = load_contracts(out)[0]
        self.assertIn("npm run validate", first["resume_from"]["verify_before_starting"])
        self.assertIn("npm run validate", first["commit_gate"]["required_before_commit"])

    def test_python_has_no_implicit_npm_and_predecessor_proof_is_bound(self):
        out = self.tmp / "python"
        compile_spec(PY_EXAMPLE, out)
        all_text = "\n".join(p.read_text() for p in out.rglob("*") if p.is_file())
        self.assertNotIn("npm ci", all_text)
        self.assertNotIn("npm run validate", all_text)
        contracts = load_contracts(out)
        self.assertEqual(len(contracts), 2)
        c1, c2 = contracts
        self.assertIn(c1["git_workflow"]["completion_proof"], c2["resume_from"]["verify_before_starting"])
        py_spec = yaml.safe_load(PY_EXAMPLE.read_text())
        cold_resume = set(py_spec["campaign"]["validation"]["cold_resume"]["commands"])
        predecessor_repo_only = [
            cmd for cmd in c1["commit_gate"]["required_before_commit"]
            if cmd != c1["git_workflow"]["completion_proof"] and cmd not in cold_resume
        ]
        for cmd in predecessor_repo_only:
            self.assertNotIn(cmd, c2["resume_from"]["verify_before_starting"])
        self.assertIn(c1["git_workflow"]["commit_subject"], "\n".join(c2["resume_from"]["verify_before_starting"]))
        self.assertEqual(c2["prerequisite_contract"]["required_state"], "committed_and_validated")

    def test_go_has_no_implicit_node_or_python_fallback(self):
        out = self.tmp / "go"
        compile_spec(GO_EXAMPLE, out)
        all_text = "\n".join(p.read_text() for p in out.rglob("*") if p.is_file())
        self.assertIn("go test ./...", all_text)
        self.assertNotIn("npm run validate", all_text)
        self.assertNotIn("python -m unittest", all_text)

    def test_missing_validation_fails_closed(self):
        spec = tiny_spec(1)
        del spec["campaign"]["validation"]
        cp = compile_spec(self.write_spec(spec), self.tmp / "missing", expect=1, emit=False)
        self.assertIn("campaign.validation is required", cp.stdout)

    def test_empty_validation_fails_closed(self):
        spec = tiny_spec(1)
        spec["campaign"]["validation"]["cold_resume"]["commands"] = []
        cp = compile_spec(self.write_spec(spec), self.tmp / "empty", expect=1, emit=False)
        self.assertIn("at least one command is required", cp.stdout)

    def test_multiline_validation_fails_closed(self):
        spec = tiny_spec(1)
        spec["campaign"]["validation"]["cold_resume"]["commands"] = ["true\necho unsafe"]
        cp = compile_spec(self.write_spec(spec), self.tmp / "multiline", expect=1, emit=False)
        self.assertIn("single-line shell command", cp.stdout)

    def test_multi_commit_item_fails_closed(self):
        spec = tiny_spec(1)
        spec["items"][0]["sizing"]["commits"] = 2
        cp = compile_spec(self.write_spec(spec), self.tmp / "multicommit", expect=1, emit=False)
        self.assertIn("sizing.commits must equal 1", cp.stdout)

    def test_identical_repo_gate_and_completion_proof_dedupes_without_false_failure(self):
        spec = tiny_spec(1)
        spec["campaign"]["validation"]["commit_gate"]["commands"] = ["test -f proof1"]
        spec["items"][0]["verify_proof"] = "test -f proof1"
        out = self.tmp / "dedupe"
        compile_spec(self.write_spec(spec), out)
        contract = load_contracts(out)[0]
        self.assertEqual(contract["commit_gate"]["required_before_commit"], ["test -f proof1"])
        self.assertEqual(contract["git_workflow"]["completion_proof"], "test -f proof1")

    def test_branch_and_predecessor_preflight_execute_fail_closed(self):
        spec = tiny_spec(2)
        spec_path = self.write_spec(spec)
        out = self.tmp / "runtime"
        compile_spec(spec_path, out)
        contracts = load_contracts(out)
        c1, c2 = contracts
        p1 = out / "artifacts" / "PR-001" / c1["contract_id"] / "preflight.sh"
        p2 = out / "artifacts" / "PR-002" / c2["contract_id"] / "preflight.sh"

        repo = self.tmp / "repo"
        repo.mkdir()
        run(["git", "init", "-q"], cwd=repo)
        run(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
        run(["git", "config", "user.name", "Compiler Test"], cwd=repo)
        (repo / "README").write_text("base\n")
        run(["git", "add", "README"], cwd=repo)
        run(["git", "commit", "-q", "-m", "base"], cwd=repo)
        run(["git", "checkout", "-q", "-b", spec["campaign"]["target_branch"]], cwd=repo)

        # Contract 1 preflight is runnable before its output exists.
        run(["bash", str(p1)], cwd=repo)

        # Simulate contract 1 completion: proof exists and exact compiler-owned commit is HEAD.
        (repo / "proof1").write_text("green\n")
        run(["git", "add", "proof1"], cwd=repo)
        run(["git", "commit", "-q", "-m", c1["git_workflow"]["commit_subject"]], cwd=repo)
        run(["bash", str(p2)], cwd=repo)

        # Wrong branch must fail even though predecessor completion proof and commit are still present.
        run(["git", "checkout", "-q", "-b", "wrong-branch"], cwd=repo)
        run(["bash", str(p2)], cwd=repo, expect=1)

    def test_deterministic_recompile_and_single_terminal_delivery(self):
        spec_path = self.write_spec(tiny_spec(3))
        a, b = self.tmp / "a", self.tmp / "b"
        compile_spec(spec_path, a)
        compile_spec(spec_path, b)
        ca, cb = load_contracts(a), load_contracts(b)
        self.assertEqual(ca, cb)
        self.assertEqual([c["session_budget"]["source_commits"] for c in ca], [[1], [2], [3]])
        terminal = [c for c in ca if c["git_workflow"]["terminal_delivery"]["authorized"]]
        self.assertEqual(len(terminal), 1)
        self.assertIs(terminal[0], ca[-1])
        self.assertEqual(terminal[0]["git_workflow"]["terminal_delivery"]["command"], "make pr")
        for c in ca[:-1]:
            self.assertIsNone(c["git_workflow"]["terminal_delivery"]["command"])

    def test_emitter_has_no_ecosystem_fallback_literals(self):
        source = COMPILER.read_text()
        for forbidden in [
            "npm ci", "npm run validate", "pytest", "python -m unittest",
            "go test ./...", "cargo test", "mvn test", "gradle test", "bundle exec",
        ]:
            self.assertNotIn(forbidden, source, f"implicit ecosystem fallback reintroduced: {forbidden}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
