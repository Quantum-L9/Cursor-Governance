#!/usr/bin/env python3
"""Full-throttle flag inventory: enumerate off-by-default flags, classify each by
danger polarity, and emit a deterministic single-line flip transform.

This is the safety core of the skill's *full-throttle activation mode* (see
`references/full-throttle-activation.md`). That mode deliberately relaxes
Identity-Lock #1's `dormant_by_design` clause **for testing** — flipping
off-by-default flags on, proving them with the repo's own tests, and packaging
the flip as a review-required PR. It pays for that relaxation with a
conservative, polarity-aware danger classifier: a flag is NEVER auto-flipped
when turning it on either *enables a dangerous action* (delete/deploy/charge/…)
or *disables a safety control* (auth/tls/verify/sandbox/…).

Stdlib-only, read-only, deterministic. Enumerating and classifying mutates
nothing; `flip_flag()` returns edited text, it does not write. The core scan /
PR-pack pipeline and its `dormant_by_design` guarantees are untouched by this
module.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# Reuse the scanner's staged-intent detection and file-walk law so the two
# stay consistent (a flag the core scan calls dormant_by_design is `staged`
# here too, and still danger-excluded if dangerous).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_capabilities import (  # noqa: E402
    SKIP_DIRS,
    STAGED_MARKER,
    intent_scan,
    is_excluded,
    is_test_file,
)

PY_EXT = {".py"}
CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
ENV_NAMES = {".env"}

# Names that read as an off-by-default *feature* or *safety* flag. Deliberately
# inclusive of disable_/skip_/bypass_ names so the danger classifier can hold
# them, but trimmed of noisy predicate stems (is/has/with/only) that match
# computed booleans (`is_dominated`, `any_strict`) rather than config flags.
FLAG_NAME = re.compile(
    r"(?:^|_)(?:enable[d]?|disable[d]?|feature|flag|toggle|use|allow|"
    r"skip|bypass|suppress|ignore|without|unsafe|insecure|force|debug|verbose|"
    r"experimental|beta|preview|dry|auto|live|prod)(?:_|$)"
    r"|_enabled?$|_disabled?$|_flag$|_feature$|_toggle$|_mode$|_on$",
    re.IGNORECASE,
)
# JSON-Schema / meta keywords that appear as `key: false` but are schema
# declarations, not feature flags.
SCHEMA_KEYWORDS = {
    "additionalproperties", "uniqueitems", "required", "nullable", "deprecated",
    "readonly", "writeonly", "strict", "exclusiveminimum", "exclusivemaximum",
    "propertynames", "unevaluatedproperties", "additionalitems",
}
# Path segments that mark scratch / harvested / work-in-progress trees whose
# contents are not the repo's live config.
_NOISE_SEG = re.compile(r"(?:^|[\s_\-/])(?:wip|harvested|current_work|backup|backups|snapshot)(?:$|[\s_\-/])", re.IGNORECASE)
# Config files that are templates / versioned specs / examples, not the runtime
# config the engine loads — flipping a flag in them changes nothing at runtime.
_NONRUNTIME_CFG = re.compile(
    r"(?:^|/)_?template[\w.\-]*\.(?:ya?ml|json|toml|ini)$"      # _template.yaml
    r"|[-_]v\d+(?:[._]\d+)*[\w.\-]*\.(?:ya?ml|json|toml|ini)$"  # ...-v1.1.0.yaml / _v0.3.0.yaml
    r"|[-_]spec[-_]v[\w.\-]*\.(?:ya?ml|json)$"                  # ...-spec-v1.1.0.yaml
    r"|(?:^|/)(?:example|sample)[\w.\-]*\.(?:ya?ml|json|toml|ini)$",
    re.IGNORECASE,
)

# --- danger vocabulary (polarity-aware) ---------------------------------------
# Turning a flag False->True that ENABLES one of these actions is danger.
DANGER_ENABLE = {
    "delete", "deletion", "purge", "drop", "wipe", "destroy", "truncate",
    "erase", "remove", "prune", "reset", "overwrite", "clobber",
    "deploy", "publish", "release", "ship", "promote", "rollout",
    "push", "upload", "commit", "merge", "apply",
    "charge", "bill", "billing", "payment", "paid", "invoice", "purchase",
    "live", "prod", "production", "mainnet", "real",
    "send", "email", "sms", "notify", "webhook", "broadcast", "dispatch",
    "external", "remote", "network", "egress", "outbound", "internet",
    "migrate", "migration", "seed", "backfill", "execute", "exec", "shell",
    "auto", "autonomous", "nonstop", "unattended", "unlimited", "infinite",
    # supply-chain / code-execution and open-access hardenings — enabling these
    # weakens a control (yarn enableScripts, public sign-up, anonymous access).
    "script", "scripts", "plugin", "plugins", "eval",
    "signup", "register", "registration", "anonymous", "public", "guest",
}
# Substring-danger (high-confidence destructive/financial/deploy roots) — catch
# `autodeploy`, `livecharge`, `deletestore` even without an underscore boundary.
DANGER_SUBSTR = (
    "delete", "purge", "destroy", "deploy", "publish", "release", "charge",
    "billing", "wipe", "truncate", "mainnet", "production",
    "sign_up", "signup", "enable_scripts", "allow_scripts",
)
# Prefixes that, turned on, DISABLE a control -> danger.
DISABLE_PREFIX = ("disable", "bypass", "skip", "ignore", "suppress", "no", "without", "un")
# Safety/verification roots — disabling any of these is danger.
SAFETY_TOKENS = {
    "auth", "authn", "authz", "login", "permission", "permissions", "acl",
    "rbac", "secret", "secrets", "credential", "credentials", "token", "tokens",
    "tls", "ssl", "https", "cert", "certificate", "verify", "verification",
    "validate", "validation", "check", "checks", "sandbox", "guard", "guardrail",
    "safety", "safe", "confirm", "confirmation", "approval", "approve", "sign",
    "signature", "encrypt", "encryption", "audit", "limit", "limits", "quota",
    "throttle", "ratelimit", "backpressure", "csrf", "cors", "sanitize",
    "sanitization", "escape", "firewall",
}
# Config parent-block names whose activation is sensitive: a bare `enabled: false`
# under one of these blocks (e.g. `pii.enabled`, `auth.enabled`) is context-danger
# even though the leaf key carries no danger token.
SENSITIVE_BLOCKS = {
    "pii", "privacy", "gdpr", "phi", "pci",
    "auth", "authn", "authz", "security", "secret", "secrets",
    "credential", "credentials", "compliance", "audit_export",
    "retention", "encryption", "encrypt", "tls", "ssl", "permission",
    "permissions", "rbac", "acl", "billing", "payment", "charge",
    "deploy", "deployment", "publish", "release", "killswitch", "kill_switch",
    "external", "webhook", "egress", "quota",
}
GENERIC_GATE = {"enabled", "enable", "disabled", "disable", "on", "off", "active", "enforce"}

# Names that, turned on, are self-evidently unsafe regardless of surroundings.
ALWAYS_DANGER = {
    "unsafe", "insecure", "unverified", "danger", "dangerous", "force",
    "allow_insecure", "no_verify", "noverify", "trust_all", "verify_none",
    "disable_ssl_verify", "allow_all",
}


def _tokens(name: str) -> list[str]:
    """Split a flag name into lowercase word tokens (snake_case + camelCase)."""
    parts = re.split(r"[^A-Za-z0-9]+", name)
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", p):
            out.append(w.lower())
    return out


def classify_flag(name: str, context: str, *, staged: bool,
                  parent: str | None = None,
                  overrides: dict | None = None) -> tuple[str, str]:
    """Classify flipping `name` False->True. Returns (classification, reason).

    classification ∈ {danger, staged, safe}. Adapter overrides win first:
    `.optimize-scan.json` may carry {full_throttle:{never_flip:[...],
    always_flip:[...], danger_tokens:[...]}}.
    """
    overrides = overrides or {}
    low = name.lower()
    never = {n.lower() for n in overrides.get("never_flip", [])}
    always = {n.lower() for n in overrides.get("always_flip", [])}
    extra_danger = {t.lower() for t in overrides.get("danger_tokens", [])}
    if low in never:
        return "danger", "adapter never_flip block-list"
    if low in always:
        return "safe", "adapter always_flip allow-list"

    toks = set(_tokens(name))
    # Context-aware: a generic gate under a sensitive parent block is danger.
    if parent and parent.lower() in SENSITIVE_BLOCKS and (low in GENERIC_GATE or toks & GENERIC_GATE):
        return "danger", f"flip enables the sensitive '{parent}' block (context-aware)"
    if parent and parent.lower() in SENSITIVE_BLOCKS:
        return "danger", f"flag sits inside the sensitive '{parent}' block"
    if low in ALWAYS_DANGER or toks & {"unsafe", "insecure", "unverified", "danger"}:
        return "danger", "flip enables a self-evidently unsafe state"
    if toks & extra_danger or any(t in low for t in extra_danger):
        return "danger", "adapter danger_tokens match"

    # 1. flipping ON enables a dangerous action
    if toks & DANGER_ENABLE:
        hit = sorted(toks & DANGER_ENABLE)[0]
        return "danger", f"flip enables a dangerous action ('{hit}')"
    if any(s in low for s in DANGER_SUBSTR):
        return "danger", "flip enables a destructive/deploy/financial action"

    # 2. flipping ON disables a safety control (disable_/skip_/bypass_/no_ + safety)
    head = (_tokens(name) or [""])[0]
    if head in DISABLE_PREFIX:
        rest = set(_tokens(name)[1:])
        if head in ("disable", "bypass") or rest & SAFETY_TOKENS:
            return "danger", f"flip disables a control ('{head}_…')"

    # 3. staged rollout / dormant_by_design intent (Identity-Lock #1)
    if staged or STAGED_MARKER.search(context or ""):
        return "staged", "repo intent marks this a staged rollout / dormant_by_design"

    return "safe", "off-by-default flag with no danger signal or staged intent"


# --- flip transform -----------------------------------------------------------
_PY_VALUE = re.compile(r"(?P<pre>[:=]\s*)(?P<val>False|0)(?P<post>\b)")
_CFG_VALUE = re.compile(r"(?P<pre>[:=]\s*)(?P<val>false|False|0)(?P<post>\b)")


def flip_flag(text: str, flag: dict) -> str:
    """Deterministic single-line edit: on `flag['line']`, flip the first
    False/0/false value token after the `=`/`:` to True/1/true. Idempotent
    (already-True lines are untouched) and never mutates any other line."""
    lines = text.splitlines(keepends=True)
    idx = flag["line"] - 1
    if not (0 <= idx < len(lines)):
        return text
    line = lines[idx]
    pat = _PY_VALUE if flag.get("lang") == "python" else _CFG_VALUE

    def repl(m: re.Match) -> str:
        val = m.group("val")
        new = {"False": "True", "false": "true", "0": "1"}[val]
        return m.group("pre") + new + m.group("post")

    new_line = pat.sub(repl, line, count=1)
    if new_line == line:
        return text
    lines[idx] = new_line
    return "".join(lines)


# --- inventory ----------------------------------------------------------------
def _py_flags(rel: str, text: str) -> list[dict]:
    out: list[dict] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    lines = text.splitlines()

    def _emit_assign(node: ast.Assign) -> None:
        val = node.value
        is_off = (isinstance(val, ast.Constant) and val.value is False) or (
            isinstance(val, ast.Constant) and val.value == 0 and val.value is not False)
        if not is_off:
            return
        for tgt in node.targets:
            name = getattr(tgt, "id", None)  # bare Name only (module/class constant)
            if not name or name.startswith("_"):  # skip locals-by-convention and dunders
                continue
            if FLAG_NAME.search(name):
                ctx = lines[node.lineno - 1] if 0 <= node.lineno - 1 < len(lines) else ""
                out.append({"flag": name, "file": rel, "line": node.lineno,
                            "current": "False" if val.value is False else "0",
                            "lang": "python", "kind": "python_assignment", "context": ctx})

    # Module-level and class-level assignments only — a real feature flag is a
    # module/class constant, not a loop/function-local boolean (which is where the
    # `is_dominated`/`any_strict` false positives came from).
    scopes: list[list] = [tree.body]
    scopes += [n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for body in scopes:
        for node in body:
            if isinstance(node, ast.Assign):
                _emit_assign(node)

    for node in ast.walk(tree):
        # argparse add_argument(..., action="store_true") / default=False
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_argument":
            name = None
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--"):
                    name = a.value.lstrip("-").replace("-", "_")
            store_true = default_false = False
            for kw in node.keywords:
                if kw.arg == "action" and isinstance(kw.value, ast.Constant) and kw.value.value == "store_true":
                    store_true = True
                if kw.arg == "default" and isinstance(kw.value, ast.Constant) and kw.value.value in (False, 0):
                    default_false = True
            if name and (store_true or default_false):
                ctx = lines[node.lineno - 1] if 0 <= node.lineno - 1 < len(lines) else ""
                out.append({"flag": name, "file": rel, "line": node.lineno,
                            "current": "store_true" if store_true else "default=False",
                            "lang": "python", "kind": "argparse_flag", "context": ctx,
                            "no_flip": True})  # CLI default; documented, not auto-flipped in-file
    return out


# Match any `key: false/0` pair; the flag-name filter runs in Python so the
# regex does not have to encode the flag vocabulary (avoids leading-char
# backtracking that dropped names like "feature_new_ui").
_CFG_OFF = re.compile(
    r"""["']?([A-Za-z_][\w.\-]*)["']?\s*[:=]\s*(false|False|0)\b""")


_YAML_KEY = re.compile(r"^(\s*)([A-Za-z_][\w.\-]*)\s*:")


def _config_flags(rel: str, text: str) -> list[dict]:
    out: list[dict] = []
    is_yaml = rel.rsplit(".", 1)[-1].lower() in ("yaml", "yml")
    stack: list[tuple[int, str]] = []  # (indent, key) — nearest-ancestor block chain
    for i, line in enumerate(text.splitlines(), start=1):
        if is_yaml:
            km = _YAML_KEY.match(line)
            if km:
                indent = len(km.group(1))
                while stack and stack[-1][0] >= indent:
                    stack.pop()
        for m in _CFG_OFF.finditer(line):
            name = m.group(1)
            if name.lower() in SCHEMA_KEYWORDS or not FLAG_NAME.search(name):
                continue
            parent = stack[-1][1] if (is_yaml and stack) else None
            out.append({"flag": name, "file": rel, "line": i,
                        "current": m.group(2), "lang": "config",
                        "kind": "config_key", "context": line, "parent": parent})
        if is_yaml and km:
            stack.append((indent, km.group(2)))
    return out


def _iter(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        if _NOISE_SEG.search("/" + rel):  # scratch / harvested / WIP trees
            continue
        suffix = path.suffix.lower()
        name = path.name.lower()
        if name.endswith(".schema.json") or name.endswith(".schema.yaml"):
            continue  # JSON/YAML Schema, not repo config
        if suffix in PY_EXT:
            yield path, rel, "python"
        elif suffix in CONFIG_EXT or name in ENV_NAMES:
            if _NONRUNTIME_CFG.search("/" + rel):
                continue  # template / versioned / example spec — not runtime config
            yield path, rel, "config"


def inventory_flags(root: Path, overrides: dict | None = None) -> list[dict]:
    """Enumerate every off-by-default flag under `root`, classify each, and
    attach the flip decision. Test files and archived/scratch trees are read for
    context but excluded from activation candidates."""
    staged_flags, _ = intent_scan(root)
    overrides = overrides or _load_overrides(root)
    rows: list[dict] = []
    for path, rel, lang in _iter(root):
        if is_test_file(rel) or is_excluded(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found = _py_flags(rel, text) if lang == "python" else _config_flags(rel, text)
        for f in found:
            staged = f["flag"] in staged_flags or bool(STAGED_MARKER.search(f.get("context", "")))
            classification, reason = classify_flag(
                f["flag"], f.get("context", ""), staged=staged,
                parent=f.get("parent"), overrides=overrides)
            if f.get("no_flip"):
                decision, dec_reason = "hold", "argparse CLI default — surface in docs, not flipped in source"
            elif classification == "danger":
                decision, dec_reason = "hold", reason
            elif classification == "staged":
                decision, dec_reason = "hold", reason
            else:
                decision, dec_reason = "flip", reason
            row = dict(f)
            row.pop("context", None)
            row.update({"polarity": "off->on", "classification": classification,
                        "decision": decision, "reason": dec_reason})
            rows.append(row)
    rows.sort(key=lambda r: (r["file"], r["line"], r["flag"]))
    return rows


def _load_overrides(root: Path) -> dict:
    cfg = root / ".optimize-scan.json"
    if not cfg.is_file():
        return {}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data.get("full_throttle", {}) if isinstance(data, dict) else {}


def summarize(rows: list[dict]) -> dict:
    by_class: dict[str, int] = {}
    for r in rows:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
    return {
        "total": len(rows),
        "by_classification": by_class,
        "flip_candidates": sorted(r["flag"] for r in rows if r["decision"] == "flip"),
        "held_danger": sorted(r["flag"] for r in rows if r["classification"] == "danger"),
        "held_staged": sorted(r["flag"] for r in rows if r["classification"] == "staged"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.repo.is_dir():
        print(f"FAIL: not a directory: {args.repo}", file=sys.stderr)
        return 2
    rows = inventory_flags(args.repo)
    result = {
        "repo": str(args.repo),
        "flags": rows,
        "summary": summarize(rows),
        "note": "Off-by-default flag inventory for full-throttle activation. decision=flip "
                "means non-danger and non-staged (empirical back-out in full_throttle.py still "
                "validates it against the repo's own tests). classification=danger is NEVER "
                "flipped (polarity-aware: enables a dangerous action OR disables a safety "
                "control); classification=staged is dormant_by_design (Identity-Lock #1).",
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
