"""Regression guard: the PE manifest heal must stay reachable.

``environment/program-execution/MANIFEST.json`` hashes the whole mutable
Program Execution tree, so ordinary PE edits invalidate it, and
``make program-execution-conformance`` hard-fails on a digest mismatch. Writing
it is opt-in: ``sync()`` reaches ``sync_pe_adapters`` only under
``pe_manifest=True`` / ``--pe-manifest``, and a bare ``--force`` does not.

That opt-in was, for a while, opted into by nobody. The only caller was
``.pre-commit-config.yaml``, labelled "commit-time heal" -- but this repo has no
git commit hook (``run_pr_precommit.sh`` says so), that config is executed only
by ``run_pr_precommit.sh``, and that script SKIPs the hook by name. The hook's
comment said the work had moved to the PR gate; the gate called sync without the
flag. So the manifest was regenerated only when a human remembered, the target
sat red on ``main``, and three separate comments described a heal that ran
nowhere.

Two callers now pass it, and each covers a different failure:

  * ``ops/scripts/run_pr_gate.sh`` heals locally on the sanctioned publish path
  * ``.github/workflows/governance-self-check.yml`` fails the PR on drift

Dropping either is silent -- nothing else would report it -- so both are pinned
here, by parsing the real invocations through the sync script's own argparse
rather than by grepping for prose.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shlex
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "ops" / "scripts" / "run_pr_gate.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "governance-self-check.yml"
SYNC = ROOT / "ops" / "scripts" / "sync_generated_artifacts.py"
PE_MANIFEST = "environment/program-execution/MANIFEST.json"


def _sync_module():
    spec = importlib.util.spec_from_file_location("sync_generated_artifacts", SYNC)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_NAME = "sync_generated_artifacts.py"
_INTERPRETER_RE = re.compile(r"^python[0-9.]*$")


def _sync_invocations(text: str) -> list[list[str]]:
    """Every `sync_generated_artifacts.py ...` command line in a shell body.

    Line continuations are folded first so a multi-line invocation reads as one
    command (the PR gate spells it that way). Shell variables holding the script
    path are resolved too, because the workflow assigns
    ``gen=ops/scripts/sync_generated_artifacts.py`` and then calls ``"$gen"`` --
    matching only a literal path would silently find nothing there and the
    assertion would pass on an empty generator.
    """
    folded = re.sub(r"\\\n\s*", " ", text)
    aliases: set[str] = set()
    found: list[list[str]] = []
    for line in folded.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            argv = shlex.split(stripped, comments=True)
        except ValueError:  # unbalanced quotes in unrelated shell prose
            continue
        for index, token in enumerate(argv):
            name, sep, value = token.partition("=")
            if sep and name.isidentifier() and value.endswith(SCRIPT_NAME):
                aliases.add(name)
                break
            names_script = token.endswith(SCRIPT_NAME) or token.strip('${}"') in aliases
            # `[ -f "$gen" ]` names the script but does not run it. An
            # invocation is the script preceded by an interpreter.
            invoked = index > 0 and _INTERPRETER_RE.match(argv[index - 1])
            if names_script and invoked:
                tail: list[str] = []
                for arg in argv[index + 1 :]:
                    if arg in {"||", "&&", ";", "|", ">", ">>", "2>&1"}:
                        break
                    tail.append(arg)
                found.append(tail)
                break
    return found


def _parse(argv: list[str]) -> argparse.Namespace:
    """Parse flags with the real CLI, so a renamed or dropped flag is caught.

    Values are irrelevant here; only the parsed flags are asserted. Paths are
    replaced because the callers interpolate shell variables ("$WS") that
    argparse would happily accept but that mean nothing outside the script.
    """
    cleaned: list[str] = []
    skip = False
    for token in argv:
        if skip:
            cleaned.extend([str(ROOT)])
            skip = False
            continue
        if token in {"--root", "--changed-file", "--workspace"}:
            cleaned.append(token)
            skip = True
            continue
        cleaned.append(token)
    return _sync_module().build_parser().parse_args(cleaned)


def test_pr_gate_opts_into_the_pe_manifest() -> None:
    """The local heal. Without it every PE branch fails conformance by hand."""
    invocations = _sync_invocations(GATE.read_text(encoding="utf-8"))
    assert invocations, f"no sync_generated_artifacts.py invocation found in {GATE}"
    assert any(_parse(argv).pe_manifest for argv in invocations), (
        "run_pr_gate.sh no longer passes --pe-manifest. Without it "
        f"{PE_MANIFEST} is never regenerated on the publish path and "
        "`make program-execution-conformance` goes red on every PE edit."
    )


def test_governance_self_check_enforces_pe_manifest_drift() -> None:
    """The CI half: regenerate with the flag AND diff the artifact."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    bodies = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    ]
    drift = [body for body in bodies if "sync_generated_artifacts.py" in body]
    assert drift, "governance-self-check.yml no longer regenerates artifacts"

    body = "\n".join(drift)
    invocations = _sync_invocations(body)
    assert invocations, "the drift step no longer invokes the sync script"
    assert any(_parse(argv).pe_manifest for argv in invocations), (
        "governance-self-check.yml must regenerate with --pe-manifest"
    )
    assert PE_MANIFEST in body, (
        f"{PE_MANIFEST} must stay in the drift-checked paths. Regenerating it "
        "without diffing it proves nothing."
    )


