#!/usr/bin/env python3
"""Compose an issue body from an org issue form — the sibling of compose_pr_body.py.

``make pr`` fills the org PR template; nothing filled the org issue forms, so an
agent-filed issue was free text that triage could not parse. This renders the
exact body GitHub renders when the form is submitted in the browser — one
``### <label>`` heading per field, in form order, ``_No response_`` for an empty
field, a fenced block for a field that sets ``render`` — so the org triage
workflows (Quantum-L9/.github issue-triage.yml, governance-issue.yml) label an
agent-filed issue exactly like a hand-filed one.

Form resolution mirrors GitHub, and open_pr_after_gate.sh's template lookup:

1. ``--form-file`` when given (tests, local drafts);
2. the workspace's own ``.github/ISSUE_TEMPLATE/`` — when that folder exists,
   GitHub shows none of the org defaults, so a form missing there is an error,
   not a fall-through;
3. the org default in ``<owner>/.github`` (REST contents, base64);
4. the governance fork's ``.github/ISSUE_TEMPLATE/``.

Required fields are the reporter's judgment and are never invented. A missing
one is reported (exit 2, ``missing_required`` in the handoff), and ``--create``
refuses to file an incomplete issue, as the web form would.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "l9.issue_body_completion.v1"
RECEIPT_SCHEMA = "l9.issue_receipt.v1"
NO_RESPONSE = "_No response_"
FORM_DIR = Path(".github/ISSUE_TEMPLATE")
RECEIPT_REL = Path(".l9/issue/issue-receipt.json")
HANDOFF_REL = Path(".l9/issue/issue-body-completion.json")
GOV_ROOT = Path(__file__).resolve().parents[2]

#: Short names an operator or agent types; the file names are the org's.
FORM_ALIASES = {
    "bug": "1-bug.yml",
    "feature": "2-feature.yml",
    "task": "3-task.yml",
    "incident": "4-incident.yml",
    "ci": "ci-failure.yml",
    "seed-ci": "seed-ci-failure.yml",
    "governance": "gov-violation.yml",
}


class FormError(ValueError):
    """The form, or an answer to it, cannot produce a valid issue."""


@dataclass
class ComposedIssue:
    title: str
    body: str
    labels: list[str]
    form_file: str
    form_source: str
    missing_required: list[str] = field(default_factory=list)
    mechanical_filled: list[str] = field(default_factory=list)


def form_file_name(name: str) -> str:
    """Map ``bug`` / ``1-bug`` / ``1-bug.yml`` to the form's file name."""
    key = name.strip()
    if key in FORM_ALIASES:
        return FORM_ALIASES[key]
    return key if key.endswith((".yml", ".yaml")) else f"{key}.yml"


