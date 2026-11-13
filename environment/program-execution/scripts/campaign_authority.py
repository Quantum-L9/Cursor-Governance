"""Program Execution's standing authority, read from the Autonomy Surface Profile.

Program Execution consumes root autonomy; nothing in root autonomy, L4 or
publication consumes Program Execution. This module is the one place the
campaign runner reads the three things that connect it to that plane:

* the `campaign_execution` block of `ops/autonomy/surface_profile.yaml`, which
  is what authorizes a campaign to execute at all and names the stage in force;
* the operator's explicit invocation, which the `manual` stage requires for
  every run and which is recorded beside the campaign;
* the coding-agent execution projection, which the pipeline is bound to before
  a campaign is bootstrapped or resumed, through the same admitted binding and
  the same classifier SessionStart and `/coding-agent` use.

Everything here fails closed. An absent block, an unknown stage, a missing or
bare invocation, a lane policy above the profile's ceiling, or a projection
that does not verify as admitted and current executes nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

SURFACE_PROFILE = "ops/autonomy/surface_profile.yaml"
EXECUTION_PROFILE_RESOLVER = "ops/autonomy/execution_profile.py"
ROOT_AUTONOMY_PROVIDER = "root-autonomy-control-plane"

#: Stages at which the runner executes. `retired` is the absence of the block;
#: a stage this runner does not know is refused rather than guessed at.
EXECUTABLE_STAGES = frozenset({"manual", "registered"})
INVOCATION_MODE = "explicit_operator_only"
#: PROGRAM_EXECUTION_MAKE_PR_FINISH_V1: push and pull_request happen only inside
#: the governance SSOT `make pr` that campaign_publish.py runs.
PUBLISH_VIA = "via_make_pr_only"
PUBLICATION_ROUTE = "make_pr_ssot"
DEFAULT_INVOCATION_ENV = "L9_PE_OPERATOR_INVOCATION"
#: A flag is not a statement. The operator's own words are required.
BARE_FLAGS = frozenset({"1", "true", "yes", "on", "y", "ok", "enabled"})
MIN_STATEMENT_CHARS = 12

INVOCATION_SCHEMA = "l9.program-execution.operator-invocation.v1"
BINDING_SCHEMA = "l9.program-execution.coding-projection-binding.v1"
CODING_BINDING_SCHEMA = "l9.cursor-governance.coding-projection-binding/v3"
BOUND_STATUSES = frozenset({"CURRENT", "BOUND"})
ADMITTED = "ADMITTED_AND_CURRENT"
#: The session mode that must be on before a campaign is bound (projection_binding.required_mode).
REQUIRED_MODE = "coding-agent"
MODE_ACTIVE = "ACTIVE"
MODE_BINDING_SCHEMA = "l9.program-execution.coding-agent-mode-binding.v1"
#: The workspace whose `/coding-agent` session state counts; else the invoking cwd.
MODE_WORKSPACE_ENV = "L9_PE_MODE_WORKSPACE"
SSOT_ENV = "L9_GOVERNANCE_DIR"
SESSION_ENVS = ("CURSOR_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")


class CampaignAuthorityError(RuntimeError):
    """Program Execution may not execute; `code` says which condition refused it."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


# -- the profile block ------------------------------------------------------


