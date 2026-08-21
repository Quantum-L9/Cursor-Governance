#!/usr/bin/env python3
"""Runner-owned stack-doc proof for PE campaigns.

Infer API / MCP / install / Docker / named products from the activate seed,
fetch current docs (Context7 HTTP, then official page GET, plus live MCP
schemas), write $HOME/.l9/primed/<id>/stack-proof.json, and validate.
Agent-written receipts without fetch evidence fail closed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.program-execution.stack-proof.v1"
CONTEXT7_SEARCH = "https://context7.com/api/v2/libs/search"
CONTEXT7_CONTEXT = "https://context7.com/api/v2/context"
SECRET_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}"
    r"|CONTEXT7_API_KEY\s*=\s*\S+)",
    re.I,
)

API_RE = re.compile(
    r"\b(rest\s+api|graphql|openapi|vendor\s+api|https?://)\b",
    re.I,
)
MCP_RE = re.compile(r"\b(mcp__|mcp server|mcp tool|model context protocol)\b", re.I)
INSTALL_RE = re.compile(
    r"\b(pip install|npm install|uv add|brew install|requirements\.txt|package\.json)\b",
    re.I,
)
DOCKER_RE = re.compile(r"\b(docker(?:file| compose)?|container image)\b", re.I)
EXTERNAL_PRODUCT_RE = re.compile(
    r"\b(context7|dataforseo|semgrep|github actions|next\.js)\b",
    re.I,
)
FRAMEWORK_PRODUCT_RE = re.compile(r"\b(fastapi|neo4j|pydantic)\b", re.I)
FRAMEWORK_INTENT_RE = re.compile(
    r"\b(install|upgrade|migrate|docker|driver|cypher|gds|openapi|new)\b",
    re.I,
)
NEGATION_RE = re.compile(
    r"\b(?:no(?:t)?\s+new|do\s+not|don't|never|without|"
    r"not\s+(?:a\s+|the\s+)?(?:new|call|use|add|touch|implement))\b",
    re.I,
)
PURE_FILE_RE = re.compile(
    r"\b(edit existing|existing-file|typo|comment only|rename only)\b",
    re.I,
)
LANGUAGE_NAME_ISO_RE = re.compile(
    r"""language_name\s*[:=]\s*["']([a-z]{2})["']""",
    re.I,
)

FetchFn = Callable[[str, dict[str, str] | None], tuple[int, str]]


class StackProofError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def primed_receipt_path(campaign_id: str, primed_dir: Path | None = None) -> Path:
    root = primed_dir or (Path.home() / ".l9" / "primed")
    return root / campaign_id / "stack-proof.json"


def seed_text(seed: dict[str, Any]) -> str:
    parts = [
        str(seed.get("title") or ""),
        str(seed.get("objective") or ""),
        str(seed.get("problem_statement") or ""),
        json.dumps(seed.get("tasks") or [], sort_keys=True),
        json.dumps(seed.get("target") or {}, sort_keys=True),
        str(seed.get("docs_url") or ""),
    ]
    return "\n".join(parts)


def _prior_window(text: str, start: int, size: int = 96) -> str:
    return text[max(0, start - size) : start]


def _around_window(text: str, start: int, end: int, size: int = 48) -> str:
    return text[max(0, start - size) : min(len(text), end + size)]


def _is_negated(text: str, start: int) -> bool:
    return bool(NEGATION_RE.search(_prior_window(text, start)))


def infer_tools(seed: dict[str, Any]) -> list[dict[str, str]]:
    text = seed_text(seed)
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(name: str, kind: str) -> None:
        key = f"{kind}:{name.lower()}"
        if key in seen:
            return
        seen.add(key)
        found.append({"name": name, "kind": kind})

    for match in EXTERNAL_PRODUCT_RE.finditer(text):
        if not _is_negated(text, match.start()):
            add(match.group(0), "product")
    for match in FRAMEWORK_PRODUCT_RE.finditer(text):
        if _is_negated(text, match.start()):
            continue
        if FRAMEWORK_INTENT_RE.search(_around_window(text, match.start(), match.end())):
            add(match.group(0), "product")
    if API_RE.search(text):
        add("upstream-api", "api")
    if MCP_RE.search(text):
        add("mcp", "mcp")
    if INSTALL_RE.search(text):
        add("install", "install")
    if DOCKER_RE.search(text):
        add("docker", "docker")
    for item in seed.get("stack_tools") or []:
        if isinstance(item, dict) and item.get("name"):
            add(str(item["name"]), str(item.get("kind") or "product"))
        elif isinstance(item, str) and item.strip():
            add(item.strip(), "product")
    return found


