"""Shared L9 skill-routing scorer — Cursor-primary ownership (CANONICAL_LAW §2.1).

Surface adapters import this module; they must not own scoring logic.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("ops/generated/skill-registry.json")

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
    """Resolve governance root that contains the skill registry."""
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / REGISTRY_REL).is_file():
            return candidate
    home = Path.home() / ".cursor-governance"
    if (home / REGISTRY_REL).is_file():
        return home
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        if (parent / REGISTRY_REL).is_file():
            return parent
    return home


def load_registry(root: Path) -> dict[str, Any]:
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
    blocked_primaries: set[str] = set()
    best: tuple[int, dict[str, Any], str] | None = None
    for route in routing.get("routes", []):
        primary = str(route.get("primary", ""))
        if not primary or primary in explicit:
            continue
        if any(phrase_hit(normalized, phrase) for phrase in route.get("negative_signals", [])):
            blocked_primaries.add(primary)
            continue
        positives = [
            phrase for phrase in route.get("positive_signals", []) if phrase_hit(normalized, phrase)
        ]
        score = len(positives) * int(route.get("signal_weight", 4))
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
            score = 0
        if best is None or score > best[0]:
            best = (score, route, "route")

    threshold = int(routing.get("force_threshold", 8))
    advisory = int(routing.get("advisory_threshold", max(6, threshold - 2)))

    if best is not None and best[0] >= threshold:
        score, route, source = best
        max_supporting = int(routing.get("max_supporting", 2))
        supporting = [
            name
            for name in route.get("supporting", [])
            if name in known and name not in explicit and name != route.get("primary")
        ][:max_supporting]
        return {
            "route_id": route.get("id", "unknown"),
            "primary": route["primary"],
            "supporting": supporting,
            "score": score,
            "source": source,
        }

    # Description fallback: only when no high-confidence route matched.
    desc_best: tuple[int, dict[str, Any]] | None = None
    for skill in registry.get("skills", []):
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
            "supporting": supporting[: int(routing.get("max_supporting", 2))],
            "score": score,
            "source": "description",
        }

    # Soft route hit below force_threshold still surfaces as advisory when useful.
    if best is not None and best[0] >= advisory:
        score, route, source = best
        max_supporting = int(routing.get("max_supporting", 2))
        supporting = [
            name
            for name in route.get("supporting", [])
            if name in known and name not in explicit and name != route.get("primary")
        ][:max_supporting]
        return {
            "route_id": route.get("id", "unknown"),
            "primary": route["primary"],
            "supporting": supporting,
            "score": score,
            "source": "advisory_route",
        }

    return None
