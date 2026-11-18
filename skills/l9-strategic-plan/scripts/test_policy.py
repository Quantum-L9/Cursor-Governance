import json

from script_loader import load_sibling

_plan = load_sibling("validate_working_plan")
check_policy = _plan.check_policy
check_unchanged = _plan.check_unchanged
verify_policy = _plan.verify_policy


def test_policy_assertions():
    good = {
        "graph.json": json.dumps(
            {"edges": [{"source": "a", "target": "b", "relation": "requires"}], "priority": ["a"]}
        ).encode(),
        "dashboard.json": json.dumps({"priority": ["a"]}).encode(),
        "protected.json": b"fixed",
    }
    rules = {
        "authority_ref": "test:operator",
        "assertions": [
            {
                "id": "right",
                "kind": "edge_exists",
                "file": "graph.json",
                "source": "a",
                "target": "b",
            },
            {
                "id": "reverse",
                "kind": "edge_absent",
                "file": "graph.json",
                "source": "b",
                "target": "a",
            },
            {
                "id": "sync",
                "kind": "matches_file",
                "file": "graph.json",
                "pointer": "/priority",
                "other_file": "dashboard.json",
                "other_pointer": "/priority",
            },
        ],
        "must_remain_unchanged": ["protected.json"],
        "allowed_changed_paths": ["graph.json", "dashboard.json"],
    }
    verify_policy(rules)
    assert len(check_policy(good, rules)) == 3
    bad = dict(good)
    bad["graph.json"] = json.dumps(
        {"edges": [{"source": "b", "target": "a", "relation": "requires"}], "priority": ["a"]}
    ).encode()
    try:
        check_policy(bad, rules)
        raise AssertionError("reversed edge accepted")
    except ValueError as e:
        assert "POLICY_ASSERTION_FAILED" in str(e)
    bad = dict(good)
    bad["dashboard.json"] = json.dumps({"priority": ["b"]}).encode()
    try:
        check_policy(bad, rules)
        raise AssertionError("stale projection accepted")
    except ValueError as e:
        assert "POLICY_ASSERTION_FAILED" in str(e)
    bad = dict(good)
    bad["protected.json"] = b"changed"
    try:
        check_unchanged(good, bad, rules)
        raise AssertionError("protected file changed")
    except ValueError as e:
        assert "PROTECTED_PATH_CHANGED" in str(e) or "UNEXPECTED_CHANGED_PATH" in str(e)
    bad = dict(good)
    bad["new.json"] = b"new"
    try:
        check_unchanged(good, bad, rules)
        raise AssertionError("unlisted addition accepted")
    except ValueError as e:
        assert "UNEXPECTED_CHANGED_PATH" in str(e)
    removed = dict(good)
    del removed["protected.json"]
    try:
        check_unchanged(good, removed, rules)
        raise AssertionError("unlisted removal accepted")
    except ValueError as e:
        assert "UNEXPECTED_CHANGED_PATH" in str(e)
    listed = dict(rules)
    listed["allowed_changed_paths"] = [*rules["allowed_changed_paths"], "new.json"]
    assert check_unchanged(good, bad, listed) == ["new.json"]


if __name__ == "__main__":
    test_policy_assertions()