def load_campaign_authority(governance_root: Path) -> dict[str, Any]:
    """The `campaign_execution` block, verified to be one this runner may act on."""
    path = governance_root / SURFACE_PROFILE
    try:
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CampaignAuthorityError(
            "SURFACE_PROFILE_UNREADABLE", f"cannot read {SURFACE_PROFILE}: {exc}"
        ) from exc
    block = profile.get("campaign_execution") if isinstance(profile, dict) else None
    if not isinstance(block, dict):
        raise CampaignAuthorityError(
            "CAMPAIGN_AUTHORITY_ABSENT",
            f"{SURFACE_PROFILE} carries no campaign_execution block; Program Execution is "
            "retired on this checkout and executes nothing",
        )
    stage = str(block.get("stage") or "")
    if stage not in EXECUTABLE_STAGES:
        raise CampaignAuthorityError(
            "CAMPAIGN_STAGE_NOT_EXECUTABLE",
            f"campaign_execution.stage is {stage!r}; this runner executes only at "
            f"{sorted(EXECUTABLE_STAGES)}",
        )
    if block.get("invocation") != INVOCATION_MODE:
        raise CampaignAuthorityError(
            "CAMPAIGN_INVOCATION_MODE_UNKNOWN",
            f"stage {stage!r} requires invocation: {INVOCATION_MODE}",
        )
    publication = block.get("publication")
    if (
        block.get("merge") != "forbidden"
        or any(block.get(action) != PUBLISH_VIA for action in ("push", "pull_request"))
        or not isinstance(publication, dict)
        or publication.get("route") != PUBLICATION_ROUTE
        or any(publication.get(raw) != "forbidden" for raw in ("raw_push", "raw_pull_request"))
    ):
        raise CampaignAuthorityError(
            "CAMPAIGN_AUTHORITY_WIDENED",
            f"campaign_execution must publish only {PUBLISH_VIA} (publication.route "
            f"{PUBLICATION_ROUTE}, raw push and raw pull_request forbidden) and keep merge "
            "forbidden; the runner holds no other publication authority",
        )
    autonomy = block.get("autonomy")
    if (
        not isinstance(autonomy, dict)
        or autonomy.get("provider") != ROOT_AUTONOMY_PROVIDER
        or autonomy.get("owns_program_state") is not False
    ):
        raise CampaignAuthorityError(
            "CAMPAIGN_AUTONOMY_PROVIDER_INVALID",
            f"campaign_execution.autonomy must name provider {ROOT_AUTONOMY_PROVIDER} with "
            "owns_program_state: false",
        )
    projection = block.get("projection_binding")
    if (
        not isinstance(projection, dict)
        or projection.get("required_mode") != REQUIRED_MODE
        or not projection.get("mode_runner")
    ):
        raise CampaignAuthorityError(
            "PROJECTION_MODE_UNDECLARED",
            "campaign_execution.projection_binding must require the operator's "
            f"/{REQUIRED_MODE} session mode (required_mode: {REQUIRED_MODE}, mode_runner); "
            "Program Execution binds the projection only while the operator has it on",
        )
    return dict(block)


# -- explicit operator invocation -------------------------------------------


