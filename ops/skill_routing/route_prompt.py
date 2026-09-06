"""Shared L9 skill-routing scorer — Cursor-primary ownership (CANONICAL_LAW §2.1).

Surface adapters import this module; they must not own scoring logic.

Doctrine:
  * auto_invoke / model_allowed — may force-route (source: route | advisory_route | description)
  * explicit_only + route.hint_allowed — may surface Read/attach only (source: explicit_hint)
  * explicit_only without hint_allowed — never scored
  * Recommendation is routing evidence; an auto_invoke / model_allowed skill
    contract is the authority for that skill's declared actions
  * explicit_hint still grants no mutation authority by itself
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("ops/generated/skill-registry.json")


def _sibling(name: str):
    """Import a sibling module whether loaded as a package or by file path.

    Surface hooks load this file with ``spec_from_file_location`` (no
    package), so a plain relative import is not always available.
    """
    if __package__:
        try:
            return importlib.import_module(f"{__package__}.{name}")
        except ImportError:
            pass
    module_name = f"l9_skill_routing_sibling_{name}"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise ImportError(f"cannot load sibling module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_STOPWORDS = frozenset(
    """
    a an the and or for with from into onto over under about after before
    when where what which while that this these those your you using use
    used uses make makes made need needs needed across is are was were be
    been being to of in on at by as if so it its their them they we our can
    could should would may might will just also more most such than then
    there here any all not no yes via per
    """.split()
)


def normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9+#./_-]+", " ", text.lower()).split())


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > 2:
        return 99
    prev = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        curr = [i]
        for j, rch in enumerate(right, start=1):
            cost = 0 if lch == rch else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def phrase_hit(prompt: str, phrase: str) -> bool:
    norm_phrase = normalize(phrase)
    if not norm_phrase:
        return False
    if norm_phrase in prompt:
        return True
    phrase_tokens = norm_phrase.split()
    prompt_tokens = prompt.split()
    n = len(phrase_tokens)
    if n < 2 or len(prompt_tokens) < n:
        return False
    # Contiguous window only — bag-of-words matching is too loose for short phrases
    # like "review pr". Edit-distance applies to long tokens (typo tolerance).
    for start in range(len(prompt_tokens) - n + 1):
        window = prompt_tokens[start : start + n]
        matched = True
        for got, want in zip(window, phrase_tokens):
            if got == want:
                continue
            if len(want) >= 6 and _edit_distance(got, want) <= 2:
                continue
            matched = False
            break
        if matched:
            return True
    return False


def resolve_root(start: Path | None = None) -> Path:
    """Resolve governance root — delegates to the shared registry layer."""
    return _sibling("registry").resolve_governance_root(start)


def load_registry(root: Path) -> dict[str, Any]:
    """Raw registry dict for scoring. Validation lives in registry.load_registry."""
    path = root / REGISTRY_REL
    return json.loads(path.read_text(encoding="utf-8"))


def _significant_tokens(text: str) -> set[str]:
    return {tok for tok in normalize(text).split() if len(tok) >= 4 and tok not in _STOPWORDS}


def _ngrams(tokens: list[str], size: int) -> set[str]:
    if len(tokens) < size:
        return set()
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def score_description_match(prompt: str, skill: dict[str, Any]) -> int:
    """Fallback scorer from skill when_to_use / description when no route fires."""
    corpus = normalize(
        f"{skill.get('when_to_use', '')} {skill.get('description', '')} {skill.get('reason', '')}"
    )
    if not corpus:
        return 0
    corpus_tokens = [tok for tok in corpus.split() if tok not in _STOPWORDS and len(tok) >= 4]
    if not corpus_tokens:
        return 0
    score = 0
    for size in (3, 2):
        for phrase in _ngrams(corpus_tokens, size):
            if phrase_hit(prompt, phrase):
                score += 5 if size == 3 else 3
    prompt_tokens = _significant_tokens(prompt)
    overlap = prompt_tokens & set(corpus_tokens)
    # Cap unigram contribution so generic words cannot dominate.
    score += min(len(overlap), 4) * 2
    name = str(skill.get("name", ""))
    if name and name in prompt:
        score += 12
    slug = name.removeprefix("l9-").replace("-", " ")
    if " " in slug and phrase_hit(prompt, slug):
        score += 12
    elif len(slug) >= 10 and phrase_hit(prompt, slug):
        score += 12
    return score


def _score_route(normalized: str, route: dict[str, Any], primary: str) -> int:
    positives = [
        phrase for phrase in route.get("positive_signals", []) if phrase_hit(normalized, phrase)
    ]
    weight = int(route.get("signal_weight", 4))
    score = len(positives) * weight
    slug = primary.removeprefix("l9-").replace("-", " ")
    if primary in normalized:
        score += 20
    elif " " in slug and phrase_hit(normalized, slug):
        # Multi-word slugs only (avoid "plan" matching "architecture plan").
        score += 20
    elif len(slug) >= 10 and phrase_hit(normalized, slug):
        score += 20
    required = route.get("required_any", [])
    if required and not any(phrase_hit(normalized, phrase) for phrase in required):
        return 0
    return score


def _hint_gate(route: dict[str, Any], score: int) -> int:
    """Fail-closed for explicit hint routes: required_any match or score >= 2× weight."""
    weight = int(route.get("signal_weight", 4))
    required = route.get("required_any", [])
    if required:
        # required_any already enforced in _score_route; one solid hit is enough.
        return score
    if score < 2 * weight:
        return 0
    return score


def _supporting(
    route: dict[str, Any],
    known: dict[str, Any],
    explicit: set[str],
    max_supporting: int,
) -> list[str]:
    return [
        name
        for name in route.get("supporting", [])
        if name in known and name not in explicit and name != route.get("primary")
    ][:max_supporting]


def retrieve_candidates(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Eligible routes for scoring — the retrieval boundary.

    Immediate version: every route whose primary is scoreable (model_allowed,
    or explicit_only with ``hint_allowed``). A future bounded index may narrow
    this set; the scorer below stays the same.
    """
    known = {item["name"]: item for item in registry.get("skills", [])}
    explicit = {name for name, item in known.items() if item.get("invocation") == "explicit_only"}
    eligible: list[dict[str, Any]] = []
    for route in registry.get("routing", {}).get("routes", []):
        primary = str(route.get("primary", ""))
        if not primary:
            continue
        if primary in explicit and not bool(route.get("hint_allowed", False)):
            continue
        eligible.append(route)
    return eligible