def is_pure_file_edit(seed: dict[str, Any], inferred: list[dict[str, str]]) -> bool:
    if inferred:
        return False
    return bool(PURE_FILE_RE.search(seed_text(seed)))


def _headers() -> dict[str, str]:
    key = os.environ.get("CONTEXT7_API_KEY", "").strip()
    headers = {"User-Agent": "l9-pe-stack-proof/1"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def default_fetch(url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "l9-pe-stack-proof/1"})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=20, context=context) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise StackProofError(f"GET failed for {url}: {exc}") from exc


def extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) < 12:
            continue
        if SECRET_RE.search(line):
            continue
        if re.search(
            r"\b(must|required|do not|never|one of|enum|"
            r"language_name|language_code)\b",
            line,
            re.I,
        ):
            constraints.append(line[:240])
        if len(constraints) >= 8:
            break
    if not constraints and text.strip():
        snippet = " ".join(text.split())[:240]
        if snippet and not SECRET_RE.search(snippet):
            constraints.append(snippet)
    return constraints


def _digest(body: str) -> str:
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def context7_fetch(
    name: str,
    query: str,
    *,
    fetch: FetchFn,
) -> dict[str, Any] | None:
    if not os.environ.get("CONTEXT7_API_KEY", "").strip():
        raise StackProofError("CONTEXT7_API_KEY missing on the live stack-proof path")
    params = urllib.parse.urlencode({"libraryName": name, "query": query})
    status, body = fetch(f"{CONTEXT7_SEARCH}?{params}", _headers())
    if status != 200:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        return None
    first = results[0] if isinstance(results[0], dict) else {}
    library_id = str(first.get("id") or "")
    if not library_id:
        return None
    ctx_params = urllib.parse.urlencode({"libraryId": library_id, "query": query, "type": "json"})
    ctx_status, ctx_body = fetch(f"{CONTEXT7_CONTEXT}?{ctx_params}", _headers())
    if ctx_status != 200 or not ctx_body.strip():
        return None
    return {
        "source": "context7",
        "library_id": library_id,
        "page_urls": [CONTEXT7_CONTEXT],
        "body": ctx_body,
        "http_status": ctx_status,
        "digest": _digest(ctx_body),
        "bytes": len(ctx_body.encode("utf-8")),
    }


def official_docs_fetch(
    url: str,
    *,
    fetch: FetchFn,
    source: str,
) -> dict[str, Any] | None:
    if not url.startswith("https://"):
        raise StackProofError(f"docs_url must be https: {url}")
    status, body = fetch(url, {"User-Agent": "l9-pe-stack-proof/1"})
    if status != 200 or len(body.strip()) < 40:
        return None
    return {
        "source": source,
        "library_id": "",
        "page_urls": [url],
        "body": body,
        "http_status": status,
        "digest": _digest(body),
        "bytes": len(body.encode("utf-8")),
    }


def inspect_mcp_schemas(name: str) -> dict[str, Any] | None:
    roots = [
        Path.home() / ".claude" / "plugins" / "cache" / "claude-plugins-official" / "context7",
        Path.home() / ".cursor" / "mcp.json",
    ]
    blobs: list[str] = []
    urls: list[str] = []
    for root in roots:
        if root.is_file():
            text = root.read_text(encoding="utf-8", errors="replace")
            if name.lower() in text.lower() or "context7" in text.lower():
                blobs.append(text[:4000])
                urls.append(str(root))
        elif root.is_dir():
            for path in root.rglob("*.json"):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "resolve-library-id" in text or "query-docs" in text:
                    blobs.append(text[:4000])
                    urls.append(str(path))
                    break
    if not blobs:
        return None
    body = "\n".join(blobs)
    return {
        "source": "mcp_schema",
        "library_id": "",
        "page_urls": urls[:4],
        "body": body,
        "http_status": 200,
        "digest": _digest(body),
        "bytes": len(body.encode("utf-8")),
    }