def operator_invocation(
    authority: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """The operator's statement for this run, or a refusal.

    The `manual` stage has no standing invocation: every run of the runner
    carries the operator's own words. The statement is evidence, recorded with
    the campaign; it is not a credential, and holding the variable name is not
    permission to set it.
    """
    env = os.environ if environ is None else environ
    name = str(authority.get("invocation_evidence_env") or DEFAULT_INVOCATION_ENV)
    statement = str(env.get(name) or "").strip()
    if not statement:
        raise CampaignAuthorityError(
            "OPERATOR_INVOCATION_REQUIRED",
            f"Program Execution is at stage {authority.get('stage')!r}: it runs only when the "
            f"operator explicitly asks for it. Set {name} to the operator's own words for this "
            "run. An agent does not start a campaign on its own initiative.",
        )
    if statement.lower() in BARE_FLAGS or len(statement) < MIN_STATEMENT_CHARS:
        raise CampaignAuthorityError(
            "OPERATOR_INVOCATION_NOT_A_STATEMENT",
            f"{name} must carry the operator's instruction verbatim; a flag is not one",
        )
    session = next((env.get(key) for key in SESSION_ENVS if env.get(key)), None)
    return {
        "schema": INVOCATION_SCHEMA,
        "stage": authority.get("stage"),
        "invocation": authority.get("invocation"),
        "evidence_env": name,
        "statement": statement,
        "statement_digest": _digest_text(statement),
        "governance_surface": env.get("L9_GOVERNANCE_SURFACE") or None,
        "host_session_id": session,
        "recorded_at": _now(),
    }


def record_invocation(workspace: Path, invocation: Mapping[str, Any]) -> Path:
    """Append this run's invocation to the campaign's record; never rewrite one."""
    path = workspace / "runtime" / "INVOCATION.json"
    document: dict[str, Any] = {"schema": INVOCATION_SCHEMA + ".log", "invocations": []}
    if path.is_file():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CampaignAuthorityError(
                "INVOCATION_RECORD_UNREADABLE", f"cannot read {path}: {exc}"
            ) from exc
        if isinstance(prior, dict) and isinstance(prior.get("invocations"), list):
            document["invocations"] = list(prior["invocations"])
    document["invocations"].append(dict(invocation))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


# -- lane ceiling -----------------------------------------------------------


def lane_ceiling(
    governance_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """The lanes the autonomy profile grants the surface this runner is on."""
    resolver = governance_root / EXECUTION_PROFILE_RESOLVER
    spec = importlib.util.spec_from_file_location("pe_root_execution_profile", resolver)
    if spec is None or spec.loader is None:
        raise CampaignAuthorityError(
            "LANE_CEILING_UNRESOLVED", f"cannot load the execution profile resolver at {resolver}"
        )
    module = importlib.util.module_from_spec(spec)
    # The resolver imports its siblings by bare name, so its directory has to
    # be importable while it loads. It is appended, never prepended: nothing
    # Program Execution already resolves may change meaning because of it.
    sibling_root = str(resolver.parent)
    appended = sibling_root not in sys.path
    if appended:
        sys.path.append(sibling_root)
    try:
        spec.loader.exec_module(module)
        policy = module.load_policy(governance_root)
        name = module.classify(dict(os.environ if environ is None else environ), policy)
        profile = policy["profiles"][name]
        total = int(profile["max_parallel"])
        mutation = int(profile["max_mutation_lanes"])
    except (OSError, ImportError, KeyError, TypeError, ValueError) as exc:
        raise CampaignAuthorityError(
            "LANE_CEILING_UNRESOLVED", f"the autonomy execution profile is unreadable: {exc}"
        ) from exc
    finally:
        if appended and sibling_root in sys.path:
            sys.path.remove(sibling_root)
    return {"profile": name, "total_lanes": total, "mutation_lanes": mutation}


def narrowed_lanes(
    ceiling: Mapping[str, Any],
    *,
    total_lanes: int,
    mutation_lanes: int,
) -> tuple[int, int]:
    """Program Execution's lanes, refused when its policy exceeds the profile's."""
    if total_lanes > int(ceiling["total_lanes"]) or mutation_lanes > int(ceiling["mutation_lanes"]):
        raise CampaignAuthorityError(
            "LANE_POLICY_EXCEEDS_AUTONOMY_PROFILE",
            f"EXECUTION_CONCURRENCY_POLICY asks for {total_lanes} active / {mutation_lanes} "
            f"mutating dispatches; autonomy profile {ceiling['profile']!r} grants "
            f"{ceiling['total_lanes']} / {ceiling['mutation_lanes']}. Program Execution may "
            "narrow the profile's lanes, never exceed them.",
        )
    return total_lanes, mutation_lanes


# -- coding-agent execution projection --------------------------------------


def bind_coding_projection(
    governance_root: Path,
    authority: Mapping[str, Any],
    *,
    authority_root: Path | None = None,
) -> dict[str, Any]:
    """Bind the pipeline to the admitted coding-agent execution projection.

    Nothing is verified here. The binding the profile names declares its own
    status reader -- the shared classifier SessionStart reports and
    `/coding-agent` judges by -- and this runs it. The pipeline is bound only
    when the bundle verifies at the authority's main (CURRENT, or BOUND against
    the checkout's origin/main) and the admission decision admits the exact
    profile digest. Anything else executes nothing.
    """
    declared = authority.get("projection_binding")
    if not isinstance(declared, dict) or not declared.get("binding"):
        raise CampaignAuthorityError(
            "PROJECTION_BINDING_UNDECLARED",
            "campaign_execution.projection_binding names no binding",
        )
    binding_path = governance_root / str(declared["binding"])
    try:
        binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CampaignAuthorityError(
            "PROJECTION_BINDING_UNREADABLE", f"cannot read {binding_path}: {exc}"
        ) from exc
    if not isinstance(binding, dict) or binding.get("schema") != CODING_BINDING_SCHEMA:
        raise CampaignAuthorityError(
            "PROJECTION_BINDING_UNREADABLE",
            f"{declared['binding']} is not a {CODING_BINDING_SCHEMA} binding",
        )
    profile_ref = (binding.get("upstream") or {}).get("profile_ref")
    if profile_ref != declared.get("profile_ref"):
        raise CampaignAuthorityError(
            "PROJECTION_PROFILE_MISMATCH",
            f"the profile binds {declared.get('profile_ref')!r} but {declared['binding']} "
            f"declares {profile_ref!r}",
        )
    reader = (binding.get("verification") or {}).get("status_reader")
    bundle = (binding.get("bundle") or {}).get("path")
    lock_name = (binding.get("bundle") or {}).get("lock")
    if not reader or not bundle or not lock_name:
        raise CampaignAuthorityError(
            "PROJECTION_BINDING_UNREADABLE",
            f"{declared['binding']} names no status reader or bundle",
        )
    command = [
        sys.executable,
        str(governance_root / str(reader)),
        "--workspace",
        str(governance_root),
        "--format",
        "json",
    ]
    if authority_root is not None:
        command += ["--authority-root", str(authority_root)]
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        command, capture_output=True, text=True, check=False, timeout=120
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, dict) or not isinstance(report.get("status"), str):
        raise CampaignAuthorityError(
            "PROJECTION_VERIFIER_UNREADABLE",
            f"{reader} produced no status (exit {completed.returncode})",
        )
    status = report["status"]
    admission = (report.get("admission") or {}).get("status")
    if status not in BOUND_STATUSES:
        raise CampaignAuthorityError(
            "PROJECTION_NOT_BOUND",
            f"{profile_ref} is {status}: {report.get('detail')}. Program Execution is bound to "
            "this projection at bootstrap and does not run without it. Point L9_AUTHORITY_ROOT "
            "at a verified Quantum-L9/.github checkout whose HEAD is its main.",
        )
    if admission != ADMITTED:
        raise CampaignAuthorityError(
            "PROJECTION_ADMISSION_NOT_PROVED",
            f"{profile_ref} verifies as {status} but its admission is {admission!r}",
        )
    bundle_root = governance_root / str(bundle)
    lock_path = bundle_root / str(lock_name)
    views = sorted(path for path in (bundle_root / "projections").glob("*.projection.json"))
    if not lock_path.is_file() or not views:
        raise CampaignAuthorityError(
            "PROJECTION_BUNDLE_INCOMPLETE", f"{bundle} carries no lock or no projection views"
        )
    return {
        "schema": BINDING_SCHEMA,
        "profile_ref": profile_ref,
        "profile_digest": (binding.get("upstream") or {}).get("profile_digest"),
        "binding": str(declared["binding"]),
        "status": status,
        "admission": admission,
        "detail": report.get("detail"),
        "bundle_revision": report.get("bundle_revision"),
        "observed_main": report.get("observed_main"),
        "authority_root": report.get("authority_root"),
        "bundle_lock_digest": _digest_file(lock_path),
        "components": list(report.get("components") or []),
        "views": [
            {"path": str(path.relative_to(governance_root)), "digest": _digest_file(path)}
            for path in views
        ],
        "status_reader": str(reader),
        "bound_at": _now(),
    }


# -- /coding-agent, the session switch ----------------------------------------


def _mode_runner(runner: str, ssot: Path, workspace: Path) -> dict[str, Any]:
    """`coding_agent_mode.py status` as the operator ran it: the SSOT's, for this session."""
    python = ssot / ".venv" / "bin" / "python"
    command = [
        str(python) if python.is_file() else sys.executable,
        str(ssot / runner),
        "status",
        "--workspace",
        str(workspace),
    ]
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        command, capture_output=True, text=True, check=False, timeout=180, cwd=str(workspace)
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, dict) or not isinstance(report.get("mode"), str):
        raise CampaignAuthorityError(
            "CODING_AGENT_MODE_UNREADABLE",
            f"{runner} status produced no mode (exit {completed.returncode})",
        )
    return report


