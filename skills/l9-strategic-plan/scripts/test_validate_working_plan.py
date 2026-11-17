#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def _load_sibling(stem: str):
    import importlib.util

    name = f"l9_strategic_plan_scripts.{stem}"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().parent / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(stem)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_plan = _load_sibling("validate_working_plan")
check_graph = _plan.check_graph
read_zip = _plan.read_zip


def pack(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for k, v in files.items():
            z.writestr("plan/" + k, v)


def test():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        good = d / "good.zip"
        bad = d / "bad.zip"
        g = json.dumps(
            {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"source": "a", "target": "b", "relation": "requires"}],
            }
        )
        pack(good, {"graph.json": g, "README.md": "working"})
        assert len(read_zip(good)) == 2
        assert (
            check_graph(
                read_zip(good),
                "graph.json",
                "nodes",
                "edges",
                "id",
                "source",
                "target",
                "relation",
                {"requires"},
            )["edges"]
            == 1
        )
        pack(
            bad,
            {
                "graph.json": json.dumps(
                    {
                        "nodes": [{"id": "a"}],
                        "edges": [{"source": "a", "target": "missing", "relation": "requires"}],
                    }
                )
            },
        )
        try:
            check_graph(
                read_zip(bad),
                "graph.json",
                "nodes",
                "edges",
                "id",
                "source",
                "target",
                "relation",
                {"requires"},
            )
            raise AssertionError("dangling edge passed")
        except ValueError as e:
            assert "dangling" in str(e)
        pack(bad, {"../escape": "unsafe"})
        try:
            read_zip(bad)
            raise AssertionError("traversal passed")
        except ValueError as e:
            assert "unsafe" in str(e)
        pack(bad, {"graph.json": g})
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("validate_working_plan.py")),
                str(bad),
                "--predecessor",
                str(good),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1 and "undocumented" in proc.stdout
        policy = d / "policy.json"
        policy.write_text(
            json.dumps(
                {
                    "authority_ref": "test:operator",
                    "assertions": [],
                    "must_remain_unchanged": ["README.md"],
                }
            )
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("validate_working_plan.py")),
                str(good),
                "--policy",
                str(policy),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1 and "predecessor required" in proc.stdout
        print("PASS structural tests including negative controls")


if __name__ == "__main__":
    test()
