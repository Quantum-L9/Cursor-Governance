"""semgrep-l9 stages the governance org-ci stages for the consumer under test.

Core (l9-ci-core #237) binds the four Gate routing rules only to a repository
that declares `product_kind: node` in `.l9/ci.json`; every other repository gets
the same policy with only those rules `disabled`. The lane does not re-implement
that: it runs Core's own resolve-consumer-metadata and resolve-governance
actions. Here those two actions are stand-ins honouring the same interface
(env in, GITHUB_OUTPUT out, files staged under GITHUB_WORKSPACE), and the SDK is
a stand-in that classifies findings by the staged policy, so the scoping is
exercised without the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import findings as fnd  # noqa: E402
import manifest  # noqa: E402
import run  # noqa: E402

ROUTING = "l9.runtime.sdk.source.l9_ci.rulesets.semgrep.python.l9.routing.hardcoded-peer-node-url"
CREDENTIAL = "l9.baseline.python.hardcoded-credential"
CORE_SHA = "c" * 40
INADMISSIBLE = "resolve-consumer-metadata: product_kind must be one of ['dependency', 'node']"

METADATA = f"""
import json, os, sys
from pathlib import Path
path = Path(os.environ["GITHUB_WORKSPACE"]) / ".l9" / "ci.json"
kind = ""
if path.is_file():
    kind = json.loads(path.read_text()).get("product_kind", "")
    if kind not in ("", "node", "dependency"):
        print({INADMISSIBLE!r}, file=sys.stderr)
        raise SystemExit(2)
with open(os.environ["GITHUB_OUTPUT"], "a") as out:
    out.write(f"present={{str(path.is_file()).lower()}}\\nproduct-kind={{kind}}\\n")
"""

RESOLVE = f"""
import json, os
from pathlib import Path
kind = os.environ.get("L9_PRODUCT_KIND", "")
scope = "node" if kind == "node" else "non-node"
policy = {{"schema": "l9.finding-policy/v1", "defaults": {{"mode": "blocking"}}, "rules": {{}}}}
if scope != "node":
    policy["rules"][{ROUTING!r}] = {{
        "policy_key": "routing.constellation-node-only", "mode": "disabled"}}
staged = Path(os.environ["GITHUB_WORKSPACE"]) / ".l9/runtime/org-governance"
(staged / "semgrep-identity-maps").mkdir(parents=True, exist_ok=True)
(staged / "semgrep-policy.yaml").write_text(json.dumps(policy))
(staged / "semgrep-identity-maps" / "python.yaml").write_text("rules: {{}}\\n")
Path(os.environ["GITHUB_OUTPUT"] + ".env.json").write_text(json.dumps(dict(os.environ)))
with open(os.environ["GITHUB_OUTPUT"], "a") as out:
    out.write("sdk-profile=ci_fast\\nmode=blocking\\nenabled=true\\nstrict=false\\n")
    out.write("required-provider=true\\n")
    out.write("sdk-policy=.l9/runtime/org-governance/semgrep-policy.yaml\\n")
    out.write(f"constellation-scope={{scope}}\\n")
    out.write("identity-map-directory=.l9/runtime/org-governance/semgrep-identity-maps\\n")
    out.write("waiver-ids=\\ngovernance-digest=sha256:test\\n")
"""

#: Classifies each finding by the staged policy, as the SDK does, and gates on
#: the blocking classifications.
POLICY_SDK = """
import json, os, sys
args = sys.argv[1:]
def value(flag):
    return args[args.index(flag) + 1]
if args[:2] == ["semgrep", "run"]:
    policy = json.load(open(value("--policy")))
    findings, classes = [], []
    for n, rule in enumerate(filter(None, os.environ["FAKE_RULES"].split(","))):
        fid = f"fn_{n}"
        findings.append({"finding_id": fid, "provider_rule_id": rule, "message": rule,
                         "locations": [{"normalized_path": "app.py", "start_line": n + 1}]})
        entry = policy["rules"].get(rule, {})
        classes.append({"finding_id": fid, "mode": entry.get("mode", "blocking"),
                        "policy_key": entry.get("policy_key")})
    bundle = {"findings": findings, "classifications": classes}
    open(value("--output"), "w").write(json.dumps(bundle))
    raise SystemExit(0)