def coding_agent_mode(
    authority: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    status: Any = None,
) -> dict[str, Any]:
    """`/coding-agent` must be ACTIVE for the invoking session before PE binds.

    The operator's session switch is the one that turns the projection on: PE
    reads the same session state `/coding-agent status` reads
    (`.l9/coding-agent-mode/session.json` in the invoking workspace, bound to
    the host session id), through the SSOT's own mode command. OFF, BLOCKED,
    STALE or REJECTED executes nothing (CODING_AGENT_MODE_OFF). On ACTIVE it
    returns the mode's bundle revision and view digests so the caller can
    prove PE binds the same revision the session does.
    """
    declared = authority.get("projection_binding")
    if not isinstance(declared, Mapping) or declared.get("required_mode") != REQUIRED_MODE:
        raise CampaignAuthorityError(
            "PROJECTION_MODE_UNDECLARED",
            f"campaign_execution.projection_binding.required_mode must be {REQUIRED_MODE!r}",
        )
    runner = str(declared.get("mode_runner") or "")
    if not runner:
        raise CampaignAuthorityError(
            "PROJECTION_MODE_UNDECLARED", "projection_binding names no mode_runner"
        )
    env = os.environ if environ is None else environ
    workspace = Path(str(env.get(MODE_WORKSPACE_ENV) or os.getcwd())).expanduser().resolve()
    raw_ssot = str(env.get(SSOT_ENV) or "").strip()
    ssot = (Path(raw_ssot) if raw_ssot else Path.home() / ".cursor-governance").resolve()
    report = (status or _mode_runner)(runner, ssot, workspace)
    mode = str(report.get("mode") or "")
    if mode != MODE_ACTIVE:
        blockers = "; ".join(
            f"{item.get('ref')}: {item.get('reason')}" for item in report.get("blockers") or []
        )
        why = report.get("reason") or blockers or "no reason"
        raise CampaignAuthorityError(
            "CODING_AGENT_MODE_OFF",
            f"/coding-agent is {mode or 'unknown'} ({why}) "
            f"for this session in {workspace}. Program Execution binds the coding-agent "
            "execution projection only while the operator has it on: run /coding-agent on "
            f"in that workspace (or set {MODE_WORKSPACE_ENV} to the workspace where it is on).",
        )
    profile_ref = declared.get("profile_ref")
    loaded = [item for item in report.get("load") or [] if item.get("ref") == profile_ref]
    views = [Path(str(view)) for item in loaded for view in item.get("views") or []]
    if not views or not all(view.is_file() for view in views):
        raise CampaignAuthorityError(
            "CODING_AGENT_MODE_UNREADABLE",
            f"/coding-agent is ACTIVE but loads no readable {profile_ref} views",
        )
    lock = views[0].parent.parent / "bundle.lock.json"
    try:
        revision = (json.loads(lock.read_text(encoding="utf-8")).get("authority") or {}).get(
            "revision"
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignAuthorityError(
            "CODING_AGENT_MODE_UNREADABLE", f"cannot read the mode's bundle lock {lock}: {exc}"
        ) from exc
    return {
        "schema": MODE_BINDING_SCHEMA,
        "mode": MODE_ACTIVE,
        "workspace": str(workspace),
        "ssot": str(ssot),
        "requested_at": report.get("requested_at"),
        "profile_ref": profile_ref,
        "bundle_revision": revision,
        "views": [{"name": view.name, "digest": _digest_file(view)} for view in sorted(views)],
    }


def bind_with_mode(binding: Mapping[str, Any], mode: Mapping[str, Any]) -> dict[str, Any]:
    """PE's binding, with the session mode it agreed with; refused when they disagree."""
    if mode.get("bundle_revision") != binding.get("bundle_revision"):
        raise CampaignAuthorityError(
            "CODING_AGENT_MODE_MISMATCH",
            f"/coding-agent is bound at bundle {mode.get('bundle_revision')} but Program "
            f"Execution binds {binding.get('bundle_revision')}; one campaign runs under one "
            "revision of the execution contract",
        )
    ours = {Path(str(view["path"])).name: view["digest"] for view in binding.get("views") or []}
    theirs = {str(view["name"]): view["digest"] for view in mode.get("views") or []}
    if ours != theirs:
        differing = sorted(
            name for name in set(ours) | set(theirs) if ours.get(name) != theirs.get(name)
        )
        raise CampaignAuthorityError(
            "CODING_AGENT_MODE_MISMATCH",
            f"/coding-agent and Program Execution load different projection views: {differing}",
        )
    return {**dict(binding), "coding_agent_mode": dict(mode)}


def record_projection_binding(workspace: Path, binding: Mapping[str, Any]) -> Path:
    """Persist the bootstrap binding, or refuse a resume under a different bundle.

    A campaign runs under the projection it was bootstrapped with. If the
    bundle has been rebound since, the recorded evidence no longer describes
    what the pipeline is bound to, and continuing would mix two revisions of
    the execution contract in one campaign.
    """
    path = workspace / "runtime" / "coding-projection-binding.json"
    if path.is_file():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CampaignAuthorityError(
                "PROJECTION_BINDING_RECORD_UNREADABLE", f"cannot read {path}: {exc}"
            ) from exc
        recorded = (prior.get("bootstrap") or {}).get("bundle_lock_digest")
        if recorded != binding.get("bundle_lock_digest"):
            raise CampaignAuthorityError(
                "PROJECTION_BINDING_DRIFT",
                "this campaign was bootstrapped under projection bundle "
                f"{(prior.get('bootstrap') or {}).get('bundle_revision')} and the bundle is now "
                f"{binding.get('bundle_revision')}; a campaign is not resumed across a rebind",
            )
        document = dict(prior)
        document["verified"] = [*list(prior.get("verified") or []), dict(binding)]
    else:
        document = {
            "schema": BINDING_SCHEMA + ".record",
            "bootstrap": dict(binding),
            "verified": [],
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path
