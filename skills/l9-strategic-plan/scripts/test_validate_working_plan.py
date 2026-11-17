#!/usr/bin/env python3
import io
import json
import os
import tempfile
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

from script_loader import load_sibling

_plan = load_sibling("validate_working_plan")
check_graph = _plan.check_graph
read_zip = _plan.read_zip


def pack(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for k, v in files.items():
            z.writestr("plan/" + k, v)


def _invoke(argv):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = _plan.main(argv)
    return code, buffer.getvalue()


def test_structural_package():
    previous = os.getcwd()
    try:
        _structural_package()
    finally:
        os.chdir(previous)


def _structural_package():
    with tempfile.TemporaryDirectory() as t:
        os.chdir(t)
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
        code, out = _invoke([bad.name, "--predecessor", good.name])
        assert code == 1 and "undocumented" in out
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
        code, out = _invoke([good.name, "--policy", policy.name])
        assert code == 1 and "predecessor required" in out
        try:
            _plan.safe_path("/etc/passwd")
            raise AssertionError("path outside the working directory was accepted")
        except ValueError as exc:
            assert "outside the allowed directory" in str(exc)


if __name__ == "__main__":
    test_structural_package()
