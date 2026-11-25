#!/usr/bin/env python3
"""Advisory lane-claim registry for parallel CTO campaigns on one repository.

Two CTO campaigns working one repository do not know each other's planned paths
until code exists, and a base-changing landing (a CI baseline, a gate config)
reaches the other campaign only as a red build. This module gives each campaign
a place to declare its lanes and a way to ask who else is on a path. Nothing
more:

  register  upsert one lane of this campaign's claim
  release   mark a lane, or the whole campaign, released
  check     overlaps of the given paths with every other campaign's live lanes
            and every open PR's files (open PRs via ``pr_fleet.inventory``)
  label     add ``campaign:<C>`` and ``cto:<S>`` to a PR
  notice    append a structured notice to this campaign's claim and print the
            ready-to-send ``CTO NOTICE`` texts; sending is the CTO's own act

Storage: one per-repository GitHub issue labelled ``l9-cto-registry`` and
titled "L9 CTO lane registry", created on first register. Each campaign owns
exactly one comment on it, holding one fenced JSON block of schema
``l9.cto-claims/v1`` (governance/cto-mode/schemas/claims.schema.json). A CTO
edits only the comment whose ``cto_session`` is its own. Transport is REST
(``gh api``); GraphQL is never used (rules/62).

Advisory, never authority (rule 96 E7/E8/E10; L9-AUTH-001/002): a claim is not
a lock and grants no repository-write permission. Git, the PR gates and the
``pr_fleet`` overlap analysis stay the enforcement. Every JSON output carries
``"grants_permission": false`` and ``"advisory": true``. This tool never sends a
message and never merges.

Undeterminable state is not clean (L9-UNKNOWN-001): when the open-PR inventory
or a registry comment cannot be read, ``check`` reports ``status: unknown`` and
exits 2 rather than reporting no overlap.

Path grammar: ``**`` crosses ``/``, ``*`` and ``?`` stay within one segment, a
trailing ``/`` means the whole directory. Glob-to-glob overlap is conservative:
it may report a pair that shares no real file, never the reverse.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

CLAIMS_SCHEMA = "l9.cto-claims/v1"
OWNERSHIP_SCHEMA = "l9.cto-ownership/v1"
RESULT_SCHEMA = "l9.cto-claims-result/v1"
REGISTRY_LABEL = "l9-cto-registry"
REGISTRY_TITLE = "L9 CTO lane registry"
STATES = ("planned", "active", "published", "merged", "released")
LIVE_STATES = frozenset({"planned", "active", "published"})
NOTICE_KINDS = ("base-change", "interface-change", "gate-change")
MARKER = "<!-- l9-cto-claims"
LABEL_MAX = 50  # GitHub label name limit
PAGE_SIZE = 100
MAX_PAGES = 20
GH_TIMEOUT_SECONDS = 60

CLAIMS_SCHEMA_PATH = _ROOT / "governance" / "cto-mode" / "schemas" / "claims.schema.json"
OWNERSHIP_PATH = _ROOT / "governance" / "cto-mode" / "ownership.yaml"

_FENCE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class ClaimsError(RuntimeError):
    """A registry operation that must not proceed. Nothing was written."""


# ---------------------------------------------------------------------------
# REST transport
# ---------------------------------------------------------------------------


class Rest(Protocol):
    def get(self, path: str) -> Any: ...

    def send(self, method: str, path: str, body: dict[str, Any]) -> Any: ...


class GhRest:
    """``gh api`` REST. Raises ClaimsError with a short detail."""

    def _run(self, args: list[str], stdin: str | None = None) -> Any:
        if not shutil.which("gh"):
            raise ClaimsError("gh not on PATH")
        try:
            proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                ["gh", "api", *args],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=GH_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ClaimsError(f"gh api failed: {exc}") from exc
        if proc.returncode != 0:
            lines = (proc.stderr or "gh api returned non-zero").strip().splitlines()
            raise ClaimsError(f"gh api {args[-1]}: {(lines[-1] if lines else '')[:200]}")
        try:
            return json.loads(proc.stdout or "null")
        except json.JSONDecodeError as exc:
            raise ClaimsError(f"gh api emitted non-JSON: {exc}") from exc

    def get(self, path: str) -> Any:
        return self._run(["-X", "GET", path])

    def send(self, method: str, path: str, body: dict[str, Any]) -> Any:
        return self._run(["-X", method, path, "--input", "-"], stdin=json.dumps(body))


def _pages(rest: Rest, path: str) -> list[Any]:
    out: list[Any] = []
    for page in range(1, MAX_PAGES + 1):
        sep = "&" if "?" in path else "?"
        body = rest.get(f"{path}{sep}per_page={PAGE_SIZE}&page={page}")
        if not isinstance(body, list):
            raise ClaimsError(f"{path} returned a non-list payload")
        out.extend(body)
        if len(body) < PAGE_SIZE:
            return out
    raise ClaimsError(f"{path}: more than {MAX_PAGES} pages; refusing a partial set")


# ---------------------------------------------------------------------------
# path grammar
# ---------------------------------------------------------------------------

_WILD = re.compile(r"[*?\[]")


def _normalize_glob(glob: str) -> str:
    glob = glob.strip().removeprefix("./")
    if glob.endswith("/"):
        glob += "**"
    return glob


def _glob_regex(glob: str) -> re.Pattern[str]:
    out = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def glob_matches(glob: str, path: str) -> bool:
    """True when the concrete ``path`` is covered by ``glob``."""
    return bool(_glob_regex(_normalize_glob(glob)).match(path))


def _static_prefix(glob: str) -> str:
    match = _WILD.search(glob)
    return glob if match is None else glob[: match.start()]


def _static_tail(glob: str) -> str:
    last = max(glob.rfind("*"), glob.rfind("?"), glob.rfind("]"))
    return glob[last + 1 :]


def globs_overlap(left: str, right: str) -> bool:
    """Whether two path globs may cover a common path. Conservative."""
    a, b = _normalize_glob(left), _normalize_glob(right)
    wild_a, wild_b = bool(_WILD.search(a)), bool(_WILD.search(b))
    if not wild_a and not wild_b:
        return a == b
    if not wild_a:
        return glob_matches(b, a)
    if not wild_b:
        return glob_matches(a, b)
    if glob_matches(a, b) or glob_matches(b, a):
        return True
    pa, pb = _static_prefix(a), _static_prefix(b)
    if not (pa.startswith(pb) or pb.startswith(pa)):
        return False
    ta, tb = _static_tail(a), _static_tail(b)
    return ta.endswith(tb) or tb.endswith(ta)


# ---------------------------------------------------------------------------
# ownership
# ---------------------------------------------------------------------------


def load_ownership(path: Path | None = None) -> dict[str, Any]:
    import yaml  # noqa: PLC0415 - governance venv dependency

    source = path or OWNERSHIP_PATH
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ClaimsError(f"unreadable ownership file {source}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != OWNERSHIP_SCHEMA:
        raise ClaimsError(f"{source}: schema must be {OWNERSHIP_SCHEMA}")
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ClaimsError(f"{source}: rules must be a non-empty list")
    for rule in rules:
        if not (
            isinstance(rule, dict)
            and isinstance(rule.get("repos"), list)
            and isinstance(rule.get("paths"), list)
            and isinstance(rule.get("owner"), str)
        ):
            raise ClaimsError(f"{source}: every rule needs repos, paths and owner")
    return data


def owner_of(ownership: dict[str, Any], repo: str, path: str) -> str | None:
    """First rule whose repo pattern and path glob both cover ``path``."""
    for rule in ownership["rules"]:
        if not any(fnmatch.fnmatchcase(repo.lower(), p.lower()) for p in rule["repos"]):
            continue
        if any(globs_overlap(glob, path) for glob in rule["paths"]):
            return str(rule["owner"])
    return None


def _ownership_rows(
    ownership: dict[str, Any], repo: str, paths: Sequence[str], role: str | None
) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(set(paths)):
        owner = owner_of(ownership, repo, path)
        if owner is None:
            continue
        rows.append(
            {"path": path, "owner": owner, "mismatch": None if role is None else owner != role}
        )
    return rows


# ---------------------------------------------------------------------------
# registry storage
# ---------------------------------------------------------------------------


@dataclass
class Comment:
    id: int
    doc: dict[str, Any] | None
    error: str | None


def validate_doc(doc: dict[str, Any]) -> None:
    import jsonschema  # noqa: PLC0415 - governance venv dependency

    schema = json.loads(CLAIMS_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        raise ClaimsError(f"claim violates {CLAIMS_SCHEMA}: {exc.message}") from exc


def render_body(doc: dict[str, Any]) -> str:
    return (
        f"{MARKER} campaign={doc['campaign']} -->\n"
        f"### L9 CTO claims: `{doc['campaign']}`\n\n"
        "Advisory registry entry: it is not a lock and grants no permission. "
        "Edited only by the CTO session named in it, through "
        "`ops/autonomy/cto_claims.py`.\n\n"
        f"```json\n{json.dumps(doc, indent=2, sort_keys=True)}\n```\n"
    )


def parse_body(body: str) -> tuple[dict[str, Any] | None, str | None]:
    """(doc, None) for a claim comment, (None, error) for a broken one, (None, None) otherwise."""
    if MARKER not in body:
        return None, None
    match = _FENCE.search(body)
    if match is None:
        return None, "claim comment has no fenced json block"
    try:
        doc = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return None, f"claim comment json is malformed: {exc}"
    if not isinstance(doc, dict) or doc.get("schema") != CLAIMS_SCHEMA:
        return None, f"claim comment schema is not {CLAIMS_SCHEMA}"
    try:
        validate_doc(doc)
    except ClaimsError as exc:
        return None, str(exc)
    return doc, None


def find_registry(rest: Rest, repo: str) -> int | None:
    rows = _pages(rest, f"repos/{repo}/issues?labels={REGISTRY_LABEL}&state=open")
    numbers = sorted(
        int(row["number"])
        for row in rows
        if isinstance(row, dict)
        and row.get("title") == REGISTRY_TITLE
        and "pull_request" not in row
    )
    return numbers[0] if numbers else None


def ensure_registry(rest: Rest, repo: str) -> int:
    number = find_registry(rest, repo)
    if number is not None:
        return number
    body = (
        "Advisory lane registry for parallel L9 CTO campaigns. One comment per "
        "campaign, maintained by `ops/autonomy/cto_claims.py`. Claims are not "
        "locks and grant no permission; git, the PR gates and CI remain the "
        "enforcement."
    )
    created = rest.send(
        "POST",
        f"repos/{repo}/issues",
        {"title": REGISTRY_TITLE, "body": body, "labels": [REGISTRY_LABEL]},
    )
    if not isinstance(created, dict) or "number" not in created:
        raise ClaimsError("registry issue creation returned no number")
    return int(created["number"])


def load_comments(rest: Rest, repo: str, issue: int) -> list[Comment]:
    out = []
    for row in _pages(rest, f"repos/{repo}/issues/{issue}/comments"):
        if not isinstance(row, dict):
            continue
        doc, error = parse_body(str(row.get("body") or ""))
        if doc is None and error is None:
            continue
        out.append(Comment(id=int(row["id"]), doc=doc, error=error))
    return out


def _own_comment(comments: list[Comment], campaign: str) -> Comment | None:
    own = [c for c in comments if c.doc is not None and c.doc["campaign"] == campaign]
    if len(own) > 1:
        raise ClaimsError(
            f"campaign {campaign} has {len(own)} registry comments "
            f"({', '.join(str(c.id) for c in own)}); refusing to choose one"
        )
    return own[0] if own else None


def _require_owner(comment: Comment, session: str) -> dict[str, Any]:
    assert comment.doc is not None
    if comment.doc["cto_session"] != session:
        raise ClaimsError(
            f"registry comment {comment.id} for campaign {comment.doc['campaign']} belongs "
            f"to cto_session {comment.doc['cto_session']}, not {session}; "
            "a CTO edits only its own claim"
        )
    return comment.doc


def _write(rest: Rest, repo: str, issue: int, comment: Comment | None, doc: dict[str, Any]) -> int:
    validate_doc(doc)
    body = {"body": render_body(doc)}
    if comment is not None:
        rest.send("PATCH", f"repos/{repo}/issues/comments/{comment.id}", body)
        return comment.id
    created = rest.send("POST", f"repos/{repo}/issues/{issue}/comments", body)
    if not isinstance(created, dict) or "id" not in created:
        raise ClaimsError("comment creation returned no id")
    return int(created["id"])


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _envelope(action: str, repo: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "action": action,
        "repo": repo,
        "grants_permission": False,
        "advisory": True,
        **fields,
    }


def _new_doc(campaign: str, session: str, repo: str, base: str, now: str) -> dict[str, Any]:
    return {
        "schema": CLAIMS_SCHEMA,
        "campaign": campaign,
        "cto_session": session,
        "repo": repo,
        "base": base,
        "lanes": [],
        "notices": [],
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# operations
# ---------------------------------------------------------------------------


def register(
    rest: Rest,
    *,
    repo: str,
    campaign: str,
    session: str,
    lane: str,
    paths: Sequence[str],
    pr: int | None = None,
    state: str | None = None,
    base: str | None = None,
    now: Callable[[], str] = _now,
) -> dict[str, Any]:
    if not paths:
        raise ClaimsError("register needs at least one path")
    issue = ensure_registry(rest, repo)
    comment = _own_comment(load_comments(rest, repo, issue), campaign)
    stamp = now()
    if comment is None:
        doc = _new_doc(campaign, session, repo, base or "main", stamp)
    else:
        doc = json.loads(json.dumps(_require_owner(comment, session)))
        if base:
            doc["base"] = base
    entry = next((row for row in doc["lanes"] if row["lane"] == lane), None)
    if entry is None:
        entry = {"lane": lane, "paths": [], "pr": None, "state": "planned"}
        doc["lanes"].append(entry)
    entry["paths"] = sorted({_normalize_glob(p) for p in paths})
    if pr is not None:
        entry["pr"] = pr
    if state is not None:
        entry["state"] = state
    elif pr is not None and entry["state"] == "planned":
        entry["state"] = "published"
    doc["updated_at"] = stamp
    comment_id = _write(rest, repo, issue, comment, doc)
    return _envelope("register", repo, issue=issue, comment_id=comment_id, claim=doc)


def release(
    rest: Rest,
    *,
    repo: str,
    campaign: str,
    session: str,
    lane: str | None = None,
    now: Callable[[], str] = _now,
) -> dict[str, Any]:
    issue = find_registry(rest, repo)
    comment = None if issue is None else _own_comment(load_comments(rest, repo, issue), campaign)
    if issue is None or comment is None:
        raise ClaimsError(f"campaign {campaign} has no claim on {repo}")
    doc = json.loads(json.dumps(_require_owner(comment, session)))
    targets = [row for row in doc["lanes"] if lane is None or row["lane"] == lane]
    if lane is not None and not targets:
        raise ClaimsError(f"campaign {campaign} has no lane {lane}")
    for row in targets:
        row["state"] = "released"
    doc["updated_at"] = now()
    comment_id = _write(rest, repo, issue, comment, doc)
    return _envelope(
        "release",
        repo,
        issue=issue,
        comment_id=comment_id,
        released=[row["lane"] for row in targets],
        claim=doc,
    )


def _overlapping(mine: Sequence[str], theirs: Sequence[str]) -> list[str]:
    return sorted({t for t in theirs if any(globs_overlap(m, t) for m in mine)})


def check(
    rest: Rest,
    *,
    repo: str,
    paths: Sequence[str],
    campaign: str | None = None,
    role: str | None = None,
    open_prs: Callable[[str], list[dict[str, Any]]] | None = None,
    ownership: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not paths:
        raise ClaimsError("check needs at least one path")
    mine = [_normalize_glob(p) for p in paths]
    owners = ownership if ownership is not None else load_ownership()
    unknown: list[str] = []
    issue = find_registry(rest, repo)
    comments = [] if issue is None else load_comments(rest, repo, issue)
    unknown.extend(f"registry comment {c.id}: {c.error}" for c in comments if c.error)
    docs = [c.doc for c in comments if c.doc is not None]
    own_prs = {
        int(row["pr"])
        for doc in docs
        if campaign is not None and doc["campaign"] == campaign
        for row in doc["lanes"]
        if row.get("pr") is not None
    }
    pr_owner: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {
        int(row["pr"]): (doc, row) for doc in docs for row in doc["lanes"] if row.get("pr")
    }

    overlaps: list[dict[str, Any]] = []
    for doc in docs:
        if campaign is not None and doc["campaign"] == campaign:
            continue
        for row in doc["lanes"]:
            if row["state"] not in LIVE_STATES:
                continue
            shared = _overlapping(mine, row["paths"])
            if shared:
                overlaps.append(
                    {
                        "source": "claim",
                        "campaign": doc["campaign"],
                        "cto_session": doc["cto_session"],
                        "lane": row["lane"],
                        "pr": row.get("pr"),
                        "state": row["state"],
                        "paths": shared,
                        "ownership": _ownership_rows(owners, repo, shared, role),
                    }
                )

    prs: list[dict[str, Any]] = []
    try:
        prs = (open_prs or _fleet_inventory)(repo)
    except Exception as exc:  # noqa: BLE001 - any inventory failure is unknown, not clean
        unknown.append(f"open-PR inventory unavailable: {exc}")
    generated = _generated_predicate()
    for pr in prs:
        number = int(pr["number"])
        if number in own_prs:
            continue
        shared = sorted({f for f in pr.get("files") or [] if any(glob_matches(m, f) for m in mine)})
        if not shared:
            continue
        doc, row = pr_owner.get(number, (None, None))
        overlaps.append(
            {
                "source": "open_pr",
                "campaign": doc["campaign"] if doc else None,
                "cto_session": doc["cto_session"] if doc else None,
                "lane": row["lane"] if row else None,
                "pr": number,
                "head": pr.get("headRefOid"),
                "paths": shared,
                "generated_only": all(generated(f) for f in shared),
                "ownership": _ownership_rows(owners, repo, shared, role),
            }
        )

    status = "unknown" if unknown else ("overlap" if overlaps else "clear")
    return _envelope(
        "check",
        repo,
        status=status,
        campaign=campaign,
        role=role,
        paths=mine,
        registry_issue=issue,
        overlaps=overlaps,
        requested_ownership=_ownership_rows(owners, repo, mine, role),
        unknown=unknown,
    )


def _fleet_inventory(repo: str) -> list[dict[str, Any]]:
    import pr_fleet  # noqa: PLC0415 - heavy import, only on the live path

    return pr_fleet.inventory(repo)


def _generated_predicate() -> Callable[[str], bool]:
    try:
        import pr_fleet  # noqa: PLC0415

        return pr_fleet.is_generated_path
    except ImportError:  # pragma: no cover - the module ships beside this one
        return lambda _path: False


def label(rest: Rest, *, repo: str, pr: int, campaign: str, session: str) -> dict[str, Any]:
    labels = [f"campaign:{campaign}", f"cto:{session}"]
    too_long = [name for name in labels if len(name) > LABEL_MAX]
    if too_long:
        raise ClaimsError(f"label exceeds GitHub's {LABEL_MAX}-character limit: {too_long}")
    rest.send("POST", f"repos/{repo}/issues/{pr}/labels", {"labels": labels})
    return _envelope("label", repo, pr=pr, labels=labels)


def _affected(
    docs: list[dict[str, Any]], campaign: str, base: str, kind: str, paths: Sequence[str]
) -> list[dict[str, Any]]:
    out = []
    for doc in docs:
        if doc["campaign"] == campaign:
            continue
        live = [row for row in doc["lanes"] if row["state"] in LIVE_STATES]
        hit = [row for row in live if _overlapping(paths, row["paths"])]
        if kind == "base-change" and doc.get("base") == base:
            hit = live
        if hit:
            out.append(
                {
                    "campaign": doc["campaign"],
                    "cto_session": doc["cto_session"],
                    "lanes": sorted(row["lane"] for row in hit),
                }
            )
    return sorted(out, key=lambda row: row["campaign"])


def render_notice(
    repo: str, campaign: str, session: str, notice: dict[str, Any], to: dict[str, Any]
) -> str:
    return "\n".join(
        [
            f"CTO NOTICE {notice['kind']} | repo {repo} | from campaign {campaign} "
            f"(cto_session {session})",
            notice["text"],
            "Paths: " + ", ".join(notice["paths"]),
            f"Your affected lanes (campaign {to['campaign']}): " + ", ".join(to["lanes"]),
            "Advisory: this notice is not a lock and grants no permission.",
        ]
    )


def notice(
    rest: Rest,
    *,
    repo: str,
    campaign: str,
    session: str,
    kind: str,
    paths: Sequence[str],
    text: str,
    base: str | None = None,
    now: Callable[[], str] = _now,
) -> dict[str, Any]:
    if kind not in NOTICE_KINDS:
        raise ClaimsError(f"notice kind must be one of {', '.join(NOTICE_KINDS)}")
    if not paths or not text.strip():
        raise ClaimsError("notice needs paths and text")
    issue = ensure_registry(rest, repo)
    comments = load_comments(rest, repo, issue)
    comment = _own_comment(comments, campaign)
    stamp = now()
    if comment is None:
        doc = _new_doc(campaign, session, repo, base or "main", stamp)
    else:
        doc = json.loads(json.dumps(_require_owner(comment, session)))
    norm = sorted({_normalize_glob(p) for p in paths})
    docs = [c.doc for c in comments if c.doc is not None]
    affected = _affected(docs, campaign, doc["base"], kind, norm)
    record = {
        "kind": kind,
        "paths": norm,
        "text": text.strip(),
        "created_at": stamp,
        "affected": affected,
    }
    doc["notices"].append(record)
    doc["updated_at"] = stamp
    comment_id = _write(rest, repo, issue, comment, doc)
    messages = [
        {"to": row["cto_session"], "text": render_notice(repo, campaign, session, record, row)}
        for row in affected
    ]
    return _envelope(
        "notice",
        repo,
        issue=issue,
        comment_id=comment_id,
        notice=record,
        messages=messages,
        sent=False,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0] if __doc__ else None
    )
    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="upsert one lane of this campaign's claim")
    reg.add_argument("--repo", required=True)
    reg.add_argument("--campaign", required=True)
    reg.add_argument("--cto-session", required=True)
    reg.add_argument("--lane", required=True)
    reg.add_argument("--paths", nargs="+", required=True)
    reg.add_argument("--pr", type=int)
    reg.add_argument("--state", choices=STATES)
    reg.add_argument("--base")

    rel = sub.add_parser("release", help="mark a lane or the whole campaign released")
    rel.add_argument("--repo", required=True)
    rel.add_argument("--campaign", required=True)
    rel.add_argument("--cto-session", required=True)
    rel.add_argument("--lane")

    chk = sub.add_parser("check", help="overlaps with other campaigns and open PRs")
    chk.add_argument("--repo", required=True)
    chk.add_argument("--paths", nargs="+", required=True)
    chk.add_argument("--campaign")
    chk.add_argument("--role", help="owner role of the caller, to flag ownership mismatch")

    lab = sub.add_parser("label", help="add campaign:<C> and cto:<S> labels to a PR")
    lab.add_argument("--repo", required=True)
    lab.add_argument("--pr", type=int, required=True)
    lab.add_argument("--campaign", required=True)
    lab.add_argument("--cto-session", required=True)

    note = sub.add_parser("notice", help="record a notice and print CTO NOTICE texts")
    note.add_argument("--repo", required=True)
    note.add_argument("--campaign", required=True)
    note.add_argument("--cto-session", required=True)
    note.add_argument("--kind", choices=NOTICE_KINDS, required=True)
    note.add_argument("--paths", nargs="+", required=True)
    note.add_argument("--text", required=True)
    note.add_argument("--base")
    return parser


def main(argv: Sequence[str] | None = None, rest: Rest | None = None) -> int:
    args = _parser().parse_args(argv)
    client = rest or GhRest()
    try:
        if args.command == "register":
            result = register(
                client,
                repo=args.repo,
                campaign=args.campaign,
                session=args.cto_session,
                lane=args.lane,
                paths=args.paths,
                pr=args.pr,
                state=args.state,
                base=args.base,
            )
        elif args.command == "release":
            result = release(
                client,
                repo=args.repo,
                campaign=args.campaign,
                session=args.cto_session,
                lane=args.lane,
            )
        elif args.command == "check":
            result = check(
                client, repo=args.repo, paths=args.paths, campaign=args.campaign, role=args.role
            )
        elif args.command == "label":
            result = label(
                client,
                repo=args.repo,
                pr=args.pr,
                campaign=args.campaign,
                session=args.cto_session,
            )
        else:
            result = notice(
                client,
                repo=args.repo,
                campaign=args.campaign,
                session=args.cto_session,
                kind=args.kind,
                paths=args.paths,
                text=args.text,
                base=args.base,
            )
    except ClaimsError as exc:
        print(json.dumps(_envelope(args.command, args.repo, status="error", error=str(exc))))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command == "check":
        return {"clear": 0, "overlap": 1}.get(result["status"], 2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
