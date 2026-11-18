#!/usr/bin/env python3
"""Project PLAN_DOCUMENT JSON into a Cursor .plan.md (shared template).

Keeps scripts/render_plan_markdown.py as the legacy GMP-section renderer.
Default for l9-plan is this projector + first-class SSOT
environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md
(skill references/executable-plan.pe-autonomy.template.md is a symlink).

--execute-via=pe-campaign (default) keeps the PE execute block.
--execute-via=cursor-build swaps that block for Cursor Build (l9-plan-simple).
--execute-via=embedded swaps it for a caller-owned handoff that authorizes no
execution at all (l9-plan-simple embedded mode, for callers that own their own
downstream realization).

One projection axis, one template, one validator: a mode is a `_Projection`
row, never a second renderer.

The template owns section order and headings; this projector owns every
section body, filled from PLAN_DOCUMENT. A value PLAN_DOCUMENT does not carry
is rendered as an explicit `unknown — …` / `unbound — …` marker, never as a
template `<parameter>` and never as an invented default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paths import safe_cli_path

EXECUTE_VIA_PE = "pe-campaign"
EXECUTE_VIA_BUILD = "cursor-build"
EXECUTE_VIA_EMBEDDED = "embedded"
EXECUTE_VIA_CHOICES = (EXECUTE_VIA_PE, EXECUTE_VIA_BUILD, EXECUTE_VIA_EMBEDDED)

BUILD_EXECUTE_SECTION = """## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.
"""

EMBEDDED_EXECUTE_SECTION = """## Handoff to Caller

This document is **validated planning evidence**. Embedded mode terminates here and returns control to the invoking caller.

- The `PLAN_DOCUMENT` behind this projection PASSed `validate_plan_document.py`.
- This markdown is that document's validated projection — a planning artifact, not a run instruction.
- The **caller** owns everything downstream: branch selection, worktree, mutation, verification, publication, and release.
- The caller MUST establish and enforce its own execution authority before acting on this plan. Embedded planning confers none of it.
- Embedded mode grants **no** mutation authority, **no** commit authority, **no** publication or pull-request authority, **no** campaign or Program Execution authority, **no** phased-execution-protocol authority, and **no** deployment authority.
- Nothing in this document authorizes an executor to act on it.

**Intended callers:** nested skills, pre-birth and repository-birth workflows, orchestration pipelines, and any system that needs L9 planning depth while owning downstream realization itself.
"""

_PE_EXECUTE_HEADING = "Execute via @environment/program-execution + subordinate @autonomy"
_PE_NEXT_ACTION = (
    "| minimum_safe_next_action | When law holds and status=`executable`, attach "
    "[@environment/program-execution](environment/program-execution/) + "
    "[@autonomy](commands/autonomy.md); project→Lock→claim→render→autonomy lanes — "
    "do not free-form execute |"
)
_PE_CONVERGENCE_VIA = (
    "| execute_via | `@environment/program-execution` → Program Lock/Controller → "
    "`@autonomy` (`/autonomy` → `l9-bounded-autonomy`) under Program lease → PE adapter |"
)


@dataclass(frozen=True)
class _Projection:
    """One handoff mode's projection directives.

    `execute_section is None` means "leave the template's own PE execute
    authority in place" — that is the pe-campaign identity row.
    """

    kind: str
    execute_via: str
    executor: str
    execute_section: str | None = None
    section_heading_swap: str | None = None
    execute_blockquote: str | None = None
    todos_blockquote: str | None = None
    next_action_row: str | None = None
    convergence_via_row: str | None = None
    machine_stub: str | None = None
    next_skill: str | None = None


_BUILD_EXECUTE_BLURB = (
    "> **Execute:** when status is `executable`, press **Build**, stack on the "
    "unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), "
    "then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** "
    "run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone."
)
_BUILD_TODOS_BLURB = (
    "> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract."
)
_BUILD_NEXT_ACTION = (
    "| minimum_safe_next_action | When law holds and status=`executable`, "
    "press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` "
    "and display the PR URL — do not free-form execute |"
)
_BUILD_CONVERGENCE_VIA = (
    "| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |"
)
_BUILD_MACHINE_STUB = """execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
"""

_EMBEDDED_EXECUTE_BLURB = (
    "> **Execute:** nothing here executes. When status is `executable` this document is "
    "validated planning evidence handed back to the invoking caller, which owns branch, "
    "mutation, publication and release authority under its own contract. Do **not** "
    "free-form mutate from this markdown alone."
)
_EMBEDDED_TODOS_BLURB = (
    "> **Cursor todos:** frontmatter `todos` are the caller's task decomposition, not a "
    "live execution queue. Body is the binding contract."
)
_EMBEDDED_NEXT_ACTION = (
    "| minimum_safe_next_action | When law holds and status=`executable`, return this "
    "validated plan to the invoking caller — embedded mode authorizes no mutation, "
    "publication, or release |"
)
_EMBEDDED_CONVERGENCE_VIA = (
    "| execute_via | Embedded handoff; caller-owned execution; no mutation or "
    "publication authority granted here |"
)
_EMBEDDED_MACHINE_STUB = """execute_via:
  pipeline: embedded
  mention_program: "caller-owned handoff"
  command_ref: none
  authority_order:
    - plan_document
    - invoking_caller