def _route_rank(score: int, route: dict[str, Any]) -> tuple[int, int, str]:
    """Explicit deterministic ranking: score DESC, priority DESC, route_id ASC.

    Returned as a max-key so manifest order never decides a tie
    (VSP-P2-002). ``route_id`` is negated lexically via the tuple compare in
    ``_better``.
    """
    return (score, int(route.get("priority", 0)), str(route.get("id", "")))


def _better(candidate: tuple[int, int, str], incumbent: tuple[int, int, str] | None) -> bool:
    if incumbent is None:
        return True
    if candidate[:2] != incumbent[:2]:
        return candidate[:2] > incumbent[:2]
    return candidate[2] < incumbent[2]


def rank_candidates(
    normalized: str, routes: list[dict[str, Any]], explicit: set[str]
) -> tuple[tuple[int, dict[str, Any], str] | None, set[str]]:
    """Score eligible routes; return (best, blocked_primaries)."""
    blocked_primaries: set[str] = set()
    best: tuple[int, dict[str, Any], str] | None = None
    best_rank: tuple[int, int, str] | None = None
    for route in routes:
        primary = str(route.get("primary", ""))
        hint_allowed = bool(route.get("hint_allowed", False))
        if any(phrase_hit(normalized, phrase) for phrase in route.get("negative_signals", [])):
            blocked_primaries.add(primary)
            continue
        score = _score_route(normalized, route, primary)
        source = "route"
        if primary in explicit and hint_allowed:
            score = _hint_gate(route, score)
            source = "explicit_hint"
        rank = _route_rank(score, route)
        if _better(rank, best_rank):
            best = (score, route, source)
            best_rank = rank
    return best, blocked_primaries


def route_prompt(prompt: str, registry: dict[str, Any]) -> dict[str, Any] | None:
    routing = registry.get("routing", {})
    normalized = normalize(prompt)
    if not normalized:
        return None
    for pattern in routing.get("trivial_patterns", []):
        if re.search(str(pattern), normalized, flags=re.IGNORECASE):
            return None

    known = {item["name"]: item for item in registry.get("skills", [])}
    explicit = {name for name, item in known.items() if item.get("invocation") == "explicit_only"}
    best, blocked_primaries = rank_candidates(normalized, retrieve_candidates(registry), explicit)

    threshold = int(routing.get("force_threshold", 8))
    advisory = int(routing.get("advisory_threshold", max(6, threshold - 2)))
    max_supporting = int(routing.get("max_supporting", 2))

    if best is not None and best[0] >= threshold:
        score, route, source = best
        return {
            "route_id": route.get("id", "unknown"),
            "primary": route["primary"],
            "supporting": _supporting(route, known, explicit, max_supporting),
            "score": score,
            "source": source,
        }

    # Description fallback: only model_allowed skills when no high-confidence route matched.
    # Ties resolve by skill name ASC so registry order never decides.
    desc_best: tuple[int, dict[str, Any]] | None = None
    for skill in sorted(registry.get("skills", []), key=lambda item: str(item.get("name", ""))):
        name = str(skill.get("name", ""))
        if (
            not name
            or skill.get("invocation") != "model_allowed"
            or name in explicit
            or name in blocked_primaries
        ):
            continue
        score = score_description_match(normalized, skill)
        if desc_best is None or score > desc_best[0]:
            desc_best = (score, skill)

    if desc_best is not None and desc_best[0] >= max(threshold, advisory + 2):
        score, skill = desc_best
        supporting: list[str] = []
        if "l9-structured-reasoning" in known and skill["name"] != "l9-structured-reasoning":
            supporting = ["l9-structured-reasoning"]
        return {
            "route_id": f"description:{skill['name']}",
            "primary": skill["name"],
            "supporting": supporting[:max_supporting],
            "score": score,
            "source": "description",
        }

    # Soft route hit below force_threshold — never advisory for explicit_hint (stricter).
    if best is not None and best[0] >= advisory and best[2] != "explicit_hint":
        score, route, source = best
        return {
            "route_id": route.get("id", "unknown"),
            "primary": route["primary"],
            "supporting": _supporting(route, known, explicit, max_supporting),
            "score": score,
            "source": "advisory_route",
        }

    return None