if args[:2] == ["gate", "evaluate"]:
    bundle = json.load(open(value("--bundle")))
    blocking = [c["finding_id"] for c in bundle["classifications"] if c["mode"] == "blocking"]
    open(value("--output"), "w").write(json.dumps({"blocking_finding_ids": blocking}))
    raise SystemExit(1 if blocking else 0)
raise SystemExit(99)
"""


def _core_tree(root: Path) -> Path:
    (root / run.METADATA_ROOT).mkdir(parents=True)
    (root / run.GOVERNANCE_ROOT).mkdir(parents=True)
    (root / run.METADATA_ROOT / "metadata.py").write_text(METADATA)
    (root / run.GOVERNANCE_ROOT / "resolve.py").write_text(RESOLVE)
    return root


@pytest.fixture
def consumer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    core = _core_tree(tmp_path / "core")

    class Reader:
        CORE_GIT_URL = "unused"

        @staticmethod
        def core_commit(ref: str) -> str:
            assert ref == "main"
            return CORE_SHA

    monkeypatch.setattr(run, "_core_reader", lambda: Reader)
    monkeypatch.setattr(run, "core_actions", lambda cache_root, sha: core)
    scan = tmp_path / "scan"
    (scan / ".l9").mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / "cache").mkdir()
    sdk = tmp_path / "policy_sdk.py"
    sdk.write_text(POLICY_SDK)
    ctx = run.Context(
        loaded=manifest.load(),
        workspace=scan,
        slug="Quantum-L9/Example",
        cache=tmp_path / "cache",
        scan_dir=scan,
        sha="a" * 40,
        base="b" * 40,
        changed=["app.py"],
        ranges={},
        nice=False,
        timeout=60,
    )
    cli = [sys.executable, str(sdk)]
    return {"ctx": ctx, "scan": scan, "work": work, "cli": cli, "tmp": tmp_path}


def _declare(consumer: dict, product_kind: str | None) -> None:
    payload: dict[str, object] = {"schema": "l9.ci-consumer/v1", "repo_class": "python"}
    if product_kind is not None:
        payload["product_kind"] = product_kind
    (consumer["scan"] / ".l9" / "ci.json").write_text(json.dumps(payload))


def _judge(
    consumer: dict, monkeypatch: pytest.MonkeyPatch, rules: list[str]
) -> tuple[run.CoreGovernance, list[fnd.Finding], list[fnd.Finding]]:
    monkeypatch.setenv("FAKE_RULES", ",".join(rules))
    gov = run.resolve_core_governance(consumer["ctx"], consumer["work"], "pr_fast")
    found = run._sdk_gate(
        consumer["ctx"], consumer["cli"], ["python"], gov, consumer["work"], dict(os.environ)
    )
    block = consumer["ctx"].loaded.lanes["semgrep-l9"].block
    blocking = [f for f in found if fnd.blocks(f, block)]
    advisory = [f for f in found if not fnd.blocks(f, block)]
    return gov, blocking, advisory


@pytest.mark.parametrize("declared", [None, "dependency"])
def test_non_node_routing_findings_are_reported_but_do_not_block(
    consumer: dict, monkeypatch: pytest.MonkeyPatch, declared: str | None
) -> None:
    _declare(consumer, declared)
    gov, blocking, advisory = _judge(consumer, monkeypatch, [ROUTING])
    assert gov.scope == "non-node"
    assert blocking == []
    assert [(f.rule, f.severity) for f in advisory] == [(ROUTING, run.DISABLED_SEVERITY)]
    assert "routing.constellation-node-only" in advisory[0].message


def test_missing_consumer_metadata_is_not_a_node(
    consumer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    gov, blocking, advisory = _judge(consumer, monkeypatch, [ROUTING])
    assert (gov.scope, blocking, len(advisory)) == ("non-node", [], 1)


def test_declared_node_blocks_on_routing_findings(
    consumer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(consumer, "node")
    gov, blocking, advisory = _judge(consumer, monkeypatch, [ROUTING])
    assert gov.scope == "node"
    assert [(f.rule, f.severity) for f in blocking] == [(ROUTING, "error")]
    assert advisory == []


def test_non_routing_blocking_rule_still_blocks_a_non_node(
    consumer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(consumer, None)
    _, blocking, advisory = _judge(consumer, monkeypatch, [ROUTING, CREDENTIAL])
    assert [f.rule for f in blocking] == [CREDENTIAL]
    assert [f.rule for f in advisory] == [ROUTING]


def test_inadmissible_product_kind_fails_closed_with_cores_message(
    consumer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(consumer, "gateway")
    with pytest.raises(run.CoreRefusal) as refused:
        run.resolve_core_governance(consumer["ctx"], consumer["work"], "pr_fast")
    assert refused.value.message == INADMISSIBLE
    finding = refused.value.finding()
    assert (finding.rule, finding.severity, finding.path) == (
        "core/resolve-consumer-metadata",
        "error",
        ".l9/ci.json",
    )


def test_lane_turns_a_core_refusal_into_a_blocking_record(
    consumer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(consumer, "gateway")
    binary = consumer["tmp"] / "tool"
    binary.write_text("")
    monkeypatch.setattr(manifest.Manifest, "resolve", lambda self, name: binary)

    def no_sdk(*_args: object) -> Path:
        raise AssertionError("Core refused: the SDK must not be staged")

    monkeypatch.setattr(run, "stage_sdk_source", no_sdk)
    lane = consumer["ctx"].loaded.lanes["semgrep-l9"]
    record = run.run_lane(consumer["ctx"], lane, run.WeightedSemaphore(2))
    assert record["status"] == "fail"
    assert [b["rule"] for b in record["blocking"]] == ["core/resolve-consumer-metadata"]
    assert record["blocking"][0]["message"] == INADMISSIBLE


def test_resolver_receives_what_org_ci_hands_it(
    consumer: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declare(consumer, "node")
    gov, _, _ = _judge(consumer, monkeypatch, [])
    env_file = consumer["work"] / "resolve-governance.github-output.env.json"
    env = json.loads(env_file.read_text())
    assert env["L9_PRODUCT_KIND"] == "node"
    assert (env["L9_PROFILE"], env["L9_PROVIDER"], env["L9_EVENT_NAME"]) == (
        "pr_fast",
        "semgrep",
        "pull_request",
    )
    assert env["L9_REPOSITORY"] == "Quantum-L9/Example"
    assert Path(env["GITHUB_WORKSPACE"]) == consumer["scan"]
    assert "SEMGREP_APP_TOKEN" not in env
    assert (gov.core_sha, gov.strict, gov.required) == (CORE_SHA, False, True)
    assert (consumer["scan"] / gov.policy).is_file()
    assert (consumer["scan"] / gov.identity_maps / "python.yaml").is_file()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_core_actions_are_materialized_byte_for_byte_at_the_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core = tmp_path / "l9-ci-core"
    core.mkdir()
    _git(core, "init", "-q", "-b", "main")
    _core_tree(core)
    (core / run.GOVERNANCE_ROOT / "constellation-node-rules.json").write_text('{"x": 1}\n')
    (core / "unrelated.txt").write_text("not an action\n")
    _git(core, "add", ".")
    _git(core, "commit", "-q", "-m", "core")
    sha = _git(core, "rev-parse", "HEAD")

    class Reader:
        CORE_GIT_URL = str(core)

    monkeypatch.setattr(run, "_core_reader", lambda: Reader)
    root = run.core_actions(tmp_path / "cache", sha)
    scope_file = root / run.GOVERNANCE_ROOT / "constellation-node-rules.json"
    assert scope_file.read_text() == '{"x": 1}\n'
    assert (root / run.METADATA_ROOT / "metadata.py").read_text() == METADATA
    assert not (root / "unrelated.txt").exists()
    Reader.CORE_GIT_URL = str(tmp_path / "gone")  # cached per commit: no second fetch
    assert run.core_actions(tmp_path / "cache", sha) == root