def test_the_parser_check_would_fail_without_the_flag() -> None:
    """Guard the guard: a check that cannot fail is not a check."""
    assert not _parse(["--root", "$WS", "--force", "--check"]).pe_manifest
    assert _parse(["--root", "$WS", "--force", "--pe-manifest", "--check"]).pe_manifest


def test_extraction_reads_both_spellings_and_ignores_non_invocations() -> None:
    """The extractor must see what the two callers actually write.

    An extractor that silently found nothing would make the assertions above
    vacuous, so the shapes it has to handle are pinned directly: the gate's
    literal interpolated path with line continuations, the workflow's shell
    alias, and the `[ -f "$gen" ]` guard that names the script without running
    it.
    """
    gate_shape = (
        'python3 "$GOV_ROOT/ops/scripts/sync_generated_artifacts.py" \\\n'
        '  --root "$WS" \\\n'
        "  --pe-manifest \\\n"
        "  --check\n"
    )
    assert [_parse(argv).pe_manifest for argv in _sync_invocations(gate_shape)] == [True]

    workflow_shape = (
        "gen=ops/scripts/sync_generated_artifacts.py\n"
        '[ -f "$gen" ] || { echo missing; exit 1; }\n'
        'python3 "$gen" --force --pe-manifest --check --json\n'
    )
    assert [_parse(argv).pe_manifest for argv in _sync_invocations(workflow_shape)] == [True]

    # The flag removed from either spelling is detected, not silently missed.
    for shape in (gate_shape, workflow_shape):
        stripped = shape.replace("--pe-manifest", "")
        invocations = _sync_invocations(stripped)
        assert invocations, "extractor lost the invocation; the guard would be vacuous"
        assert not any(_parse(argv).pe_manifest for argv in invocations)


def test_flag_is_load_bearing(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--force` alone must not reach the manifest; the flag must.

    Pins the asymmetry the two callers depend on. If a future edit made
    ``--force`` reach it, the opt-in would be gone and every ``--force`` caller
    would start hashing the whole PE tree; if the flag stopped reaching it, the
    heal would be silently dead again.
    """
    module = _sync_module()
    calls: list[str] = []
    for name in ("sync_pe_core", "sync_pe_templates", "sync_pe_adapters"):
        monkeypatch.setattr(module, name, lambda root, wrote, _name=name: calls.append(_name))
    pe_change = {"environment/program-execution/scripts/run_campaign.py"}

    module.sync(ROOT, changed_paths=pe_change, pe_manifest=False)
    assert "sync_pe_adapters" not in calls, "--force alone must not write the PE manifest"
    assert "sync_pe_core" in calls, "the PE section did not run; the test proves nothing"

    calls.clear()
    module.sync(ROOT, changed_paths=pe_change, pe_manifest=True)
    assert "sync_pe_adapters" in calls, "pe_manifest=True must reach the PE manifest"


def test_non_pe_change_does_not_hash_the_pe_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag is scoped by changed paths, so it costs nothing off the PE tree."""
    module = _sync_module()
    calls: list[str] = []
    monkeypatch.setattr(module, "sync_pe_adapters", lambda root, wrote: calls.append("pe"))
    module.sync(ROOT, changed_paths={"README.md"}, pe_manifest=True)
    assert not calls