def tool_cache_key(tool: dict[str, str], seed: dict[str, Any]) -> str:
    """Fingerprint of everything a single tool's proof actually depends on.

    Deliberately narrower than the seed: proving `neo4j` reads the tool's own
    identity, the objective used as the search query, and a docs override. It
    does not read the task list. Keying the whole receipt on the whole seed --
    which is what preparation used to do -- meant editing one task's validation
    command re-fetched every tool's documentation over the network, so the stage
    an operator repeats most was also the one that paid full price every time.
    """
    return _digest(
        json.dumps(
            {
                "name": tool.get("name"),
                "kind": tool.get("kind"),
                "query": str(seed.get("objective") or tool.get("name") or "")[:200],
                "docs_url": str(seed.get("docs_url") or tool.get("docs_url") or "").strip(),
            },
            sort_keys=True,
        )
    )


def fetch_one_tool(
    tool: dict[str, str],
    seed: dict[str, Any],
    *,
    fetch: FetchFn,
) -> dict[str, Any]:
    name = tool["name"]
    query = str(seed.get("objective") or name)[:200]
    docs_url = str(seed.get("docs_url") or tool.get("docs_url") or "").strip()
    last_error = "unknown"
    for attempt in (1, 2):
        fetched: dict[str, Any] | None = None
        try:
            if tool["kind"] == "mcp":
                fetched = inspect_mcp_schemas(name)
            if fetched is None:
                fetched = context7_fetch(name, query, fetch=fetch)
            if fetched is None and docs_url:
                fetched = official_docs_fetch(docs_url, fetch=fetch, source="docs_url")
            if fetched is None:
                last_error = f"Context7 miss and no validated official docs for {name}"
                continue
            constraints = extract_constraints(str(fetched.get("body") or ""))
            if not constraints:
                last_error = f"no constraints extracted for {name}"
                continue
            return {
                "name": name,
                "kind": tool["kind"],
                "source": fetched["source"],
                "library_id": fetched.get("library_id") or "",
                "page_urls": list(fetched.get("page_urls") or []),
                "constraints": constraints,
                "fetch_evidence": {
                    "http_status": fetched["http_status"],
                    "bytes": fetched["bytes"],
                    "digest": fetched["digest"],
                },
                "attempts": attempt,
            }
        except StackProofError as exc:
            last_error = str(exc)
    raise StackProofError(last_error)