"""

PROJECTIONS: dict[str, _Projection] = {
    EXECUTE_VIA_PE: _Projection(
        kind="pe",
        execute_via=EXECUTE_VIA_PE,
        executor="program-execution controller",
    ),
    EXECUTE_VIA_BUILD: _Projection(
        kind="simple",
        execute_via=EXECUTE_VIA_BUILD,
        executor="Cursor Build agent",
        execute_section=BUILD_EXECUTE_SECTION,
        section_heading_swap="Execute via Cursor Build; stacked make pr if any open PR exists",
        execute_blockquote=_BUILD_EXECUTE_BLURB,
        todos_blockquote=_BUILD_TODOS_BLURB,
        next_action_row=_BUILD_NEXT_ACTION,
        convergence_via_row=_BUILD_CONVERGENCE_VIA,
        machine_stub=_BUILD_MACHINE_STUB,
        next_skill="Build then stacked make pr",
    ),
    EXECUTE_VIA_EMBEDDED: _Projection(
        kind="simple",
        execute_via=EXECUTE_VIA_EMBEDDED,
        executor="invoking caller",
        execute_section=EMBEDDED_EXECUTE_SECTION,
        section_heading_swap="Handoff to the invoking caller; no execution authority",
        execute_blockquote=_EMBEDDED_EXECUTE_BLURB,
        todos_blockquote=_EMBEDDED_TODOS_BLURB,
        next_action_row=_EMBEDDED_NEXT_ACTION,
        convergence_via_row=_EMBEDDED_CONVERGENCE_VIA,
        machine_stub=_EMBEDDED_MACHINE_STUB,
        next_skill="caller-owned handoff (no execution authorized here)",
    ),
}

# Skill path is a symlink; prefer resolving the first-class git SSOT.
TEMPLATE_REL = Path("references/executable-plan.pe-autonomy.template.md")
SSOT_REL = Path(
    "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
)

NOT_DECLARED = "unknown — not declared in PLAN_DOCUMENT; resolve before status `executable`"
UNBOUND = "unbound — re-render with `--workspace .` from the repo root, or bind at execution start"

_VALIDATION_STATUS = {"pending": "not_run", "passed": "passed", "failed": "failed"}
_RISK_LEVEL = {"low": "low", "medium": "medium", "high": "high", "irreversible": "critical"}
_LEVELS = ("low", "medium", "high", "critical")
# PLAN_DOCUMENT convergence is *planning* convergence; map it onto the
# template's execution lifecycle without claiming execution happened.
# Readiness is derived, never copied: planning convergence alone does not make
# a plan executable while a success property cannot be proved or an unknown
# still blocks (see _Ctx.readiness_blockers).
_CONVERGENCE_STATE = {
    "executable": "execution_ready",
    "draft": "draft",
    "preflight_blocked": "preflight_blocked",
}
_NEXT_GATE = {
    "executable": "complete_when",
    "draft": "executable_when",
    "preflight_blocked": "blocking_conditions",
}
_UNRUNNABLE = {"skipped", "not_applicable"}
_BLOCKING_RESOLUTIONS = {"block", "ask"}


def projection_for(execute_via: str) -> _Projection:
    try:
        return PROJECTIONS[execute_via]
    except KeyError:
        raise SystemExit(f"unknown --execute-via: {execute_via}") from None


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "plan").strip().lower()).strip("_")
    return cleaned or "plan"


def _hex8(plan: dict) -> str:
    raw = json.dumps(plan, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:8]


def _todo_rows(plan: dict) -> list[dict]:
    rows: list[dict] = []
    for t in plan.get("todos") or []:
        tid = str(t.get("id") or "todo")
        content = str(t.get("task") or t.get("content") or tid)
        deps = t.get("dependencies") or t.get("depends_on") or []
        if not isinstance(deps, list):
            deps = []
        rows.append(
            {
                "id": tid,
                "content": content,
                "status": "pending",
                "depends_on": [str(d) for d in deps],
                "phase": str(t.get("phase") or "execute"),
            }
        )
    return rows


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def _frontmatter(plan: dict, execute_via: str = EXECUTE_VIA_PE) -> str:
    prof = projection_for(execute_via)
    title = str(plan.get("title") or "Untitled plan")
    overview = str(plan.get("objective") or title).replace("\n", " ").strip()
    if len(overview) > 400:
        overview = overview[:397] + "..."
    todos = _todo_rows(plan)
    # Every free-text scalar goes through _yaml_scalar (a JSON string, which is
    # valid YAML). An unquoted `name:` broke the whole frontmatter for any title
    # containing ": " or a leading YAML indicator; the receipt then fell back to
    # a line parser and reported a misleading `todos` failure.
    lines = [
        "---",
        f"name: {_yaml_scalar(title)}",
        f"overview: {_yaml_scalar(overview)}",
        "todos:",
    ]
    if not todos:
        lines.append("  []")
    for t in todos:
        lines.append(f"  - id: {t['id']}")
        lines.append(f"    content: {_yaml_scalar(t['content'])}")
        lines.append("    status: pending")
        lines.append(f"    phase: {t['phase']}")
        lines.append(f"    depends_on: {_yaml_list(t['depends_on'])}")
    lines.append("isProject: false")
    lines.append(f"kind: {prof.kind}")
    lines.append(f"execute_via: {prof.execute_via}")
    lines.append("status: current")
    lines.append("---")
    return "\n".join(lines)


def _rewrite_pe_directives(body: str, prof: _Projection) -> str:
    """Omit live PE-only run-path directives from a non-PE projection."""
    if prof.execute_blockquote:
        body = re.sub(
            r"^> \*\*Execute:\*\* when status is `executable`, run through \*\*\[@environment/program-execution\].*$",
            lambda _m: prof.execute_blockquote or "",
            body,
            count=1,
            flags=re.M,
        )
    if prof.todos_blockquote:
        body = re.sub(
            r"^> \*\*Cursor todos:\*\* frontmatter `todos` project to PE Task Cards.*$",
            lambda _m: prof.todos_blockquote or "",
            body,
            count=1,
            flags=re.M,
        )
    if prof.next_action_row:
        body = body.replace(_PE_NEXT_ACTION, prof.next_action_row)
    if prof.convergence_via_row:
        body = body.replace(_PE_CONVERGENCE_VIA, prof.convergence_via_row)
    if prof.machine_stub:
        body = re.sub(
            r"execute_via:\n(?:  .+\n)+",
            lambda _m: prof.machine_stub or "",
            body,
            count=1,
        )
    return body


def _swap_execute_block(body: str, execute_via: str) -> str:
    prof = projection_for(execute_via)
    if prof.execute_section is None:
        return body
    pattern = re.compile(
        r"^## Execute via @environment/program-execution \+ autonomy.*?(?=^## |\Z)",
        re.M | re.S,
    )
    swapped, n = pattern.subn(prof.execute_section.rstrip() + "\n\n", body, count=1)
    if not n:
        swapped = prof.execute_section.rstrip() + "\n\n" + body
    if prof.section_heading_swap:
        swapped = swapped.replace(_PE_EXECUTE_HEADING, prof.section_heading_swap)
    return _rewrite_pe_directives(swapped, prof)


# --------------------------------------------------------------------------
# Workspace baseline (opt-in, read-only git probes)
# --------------------------------------------------------------------------


def _git(workspace: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(workspace), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def bind_workspace(workspace: Path) -> dict[str, str]:
    """Observe the current workspace baseline. Never mutates the repository."""
    top = _git(workspace, "rev-parse", "--show-toplevel")
    if top is None:
        raise SystemExit(f"--workspace is not a git work tree: {workspace}")
    sha = _git(workspace, "rev-parse", "HEAD") or ""
    branch = _git(workspace, "rev-parse", "--abbrev-ref", "HEAD") or ""
    porcelain = _git(workspace, "status", "--porcelain")
    remote = _git(workspace, "config", "--get", "remote.origin.url") or ""
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", remote)
    return {
        "captured_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "repository": match.group(1) if match else Path(top).name,
        "workspace": top,
        "branch": branch or "unknown — detached or unborn HEAD",
        "commit_sha": sha or "unknown — no HEAD commit",
        "dirty": "unknown" if porcelain is None else ("true" if porcelain else "false"),
    }


# --------------------------------------------------------------------------
# Section bodies, filled from PLAN_DOCUMENT
# --------------------------------------------------------------------------


def _cell(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text.replace("\n", " ").replace("|", "\\|").strip() or "—"


def _code(value: Any) -> str:
    text = _cell(value)
    return f"`{text}`" if "`" not in text else text


def _join(items: list[str], empty: str) -> str:
    cleaned = [str(i) for i in items if str(i).strip()]
    return ", ".join(_code(i) for i in cleaned) if cleaned else empty


def _declared(value: Any) -> str:
    """Project a PLAN_DOCUMENT value; absent stays the explicit NOT_DECLARED marker.

    A list renders as code items (`none` when empty — declared empty is not
    absent); a bool renders `true`/`false`; a scalar renders as code.
    """
    if value is None:
        return NOT_DECLARED
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, list):
        return _join([str(v) for v in value], "none")
    return _code(value)


def _bullets(items: list[str], empty: str) -> list[str]:
    cleaned = [str(i) for i in items if str(i).strip()]
    return [f"- {i}" for i in cleaned] if cleaned else [f"- {empty}"]


_IDENT_RE = re.compile(r"[A-Za-z0-9_.\-/]+")


def _ident_tokens(text: str) -> set[str]:
    """File/script-like identifiers (contain `.` or `_`), compared by basename."""
    out: set[str] = set()
    for tok in _IDENT_RE.findall(text or ""):
        base = tok.rstrip(".,;:-/").rsplit("/", 1)[-1]
        if len(base) >= 4 and re.search(r"[A-Za-z0-9][._][A-Za-z0-9]", base):
            out.add(base.lower())
    return out


@dataclass(frozen=True)
class _Property:
    sp_id: str
    text: str
    validation_ids: tuple[str, ...]


class _Ctx:
    def __init__(
        self,
        plan: dict,
        prof: _Projection,
        template_body: str,
        baseline: dict[str, str] | None,
    ) -> None:
        self.plan = plan
        self.prof = prof
        self.template_body = template_body
        self.baseline = baseline
        self.title = str(plan.get("title") or "Untitled plan")
        self.slug = _slug(self.title)
        self.plan_id = f"plan.{prof.kind}.{self.slug}.v1"
        self.filename = f"{self.slug}_{_hex8(plan)}.plan.md"
        self.todos: list[dict] = [t for t in plan.get("todos") or [] if isinstance(t, dict)]
        self.conv: dict = plan.get("convergence") or {}
        self.stress: dict = plan.get("stress_test") or {}
        self.gmp: dict = plan.get("gmp_handoff") or {}
        envelope: dict = plan.get("execution_envelope") or {}
        self.network: dict = envelope.get("network") or {}
        self.secrets: dict = envelope.get("secrets") or {}
        self.complexity: dict = plan.get("complexity") or {}
        self.validations: list[dict] = [
            v for v in plan.get("final_validation") or [] if isinstance(v, dict)
        ]
        self.properties = self._link_properties()

    def _link_properties(self) -> list[_Property]:
        """Bind each success criterion to the final_validation entries that prove it.

        A criterion is proved by a validation when it names that validation's
        id, or shares a file/script identifier with its command or pass
        criteria. No link is invented: an unmatched criterion stays unbound.
        """
        linked: list[_Property] = []
        for i, crit in enumerate(self.plan.get("success_criteria") or [], start=1):
            text = str(crit)
            tokens = _ident_tokens(text)
            hits: list[str] = []
            for v in self.validations:
                vid = str(v.get("id") or "")
                named = bool(vid) and re.search(rf"(?<![\w.-]){re.escape(vid)}(?![\w-])", text)
                shared = tokens & _ident_tokens(
                    f"{v.get('command') or ''} {v.get('pass_criteria') or ''}"
                )
                if named or shared:
                    hits.append(vid)
            linked.append(_Property(f"SP-{i:02d}", text, tuple(hits)))
        return linked

    def validation(self, vid: str) -> dict:
        return next((v for v in self.validations if str(v.get("id")) == vid), {})

    @property
    def max_risk(self) -> str:
        levels = [_RISK_LEVEL.get(str(t.get("risk")), "low") for t in self.todos]
        return max(levels, key=_LEVELS.index) if levels else "low"

    @property
    def conv_status(self) -> str:
        return str(self.conv.get("status") or "partial")

    def unprovable_properties(self) -> list[str]:
        """Properties with no proving validation, or only skipped / not_applicable ones."""
        out: list[str] = []
        for prop in self.properties:
            statuses = {str(self.validation(v).get("status") or "") for v in prop.validation_ids}
            if not prop.validation_ids or statuses <= _UNRUNNABLE:
                out.append(prop.sp_id)
        return out

    def readiness_blockers(self) -> list[str]:
        """Why the plan may not become `executable`; empty means it may."""
        out: list[str] = []
        if self.conv_status != "converged":
            out.append(f"planning convergence is `{self.conv_status}`")
        remaining = [str(x) for x in self.conv.get("remaining_unknown_ids") or []]
        if remaining:
            out.append("remaining unknowns: " + ", ".join(remaining))
        blocking = [
            str(u.get("id"))
            for u in self.plan.get("unknowns") or []
            if u.get("resolution") in _BLOCKING_RESOLUTIONS
        ]
        if blocking:
            out.append("blocking unknowns: " + ", ".join(blocking))
        unprovable = self.unprovable_properties()
        if unprovable:
            out.append("unprovable success properties: " + ", ".join(unprovable))
        return out

    @property
    def plan_status(self) -> str:
        if self.conv_status == "blocked":
            return "preflight_blocked"
        return "draft" if self.readiness_blockers() else "executable"

    def baseline_value(self, key: str) -> str:
        if self.baseline is None:
            return UNBOUND
        return self.baseline.get(key) or UNBOUND


def _sec_metadata(c: _Ctx) -> list[str]:
    created = c.baseline_value("captured_at")
    return [
        "| Field | Value |",
        "|-------|-------|",
        f"| plan_id | `{c.plan_id}` |",
        f"| name | {_cell(c.title)} |",
        f"| overview | {_cell(c.plan.get('objective') or c.title)} |",
        f"| schema_version | `{_cell(c.plan.get('schema_version') or '1.0.0')}` |",
        (
            f"| status | `{c.plan_status}` — "
            + ("; ".join(c.readiness_blockers()) or "every readiness gate in PLAN_DOCUMENT holds")
            + " |"
        ),
        "| is_project | `false` |",
        f"| owner | {_cell(c.plan.get('owner') or NOT_DECLARED)} |",
        f"| created_at | {created} |",
        f"| updated_at | {created} |",
        f"| depth | `{_cell(c.plan.get('depth') or 'standard')}` |",
        f"| estimate | {_cell(c.plan.get('estimate') or NOT_DECLARED)} |",
    ]


def _sec_framing(c: _Ctx) -> list[str]:
    via = c.prof.section_heading_swap or _PE_EXECUTE_HEADING
    return [
        "| Field | Value |",
        "|-------|-------|",
        "| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |",
        f"| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `{_cell(c.plan.get('mode') or 'plan')}` |",
        "| redesign_allowed | `false` |",
        "| follow_on_schema_evolution_separate | `true` |",
        f"| framing_notes | {via}; no redesign unless plan_class requires it |",
    ]


def _sec_baseline(c: _Ctx) -> list[str]:
    rows = [
        "| Field | Value |",
        "|-------|-------|",
    ]
    for key in ("captured_at", "repository", "workspace", "branch", "commit_sha", "dirty"):
        rows.append(f"| {key} | {_code(c.baseline_value(key)) if c.baseline else UNBOUND} |")
    rows += [
        "| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |",
        "| allowed_local_dirt | none |",
        "| overlap_policy | `stop_if_dirty_overlaps_may_modify` |",
        "| verification_rule | `reverify_at_execution_start` |",
        "| on_drift | `stop_and_replan` |",
    ]
    return rows


def _sec_objective(c: _Ctx) -> list[str]:
    scope = c.plan.get("scope") or {}
    lines = [
        "### Mission",
        "",
        str(c.plan.get("objective") or NOT_DECLARED),
        "",
        "### Scope in",
        "",
        *_bullets(scope.get("in") or [], NOT_DECLARED),
        "",
        "### Success properties",
        "",
        (
            "Each property's proof is the `final_validation` entry it names (by id or by "
            "script/file). A property with no proving validation, or only skipped / "
            "not_applicable ones, blocks `executable`."
        ),
        "",
        "| id | property | evidence_type | proof | blocking |",
        "|----|----------|---------------|-------|----------|",
    ]
    for prop in c.properties:
        if prop.validation_ids:
            proofs = []
            for vid in prop.validation_ids:
                v = c.validation(vid)
                proofs.append(
                    f"{vid}: {_code(v.get('command') or '')} → {_cell(v.get('pass_criteria') or '')}"
                )
            lines.append(
                f"| {prop.sp_id} | {_cell(prop.text)} | `quality_gate` | {'; '.join(proofs)} | `true` |"
            )
        else:
            lines.append(
                f"| {prop.sp_id} | {_cell(prop.text)} | unbound | unbound — no "
                "`final_validation` entry names this property; add one before status "
                "`executable` | `true` |"
            )
    return lines


def _sec_preflight(c: _Ctx) -> list[str]:
    verified = "`false` — reverify at execution start"
    lines = [
        "`schema_ref:` `canonical.schema.capability_preflight.v1`",
        f"`instance_binding:` `capability_preflight_ref` → `preflight.{c.plan_id}`",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| preflight_id | `preflight.{c.plan_id}` |",
        f"| source_ref | `{c.plan_id}` |",
        "| phase_id | `preflight` |",
        "| blocking | `true` |",
        f"| immutable_baseline_ref | `baseline.{c.plan_id}` |",
        f"| baseline_verified | {verified} |",
        f"| drift_detected | {'`false` — baseline captured at render' if c.baseline else UNBOUND} |",
        "",
        "### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)",
        "",
        "| id | capability | command_or_action | pass_criteria | blocking |",
        "|----|------------|-------------------|---------------|----------|",
    ]
    for p in c.plan.get("pre_validation") or []:
        lines.append(
            f"| {_cell(p.get('id'))} | pre-validation (status `{_cell(p.get('status'))}`) | "
            f"{_code(p.get('command_or_action') or '')} | {_cell(p.get('pass_criteria'))} | `true` |"
        )
    return lines


def _todo_files(c: _Ctx, op: str | None = None) -> list[str]:
    out: list[str] = []
    for t in c.todos:
        if op is None or t.get("operation") == op:
            out.extend(str(f) for f in t.get("files") or [])
    return out


def _commands(c: _Ctx) -> list[str]:
    seen: list[str] = []
    for cmd in [*(c.gmp.get("validation_commands") or [])] + [
        str(v.get("command") or "") for v in c.validations
    ]:
        if cmd and cmd not in seen:
            seen.append(cmd)
    return seen


def _sec_envelope(c: _Ctx) -> list[str]:
    deletes = _todo_files(c, "Delete")
    return [
        "Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).",
        "",
        "### Filesystem",
        "",
        f"- **write_allow:** {_join(c.gmp.get('may_modify') or _todo_files(c), NOT_DECLARED)}",
        f"- **write_deny:** {_join(c.gmp.get('must_not_modify') or [], 'none declared')}",
        f"- **delete_allow:** {_join(deletes, 'none — no Delete todo')}",
        "",
        "### Commands",
        "",
        f"- **allow:** {_join(_commands(c), NOT_DECLARED)}",
        "- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets",
        "",
        "### Network",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| mode | {_declared(c.network.get('mode'))} |",
        f"| allowed_services | {_declared(c.network.get('allowed_services'))} |",
        "",
        "### Secrets",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| access | {_declared(c.secrets.get('access'))} |",
        "| redaction_required | `true` |",
        "",
        "### Autonomous merge",
        "",
        "`autonomous_merge:` `false` always. This plan confers no merge authority.",
        "",
        "### Preserved contracts",
        "",
        *_bullets(c.gmp.get("preserved_contracts") or [], "none declared"),
    ]


def _side_effect_row(t: dict) -> tuple[str, str, str, str, str]:
    op = str(t.get("operation") or "")
    risk = str(t.get("risk") or "low")
    files = [str(f) for f in t.get("files") or []]
    if not files:
        effects = "none"
    elif op == "Delete":
        effects = "destructive_filesystem_mutation"
    else:
        effects = "filesystem_mutation"
    if risk == "irreversible":
        idem, retry = "non_idempotent", "manual_only"
    elif op == "Delete":
        idem, retry = "unsafe_blind_repeat", "manual_only"
    else:
        idem, retry = "safe_with_dedupe", "retry_once"
    comp = f"`git restore -- {' '.join(files)}`" if files else "none"
    return effects, idem, retry, comp, "true" if risk == "irreversible" else "false"


def _sec_side_effects(c: _Ctx) -> list[str]:
    lines = [
        "Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.",
        "",
        "| todo_id | side_effects | idempotency | retry | compensation | irreversible |",
        "|---------|--------------|-------------|-------|--------------|--------------|",
    ]
    for t in c.todos:
        effects, idem, retry, comp, irr = _side_effect_row(t)
        lines.append(
            f"| {_cell(t.get('id'))} | `{effects}` | `{idem}` | `{retry}` | {comp} | `{irr}` |"
        )
    return lines


def _common_dir(files: list[str]) -> str:
    parts = [Path(f).parts[:-1] for f in files if f]
    if not parts:
        return ""
    common: list[str] = []
    for segs in zip(*parts, strict=False):
        if len(set(segs)) != 1:
            break
        common.append(segs[0])
    return "/".join(common) or "repository root"


def _sec_architecture(c: _Ctx) -> list[str]:
    contracts = _join(c.gmp.get("preserved_contracts") or [], "none declared")
    prohibited = _join(c.gmp.get("must_not_modify") or [], "none declared")
    lines = [
        "| todo_id | bounded_context | layer | owning_contract | prohibited |",
        "|---------|-----------------|-------|-----------------|------------|",
    ]
    for t in c.todos:
        files = [str(f) for f in t.get("files") or []]
        ctx = _common_dir(files) if files else f"blocked: {_cell(t.get('blocker') or 'no files')}"
        lines.append(
            f"| {_cell(t.get('id'))} | {_code(ctx)} | {_declared(t.get('layer'))} | {contracts} | "
            f"{prohibited} |"
        )
    return lines


def _sec_rollback(c: _Ctx) -> list[str]:
    rollback = str(c.stress.get("rollback") or "").strip()
    irreversible = [t for t in c.todos if t.get("risk") == "irreversible"]
    deletes = _todo_files(c, "Delete")
    checkpoints = [
        f"{_cell(cp.get('id'))} fails ({_cell(cp.get('evidence_required'))}) → "
        + f"{_cell(cp.get('no_go_action'))}"
        for cp in c.plan.get("checkpoints") or []
    ]
    code_mode = "git_restore_scoped_paths" if _todo_files(c) else "none"
    return [
        "`schema_ref:` `canonical.schema.rollback_contract.v1`",
        f"`instance_binding:` `rollback_contract_ref` → `rollback.{c.plan_id}`",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| rollback_id | `rollback.{c.plan_id}` |",
        f"| source_execution_ref | `{c.plan_id}` |",
        f"| supported | `{'true' if rollback else 'false'}` |",
        "| automatic_allowed | `false` |",
        f"| approval_required | `{'true' if irreversible or deletes else 'false'}` |",
        f"| trigger_conditions | {'; '.join(checkpoints) or 'any blocking final_validation fails'} |",
        "",
        "### Strategies (typed — PLAN-SCHEMA-009)",
        "",
        "| domain | mode | notes |",
        "|--------|------|-------|",
        f"| code | `{code_mode}` | {_cell(rollback or NOT_DECLARED)} |",
        "| data | `none` | PLAN_DOCUMENT declares no data mutation |",
        "| external_state | `none` | PLAN_DOCUMENT declares no external write |",
        f"| local_state | `{code_mode}` | scoped to todo files |",
        "",
        "### Irreversible operations",
        "",
        *_bullets(
            [f"{t.get('id')}: {t.get('task')}" for t in irreversible],
            "none — no todo is marked `irreversible` (PLAN-SCHEMA-010)",
        ),
        "",
        "### Rollback verification",
        "",
        *_bullets(
            [f"re-run `{cmd}`" for cmd in _commands(c)],
            "re-run the final validation set",
        ),
    ]


def _sec_complexity(c: _Ctx) -> list[str]:
    unknowns = c.plan.get("unknowns") or []
    blocking = [u for u in unknowns if u.get("resolution") in {"block", "ask"}]
    uncertainty = "high" if blocking else ("medium" if unknowns else "low")
    return [
        "| Field | Value |",
        "|-------|-------|",
        f"| complexity | `{c.max_risk}` — highest todo risk across {len(c.todos)} todo(s) |",
        f"| uncertainty | `{uncertainty}` — {len(unknowns)} unknown(s), {len(blocking)} blocking |",
        f"| blast_radius | `{c.max_risk}` — {_cell(c.stress.get('blast_radius') or NOT_DECLARED)} |",
        (
            "| architectural_boundaries_crossed | "
            f"{_declared(c.complexity.get('architectural_boundaries_crossed'))} |"
        ),
        f"| external_systems_touched | {_declared(c.complexity.get('external_systems_touched'))} |",
        f"| migration_required | {_declared(c.complexity.get('migration_required'))} |",
        f"| unknown_dependency_count | `{len(unknowns)}` |",
    ]


def _not_activated(what: str) -> list[str]:
    return [f"Not activated — PLAN_DOCUMENT declares no {what}."]


def _sec_gated_write(c: _Ctx) -> list[str]:
    irreversible = [str(t.get("id")) for t in c.todos if t.get("risk") == "irreversible"]
    if not irreversible:
        return _not_activated("irreversible or external write")
    ids = ", ".join(irreversible)
    return [
        f"Activated — irreversible todo(s): {ids}.",
        "",
        "- **gates (ordered):**",
        f"  1. human approval recorded for {ids} before any of them runs",
        "  2. every blocking capability probe and earlier checkpoint has passed",
        "  3. the exact write is previewed (dry run or diff) and reviewed",
        "  4. the write executes once",
        "  5. a receipt of the write is recorded before the next todo starts",
        "- **dedupe_before_non_idempotent_write:** `true`",
        f"- **bounded_write_count:** `{len(irreversible)}` — one attempt per irreversible "
        + "todo; retry is `manual_only`",
        "- **receipt_required:** `true`",
    ]


def _sec_dag(c: _Ctx) -> list[str]:
    lev = c.plan.get("leverage") or {}
    lines = [
        "`schema_ref:` `canonical.schema.dependency_topology.v1`",
        f"`instance_binding:` `dependency_topology_ref` → `dag.{c.plan_id}`",
        "Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| topology_id | `dag.{c.plan_id}` |",
        "| topology_kind | `execution` |",
        "| graph_type | `directed_acyclic_graph` |",
        "",
        "### Nodes / edges",
        "",
        "| id | task | owner | risk | effort | depends_on | outputs |",
        "|----|------|-------|------|--------|------------|---------|",
    ]
    for t in c.todos:
        deps = [str(d) for d in t.get("dependencies") or []]
        files = [str(f) for f in t.get("files") or []]
        outputs = _join(files, f"blocked: {_cell(t.get('blocker') or 'no files')}")
        lines.append(
            f"| {_cell(t.get('id'))} | {_cell(t.get('task'))} | {c.prof.executor} | "
            f"`{_cell(t.get('risk'))}` | {_cell(t.get('effort'))} | "
            f"`{_yaml_list(deps)}` | {outputs} |"
        )
    critical = " → ".join(str(x) for x in c.plan.get("critical_path") or [])
    lines += [
        "",
        f"**Critical path:** {critical or NOT_DECLARED}",
        "",
        "**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.",
        "",
        "### Milestones",
        "",
        "| id | outcome | unlocks |",
        "|----|---------|---------|",
        *[
            f"| {_cell(m.get('id'))} | {_cell(m.get('outcome'))} | {_cell(m.get('unlocks'))} |"
            for m in c.plan.get("milestones") or []
        ],
        "",
        "### Checkpoints",
        "",
        "| id | after | evidence_required | no_go_action |",
        "|----|-------|-------------------|--------------|",
        *[
            f"| {_cell(cp.get('id'))} | {_cell(cp.get('after'))} | "
            + f"{_cell(cp.get('evidence_required'))} | {_cell(cp.get('no_go_action'))} |"
            for cp in c.plan.get("checkpoints") or []
        ],
        "",
        "### Leverage",
        "",
        f"- **Ranked todos:** {_join(lev.get('ranked_todo_ids') or [], NOT_DECLARED)}",
        f"- **Shared causes:** {'; '.join(str(x) for x in lev.get('shared_causes') or []) or 'none declared'}",
        "- **Deletions / consolidations:** "
        + f"{'; '.join(str(x) for x in lev.get('deletions_or_consolidations') or []) or 'none declared'}",
        "",
        "### Doc / root surface impact",
        "",
        "| surface | action | todo_ids | reason |",
        "|---------|--------|----------|--------|",
        *[
            f"| {_cell(d.get('surface'))} | `{_cell(d.get('action'))}` | "
            + f"{_join(d.get('todo_ids') or [], '—')} | {_cell(d.get('reason') or '—')} |"
            for d in c.plan.get("doc_root_surface_impact") or []
        ],
    ]
    return lines


def _evidence_rows(c: _Ctx) -> list[tuple[str, str, dict]]:
    rows = []
    for v in c.validations:
        vid = str(v.get("id") or "")
        claims = [p.sp_id for p in c.properties if vid in p.validation_ids]
        rows.append((f"E-{vid}", ", ".join(claims) or "regression gate (no SP)", v))
    return rows


def _evidence_status(v: dict) -> str:
    status = str(v.get("status") or "pending")
    mapped = _VALIDATION_STATUS.get(status)
    return f"`{mapped}`" if mapped else f"`not_run` ({_cell(status)})"


def _sec_evidence(c: _Ctx) -> list[str]:
    lines = [
        "`schema_ref:` `canonical.schema.validation_evidence.v1`",
        "`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`",
        "Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).",
        "",
        "| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |",
        "|-------------|---------------|---------------|--------|---------|-------------------|--------|",
    ]
    for eid, claims, v in _evidence_rows(c):
        lines.append(
            f"| {eid} | {claims} | `quality_gate_evidence` | command | "
            f"{_code(v.get('command') or '')} | {_cell(v.get('pass_criteria'))} | {_evidence_status(v)} |"
        )
    unbound = [p.sp_id for p in c.properties if not p.validation_ids]
    if unbound:
        lines += ["", f"**Unbound properties (no evidence row):** {', '.join(unbound)}"]
    return lines


def _sec_stress(c: _Ctx) -> list[str]:
    lines = [
        "### Disconfirming cases",
        "",
        *_bullets(c.stress.get("disconfirming_questions") or [], NOT_DECLARED),
        "",
        "### Assumption failure conditions",
        "",
        *_bullets(c.stress.get("assumed_false_ifs") or [], NOT_DECLARED),
        "",
        "### Blast radius notes",
        "",
        f"- {c.stress.get('blast_radius') or NOT_DECLARED}",
        "",
        "### Rollback constraints",
        "",
        f"- {c.stress.get('rollback') or NOT_DECLARED}",
        "",
        "### Risks",
        "",
        "| risk | mitigation |",
        "|------|------------|",
        *[
            f"| {_cell(r.get('risk'))} | {_cell(r.get('mitigation'))} |"
            for r in c.plan.get("risks") or []
        ],
    ]
    return lines


def _sec_out_of_scope(c: _Ctx) -> list[str]:
    scope = c.plan.get("scope") or {}
    return [
        *_bullets(scope.get("out") or [], NOT_DECLARED),
        "- Architecture redesign (unless plan_class + redesign_allowed)",
        "- Force-push, hard-reset, admin-merge, secret exfil",
        "- Weakening scanners / gates to obtain PASS",
        "- Follow-on schema/platform evolution",
    ]


def _template_gates(c: _Ctx) -> list[str]:
    match = re.search(r"^### Gates\n.*?(?=^### )", c.template_body, re.M | re.S)
    return match.group(0).rstrip().splitlines() if match else []


def _sec_convergence(c: _Ctx) -> list[str]:
    evidence = _evidence_rows(c)
    required = [eid for eid, _, _ in evidence]
    observed = [eid for eid, _, v in evidence if v.get("status") == "passed"]
    missing = [eid for eid in required if eid not in observed]
    missing += [f"{p.sp_id} (unbound)" for p in c.properties if not p.validation_ids]
    ready = not c.readiness_blockers()
    blockers = [
        f"| `unknown` | {_cell(u.get('id'))} | {_cell(u.get('question'))} — "
        + f"{_cell(u.get('decision_effect'))} | `{_cell(u.get('resolution'))}` |"
        for u in c.plan.get("unknowns") or []
    ]
    blockers += [
        f"| `open_blocker` | {sp} | success property has no runnable proving validation | "
        + "name a `final_validation` entry that can run |"
        for sp in c.unprovable_properties()
    ]
    if c.conv_status != "converged" and c.conv.get("stop_reason"):
        blockers.append(
            f"| `open_blocker` | stop_reason | {_cell(c.conv.get('stop_reason'))} | "
            f"planning convergence `{_cell(c.conv_status)}` |"
        )
    if not blockers:
        blockers.append("| — | — | no open blockers or unknowns | — |")
    next_skill = c.prof.next_skill or str(
        c.conv.get("next_skill") or "/autonomy + @environment/program-execution"
    )
    return [
        "`schema_ref:` `canonical.schema.convergence_contract.v1`",
        f"`instance_binding:` `convergence_contract_ref` → `conv.{c.plan_id}`",
        "Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| convergence_id | `conv.{c.plan_id}` |",
        f"| source_ref | `{c.plan_id}` |",
        f"| current_state | `{_CONVERGENCE_STATE[c.plan_status]}` |",
        f"| implementation_ready | `{'true' if ready else 'false'}` |",
        "",
        *_template_gates(c),
        "",
        "### Evidence",
        "",
        f"- **required_evidence_refs:** {', '.join(required) or 'none'}",
        f"- **observed_evidence_refs:** {', '.join(observed) or 'none'}",
        f"- **missing_evidence:** {', '.join(missing) or 'none'}",
        "",
        "### Blockers / unknowns",
        "",
        "| kind | id | note | resolution |",
        "|------|----|------|------------|",
        *blockers,
        "",
        "### Next",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| next_convergence_gate | `{_NEXT_GATE[c.plan_status]}` |",
        c.prof.next_action_row or _PE_NEXT_ACTION,
        c.prof.convergence_via_row or _PE_CONVERGENCE_VIA,
        f"| next_skill | {_cell(next_skill)} |",
        "| broader_work_requires_separate_contract | `true` |",
        "",
        "---",
    ]


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml(value: Any, indent: int = 0) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml(item, indent + 1))
            elif isinstance(item, list) and item and isinstance(item[0], dict):
                lines.append(f"{pad}{key}:")
                for entry in item:
                    sub = _yaml(entry, indent + 2)
                    lines.append(f"{pad}  - {sub[0].lstrip()}")
                    lines.extend(sub[1:])
            elif isinstance(item, list):
                lines.append(f"{pad}{key}: [{', '.join(_yaml_scalar(x) for x in item)}]")
            elif isinstance(item, dict):
                lines.append(f"{pad}{key}: {{}}")
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
    return lines


def _sec_machine_stub(c: _Ctx, body_after_swap: str) -> list[str]:
    match = re.search(r"^execute_via:\n(?:  .+\n)+", body_after_swap, re.M)
    execute_via_block = match.group(0).rstrip("\n").splitlines() if match else []
    scope = c.plan.get("scope") or {}
    head = {
        "schema_id": "canonical.schema.plan_document.v1",
        "schema_version": str(c.plan.get("schema_version") or "1.0.0"),
        "metadata": {
            "plan_id": c.plan_id,
            "name": c.title,
            "overview": str(c.plan.get("objective") or c.title),
            "status": c.plan_status,
            "is_project": False,
            "owner": str(c.plan.get("owner") or NOT_DECLARED),
        },
        "architect_framing": {
            "planning_ssot": "PLAN_DOCUMENT",
            "plan_class": "bounded_execution_contract",
            "redesign_allowed": False,
            "follow_on_schema_evolution_separate": True,
        },
        "immutable_baseline": {
            "repository": c.baseline_value("repository"),
            "commit_sha": c.baseline_value("commit_sha"),
            "dirty": c.baseline_value("dirty"),
            "overlap_policy": "stop_if_dirty_overlaps_may_modify",
            "verification_rule": "reverify_at_execution_start",
            "on_drift": "stop_and_replan",
        },
        "objective": {
            "mission": str(c.plan.get("objective") or ""),
            "success_properties": [
                {
                    "id": p.sp_id,
                    "property": p.text,
                    "evidence_type": "quality_gate" if p.validation_ids else "unbound",
                    "proof": list(p.validation_ids),
                    "blocking": True,
                }
                for p in c.properties
            ],
        },
        "capability_preflight_ref": f"preflight.{c.plan_id}",
        "execution_envelope": {
            "filesystem": {
                "write_allow": list(c.gmp.get("may_modify") or _todo_files(c)),
                "write_deny": list(c.gmp.get("must_not_modify") or []),
            },
            "commands": {"allow": _commands(c)},
            "network": {"mode": c.network.get("mode") or NOT_DECLARED},
            "secrets": {
                "access": c.secrets.get("access") or NOT_DECLARED,
                "redaction_required": True,
            },
            "autonomous_merge": False,
        },
        "side_effects_and_idempotency": [
            dict(
                zip(
                    ("todo_id", "side_effects", "idempotency", "retry"),
                    (str(t.get("id")), *_side_effect_row(t)[:3]),
                    strict=True,
                )
            )
            for t in c.todos
        ],
        "rollback_contract_ref": f"rollback.{c.plan_id}",
        "dependency_topology_ref": f"dag.{c.plan_id}",
        "validation_evidence_refs": [eid for eid, _, _ in _evidence_rows(c)],
        "stress_and_disconfirm": {
            "disconfirming_cases": list(c.stress.get("disconfirming_questions") or []),
            "assumption_failure_conditions": list(c.stress.get("assumed_false_ifs") or []),
        },
        "out_of_scope": list(scope.get("out") or []),
        "convergence_contract_ref": f"conv.{c.plan_id}",
    }
    todos = {
        "todos": [
            {"id": str(t.get("id")), "content": str(t.get("task") or ""), "status": "pending"}
            for t in c.todos
        ]
    }
    return [
        "Projected from PLAN_DOCUMENT; keep in sync with the sections above.",
        "",
        "```yaml",
        *_yaml(head),
        *execute_via_block,
        *_yaml(todos),
        "```",
    ]


_SECTION_BUILDERS = {
    "Metadata": _sec_metadata,
    "Architect framing": _sec_framing,
    "Immutable baseline": _sec_baseline,
    "Objective": _sec_objective,
    "Capability preflight": _sec_preflight,
    "Execution envelope": _sec_envelope,
    "Side effects and idempotency": _sec_side_effects,
    "Architecture impact": _sec_architecture,
    "Rollback": _sec_rollback,
    "Complexity and uncertainty": _sec_complexity,
    "Inventory and classification": lambda _c: _not_activated(
        "retire / migrate / replace inventory"
    ),
    "Gated write pipeline": _sec_gated_write,
    "Regeneration extinguishment": lambda _c: _not_activated("retirement or deprecation"),
    "Execution DAG": _sec_dag,
    "Property evidence matrix": _sec_evidence,
    "Stress and disconfirm": _sec_stress,
    "Out of scope": _sec_out_of_scope,
    "Follow-on milestone": lambda _c: _not_activated(
        "follow-on milestone; separate_plan_required `true` for any follow-on"
    ),
    "Convergence": _sec_convergence,
}

_SECTION_RE = re.compile(r"^## +(.+)$", re.M)


def _section_key(title: str) -> str:
    return re.sub(r"\s*\*\(optional.*$", "", title).strip()


def _fill_preamble(preamble: str, c: _Ctx) -> str:
    # A callable replacement: a string one is a template, so a title carrying a
    # backslash (`\s`, `\1`) raised "bad escape" or injected a group.
    heading = f"# PLAN: {c.title}"
    preamble = re.sub(r"^# PLAN:.*$", lambda _m: heading, preamble, count=1, flags=re.M)
    preamble = preamble.replace(
        f"# PLAN: {c.title}\n",
        f"# PLAN: {c.title}\n\n> **Projected by** `scripts/render_plan_pe_autonomy.py` "
        "from validated PLAN_DOCUMENT JSON.\n",
        1,
    )
    preamble = re.sub(
        r"^> \*\*Parameters:\*\*.*$",
        "> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading "
        "`unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved "
        "before status becomes `executable`.",
        preamble,
        count=1,
        flags=re.M,
    )
    return re.sub(
        r"^> \*\*Rename to:\*\*.*$",
        f"> **File name:** `{c.filename}`",
        preamble,
        count=1,
        flags=re.M,
    )


def _fill_sections(body: str, c: _Ctx) -> str:
    matches = list(_SECTION_RE.finditer(body))
    if not matches:
        return body
    out = [_fill_preamble(body[: matches[0].start()], c)]
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        title = match.group(1).strip()
        key = _section_key(title)
        if key.startswith("Machine stub"):
            lines = _sec_machine_stub(c, body)
        elif key in _SECTION_BUILDERS:
            lines = _SECTION_BUILDERS[key](c)
        else:
            # Execute / handoff sections and any heading this projector does not
            # own keep their template text verbatim.
            out.append(body[match.start() : end])
            continue
        out.append(f"## {title}\n\n" + "\n".join(lines).rstrip() + "\n\n")
    return "".join(out).rstrip() + "\n"


def render(
    plan: dict,
    template_text: str,
    execute_via: str = EXECUTE_VIA_PE,
    baseline: dict[str, str] | None = None,
) -> str:
    """Project PLAN_DOCUMENT through the template; every owned section is filled."""
    prof = projection_for(execute_via)
    body = template_text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].lstrip("\n")
    ctx = _Ctx(plan, prof, body, baseline)
    body = _swap_execute_block(body, execute_via)
    return _frontmatter(plan, execute_via) + "\n\n" + _fill_sections(body, ctx)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project PLAN_DOCUMENT JSON into a Cursor .plan.md"
    )
    parser.add_argument("plan_json", help="validated PLAN_DOCUMENT JSON")
    parser.add_argument("template", nargs="?", help="optional template override")
    parser.add_argument(
        "--execute-via",
        choices=EXECUTE_VIA_CHOICES,
        default=EXECUTE_VIA_PE,
        help=f"execute/handoff path (default {EXECUTE_VIA_PE})",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="bind the immutable baseline from this git work tree (read-only probes)",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="emit a projection that still contains undeclared fields",
    )
    args = parser.parse_args()
    plan_path = safe_cli_path(args.plan_json)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    skill_root = Path(__file__).resolve().parents[1]
    # skills/<pack>/ (or a nested skills/<group>/<pack>/): the repo root is the
    # parent of the nearest `skills` ancestor.
    repo_root = next(p.parent for p in skill_root.parents if p.name == "skills")
    if args.template:
        template_path = safe_cli_path(args.template)
    else:
        ssot = (repo_root / SSOT_REL).resolve()
        if ssot.is_file() and repo_root.resolve() in ssot.parents:
            template_path = ssot
        else:
            # Symlink under skill pack (confined to cwd when run from skill root)
            template_path = safe_cli_path(str(TEMPLATE_REL))
    template_text = template_path.read_text(encoding="utf-8")
    baseline = bind_workspace(safe_cli_path(args.workspace)) if args.workspace else None
    text = render(plan, template_text, execute_via=args.execute_via, baseline=baseline)
    sys.stdout.write(text)
    if not args.allow_draft and "unknown — not declared" in text:
        print(
            "FAIL: projection contains undeclared fields (unknown — not declared). "
            "Declare them in PLAN_DOCUMENT or pass --allow-draft.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