def repo_slug(workspace: Path) -> str | None:
    """``owner/name`` from the origin URL (https, ssh, or a session proxy path)."""
    try:
        url = subprocess.run(
            ["git", "-C", str(workspace), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    parts = [p for p in re.split(r"[/:]", url.removesuffix(".git")) if p]
    return f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else None


def _fetch_org_form(owner: str, file_name: str) -> str | None:
    path = f"repos/{owner}/.github/contents/{FORM_DIR.as_posix()}/{file_name}"
    try:
        out = subprocess.run(
            [
                "gh",
                "api",
                path,
                "--jq",
                'select(.type == "file" and .encoding == "base64") | .content',
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return base64.b64decode(out).decode("utf-8") if out.strip() else None


def resolve_form(
    name: str,
    workspace: Path,
    *,
    form_file: Path | None = None,
    gov_root: Path = GOV_ROOT,
    fetch_org: bool = True,
) -> tuple[str, str, str]:
    """Return ``(file_name, yaml_text, source)`` for the requested form."""
    file_name = form_file_name(name)
    if form_file is not None:
        return file_name, form_file.read_text(encoding="utf-8"), str(form_file)

    local_dir = workspace / FORM_DIR
    if local_dir.is_dir() and any(local_dir.iterdir()):
        local = local_dir / file_name
        if not local.is_file():
            forms = sorted(p.name for p in local_dir.glob("*.y*ml") if p.name != "config.yml")
            msg = (
                f"{local_dir} exists, so GitHub shows none of the org default forms here, "
                f"and it has no {file_name}. Forms in this repo: {', '.join(forms) or 'none'}"
            )
            raise FormError(msg)
        return file_name, local.read_text(encoding="utf-8"), f"workspace:{local}"

    slug = repo_slug(workspace)
    if fetch_org and slug:
        owner = slug.split("/")[0]
        text = _fetch_org_form(owner, file_name)
        if text is not None:
            return file_name, text, f"org:{owner}/.github:{FORM_DIR.as_posix()}/{file_name}"

    fork = gov_root / FORM_DIR / file_name
    if fork.is_file():
        return file_name, fork.read_text(encoding="utf-8"), f"governance-fork:{fork}"
    msg = f"no issue form {file_name} in the workspace, the org .github repo, or {fork.parent}"
    raise FormError(msg)


def _fields(form: dict[str, Any]) -> list[dict[str, Any]]:
    body = form.get("body")
    if not isinstance(body, list):
        raise FormError("issue form has no body list")
    return [el for el in body if isinstance(el, dict) and el.get("type") != "markdown"]


def _required(el: dict[str, Any]) -> bool:
    if el.get("type") == "checkboxes":
        # A checkbox field is required per option, not at field level.
        options = (el.get("attributes") or {}).get("options", [])
        return any(isinstance(o, dict) and o.get("required") for o in options)
    return bool((el.get("validations") or {}).get("required"))


def _match_option(options: list[str], value: str, field_id: str) -> str:
    """Exact option, else the one option the value prefixes (``S2``, ``Production``)."""
    if value in options:
        return value
    hits = [o for o in options if o.lower().startswith(value.strip().lower())]
    if len(hits) == 1:
        return hits[0]
    msg = f"{field_id}: {value!r} is not one option of {options}"
    raise FormError(msg)


def _render_value(el: dict[str, Any], value: Any) -> str:
    attrs = el.get("attributes") or {}
    kind = el.get("type")
    if kind == "checkboxes":
        options = [o["label"] for o in attrs.get("options", [])]
        picked = set()
        for v in value or []:
            if isinstance(v, int) and 0 <= v < len(options):
                picked.add(v)
            elif isinstance(v, str) and v in options:
                picked.add(options.index(v))
            else:
                msg = f"{el['id']}: {v!r} is not an option index or label"
                raise FormError(msg)
        return "\n".join(f"- [{'X' if i in picked else ' '}] {o}" for i, o in enumerate(options))
    if value is None or value == "" or value == []:
        return NO_RESPONSE
    if kind == "dropdown":
        options = list(attrs.get("options", []))
        picks = value if isinstance(value, list) else [value]
        if len(picks) > 1 and not attrs.get("multiple"):
            msg = f"{el['id']}: pick exactly one option"
            raise FormError(msg)
        return ", ".join(_match_option(options, str(p), el["id"]) for p in picks)
    text = str(value).strip("\n")
    if attrs.get("render"):
        return f"```{attrs['render']}\n{text}\n```"
    return text


def _answered(el: dict[str, Any], value: Any) -> bool:
    if el.get("type") == "checkboxes":
        opts = (el.get("attributes") or {}).get("options", [])
        needed = [i for i, o in enumerate(opts) if o.get("required")]
        labels = [o["label"] for o in opts]
        given = {
            v if isinstance(v, int) else labels.index(v)
            for v in value or []
            if v in labels or isinstance(v, int)
        }
        return all(i in given for i in needed)
    return not (value is None or str(value).strip() == "" or value == [])


def mechanical_answers(form: dict[str, Any], workspace: Path) -> dict[str, str]:
    """Facts the composer can measure. Only ``version`` (this checkout's HEAD)."""
    ids = {el.get("id") for el in _fields(form)}
    out: dict[str, str] = {}
    if "version" in ids:
        try:
            out["version"] = subprocess.run(
                ["git", "-C", str(workspace), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return out


def compose_issue(
    form_text: str,
    answers: dict[str, Any],
    *,
    title: str,
    form_file: str = "",
    form_source: str = "",
    mechanical: dict[str, Any] | None = None,
) -> ComposedIssue:
    form = yaml.safe_load(form_text)
    if not isinstance(form, dict):
        raise FormError("issue form is not a mapping")
    fields = _fields(form)
    ids = [el.get("id") for el in fields]
    unknown = sorted(set(answers) - set(ids))
    if unknown:
        msg = f"answers name fields this form does not have: {unknown}; fields: {ids}"
        raise FormError(msg)

    merged = dict(answers)
    filled = []
    for key, value in (mechanical or {}).items():
        if key in ids and not _answered(fields[ids.index(key)], merged.get(key)):
            merged[key] = value
            filled.append(key)

    sections = []
    missing = []
    for el in fields:
        value = merged.get(str(el.get("id")))
        if _required(el) and not _answered(el, value):
            missing.append(el["id"])
        sections.append(f"### {el['attributes']['label']}\n\n{_render_value(el, value)}")

    prefix = str(form.get("title") or "")
    text = title.strip()
    if prefix.strip() and text.lower().startswith(prefix.strip().lower()):
        text = text[len(prefix.strip()) :].strip()
    if not text:
        raise FormError("an issue needs a title after the form's prefix")
    return ComposedIssue(
        title=f"{prefix}{text}",
        body="\n\n".join(sections) + "\n",
        labels=[str(label) for label in form.get("labels") or []],
        form_file=form_file,
        form_source=form_source,
        missing_required=missing,
        mechanical_filled=filled,
    )


def _parse_set(pairs: list[str], fields_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            msg = f"--set expects id=value, got {pair!r}"
            raise FormError(msg)
        if value.startswith("@"):
            value = Path(value[1:]).read_text(encoding="utf-8")
        el = fields_by_id.get(key)
        if el is not None and el.get("type") == "checkboxes":
            out[key] = [
                int(v) if v.strip().isdigit() else v.strip() for v in value.split(",") if v.strip()
            ]
        elif el is not None and (el.get("attributes") or {}).get("multiple"):
            out[key] = [v.strip() for v in value.split(",") if v.strip()]
        else:
            out[key] = value
    return out


def create_issue(repo: str, issue: ComposedIssue) -> dict[str, Any]:
    """POST /repos/{repo}/issues over REST (no GraphQL: gh issue create is not used)."""
    payload = json.dumps({"title": issue.title, "body": issue.body, "labels": issue.labels})
    out = subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{repo}/issues", "--input", "-"],
        input=payload,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    created: dict[str, Any] = json.loads(out)
    return created


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument(
        "--form", required=True, help=f"one of {sorted(FORM_ALIASES)} or a form file name"
    )
    parser.add_argument(
        "--form-file", type=Path, default=None, help="read this form instead of resolving it"
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--answers", type=Path, default=None, help="JSON object {field_id: value}")
    parser.add_argument(
        "--set", action="append", default=[], metavar="ID=VALUE", help="VALUE of @path reads a file"
    )
    parser.add_argument("--no-org", action="store_true", help="do not fetch the org default form")
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument(
        "--create", action="store_true", help="file the issue (REST) and write a receipt"
    )
    parser.add_argument(
        "--repo", default=None, help="owner/name to file in (default: the workspace origin)"
    )
    args = parser.parse_args(argv)

    workspace = args.workspace.resolve()
    try:
        file_name, text, source = resolve_form(
            args.form, workspace, form_file=args.form_file, fetch_org=not args.no_org
        )
        form = yaml.safe_load(text)
        by_id = {str(el.get("id")): el for el in _fields(form)}
        answers: dict[str, Any] = {}
        if args.answers:
            loaded = json.loads(args.answers.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise FormError("--answers must hold a JSON object")
            answers.update(loaded)
        answers.update(_parse_set(args.set, by_id))
        issue = compose_issue(
            text,
            answers,
            title=args.title,
            form_file=file_name,
            form_source=source,
            mechanical=mechanical_answers(form, workspace),
        )
    except (FormError, OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    handoff = args.handoff or (workspace / HANDOFF_REL)
    _write_json(
        handoff,
        {
            "schema": SCHEMA,
            "form": issue.form_file,
            "form_source": issue.form_source,
            "title": issue.title,
            "labels": issue.labels,
            "missing_required": issue.missing_required,
            "mechanical_filled": issue.mechanical_filled,
        },
    )
    print(issue.body, end="")
    if issue.missing_required:
        print(
            "FAIL: required fields not answered: "
            + ", ".join(issue.missing_required)
            + " — answer them (--set id=value); they are the reporter's judgment and are"
            + " never invented",
            file=sys.stderr,
        )
        return 2

    if args.create:
        repo = args.repo or repo_slug(workspace)
        if not repo:
            print(
                "FAIL: --repo not given and the workspace origin names no owner/name",
                file=sys.stderr,
            )
            return 1
        try:
            created = create_issue(repo, issue)
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            print(f"FAIL: issue not created in {repo}: {detail.strip()}", file=sys.stderr)
            return 1
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "repo": repo,
            "number": created.get("number"),
            "url": created.get("html_url"),
            "title": issue.title,
            "form": issue.form_file,
            "form_source": issue.form_source,
            "labels": issue.labels,
            "created_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _write_json(workspace / RECEIPT_REL, receipt)
        print(f"Opened: {receipt['url']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