def validate_receipt(receipt: dict[str, Any], inferred: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    if str(receipt.get("schema") or "") != SCHEMA:
        errors.append("receipt schema is not stack-proof.v1")
    if str(receipt.get("status") or "") != "pass":
        errors.append("receipt status is not pass")
    tools = receipt.get("tools")
    if not isinstance(tools, list):
        errors.append("receipt tools missing")
        return errors
    by_name = {str(item.get("name")): item for item in tools if isinstance(item, dict)}
    for tool in inferred:
        item = by_name.get(tool["name"])
        if item is None:
            errors.append(f"missing tool {tool['name']}")
            continue
        if not item.get("constraints"):
            errors.append(f"{tool['name']} has no constraints")
        evidence = item.get("fetch_evidence")
        if not isinstance(evidence, dict) or not evidence.get("digest"):
            errors.append(f"{tool['name']} missing fetch evidence")
        dumped = json.dumps(item, sort_keys=True)
        if SECRET_RE.search(dumped):
            errors.append(f"{tool['name']} receipt contains secret material")
    return errors


def seed_contradicts(seed: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    text = seed_text(seed)
    errors: list[str] = []
    constraints = []
    for item in receipt.get("tools") or []:
        if isinstance(item, dict):
            constraints.extend(str(c) for c in (item.get("constraints") or []))
    joined = "\n".join(constraints)
    iso = LANGUAGE_NAME_ISO_RE.search(text)
    if iso and re.search(r"language_name.*(English|full (english )?name)", joined, re.I):
        errors.append(
            f"seed sets language_name={iso.group(1)!r} but docs require the full English name"
        )
    return errors


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_receipt(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise StackProofError(f"stack-proof receipt missing: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StackProofError(f"stack-proof receipt is not JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise StackProofError("stack-proof receipt must be an object")
    return raw


def prove_stack(
    seed: dict[str, Any],
    *,
    primed_dir: Path | None = None,
    fetch: FetchFn | None = None,
    tool_cache: Any | None = None,
) -> dict[str, Any]:
    campaign_id = str(seed.get("campaign_id") or "").strip()
    if not campaign_id:
        raise StackProofError("seed campaign_id is required")
    inferred = infer_tools(seed)
    if not inferred:
        receipt = {
            "schema": SCHEMA,
            "campaign_id": campaign_id,
            "status": "pass",
            "pure_file_edit": is_pure_file_edit(seed, inferred),
            "skipped": "no-external-stack",
            "tools": [],
            "fetched_at": utc_now(),
            "validator": {"ok": True, "errors": []},
        }
        path = primed_receipt_path(campaign_id, primed_dir)
        write_receipt(path, receipt)
        receipt["path"] = str(path)
        return receipt
    fetch_fn = fetch or default_fetch
    tools: list[dict[str, Any]] = []
    if inferred:
        for tool in inferred:
            # Prove each tool once, and only the tools this campaign still owes
            # evidence for. The receipt is still whole -- coverage is a gate, not
            # an optimisation -- but a tool already proven costs no network.
            key = tool_cache_key(tool, seed)
            proven = tool_cache.get("stack_proof_tool", key) if tool_cache is not None else None
            if not isinstance(proven, dict):
                proven = fetch_one_tool(tool, seed, fetch=fetch_fn)
                if tool_cache is not None:
                    tool_cache.put("stack_proof_tool", key, proven)
            tools.append(proven)
    receipt = {
        "schema": SCHEMA,
        "campaign_id": campaign_id,
        "status": "pass",
        "pure_file_edit": not inferred,
        "tools": tools,
        "fetched_at": utc_now(),
        "validator": {"ok": True, "errors": []},
    }
    errors = validate_receipt(receipt, inferred)
    errors.extend(seed_contradicts(seed, receipt))
    if errors:
        receipt["status"] = "fail"
        receipt["validator"] = {"ok": False, "errors": errors}
        write_receipt(primed_receipt_path(campaign_id, primed_dir), receipt)
        raise StackProofError("stack-proof failed: " + "; ".join(errors))
    path = primed_receipt_path(campaign_id, primed_dir)
    write_receipt(path, receipt)
    receipt["path"] = str(path)
    return receipt


def require_existing_receipt(
    campaign_id: str,
    extra_text: str = "",
    *,
    primed_dir: Path | None = None,
) -> dict[str, Any]:
    inferred = infer_tools(
        {
            "campaign_id": campaign_id,
            "objective": extra_text,
            "problem_statement": extra_text,
            "tasks": [{"title": extra_text, "objective": extra_text}],
        }
    )
    path = primed_receipt_path(campaign_id, primed_dir)
    if not path.is_file():
        if not inferred:
            return {"status": "pass", "skipped": "no-receipt-no-new-tools"}
        raise StackProofError(
            "re-entry stack-proof required for new tools: "
            + ", ".join(tool["name"] for tool in inferred)
        )
    receipt = load_receipt(path)
    covered = {str(item.get("name", "")).lower() for item in receipt.get("tools") or []}
    missing = [tool["name"] for tool in inferred if tool["name"].lower() not in covered]
    if missing:
        raise StackProofError("re-entry stack-proof required for new tools: " + ", ".join(missing))
    errors = validate_receipt(receipt, [t for t in inferred if t["name"].lower() in covered])
    if receipt.get("status") != "pass" or errors:
        raise StackProofError("existing stack-proof is not valid for re-entry")
    return receipt
