#!/usr/bin/env python3
"""Cluster extracted doctrine into duplicate and potential-conflict families.
This is an analysis stage, not an authority stage.
The clusterer intentionally distinguishes:
- exact duplicates;
- lexical/semantic near-duplicates;
- potential contradictions.
"Potential conflict" is intentionally conservative language. This module is not
permitted to choose which statement is correct, infer precedence, or mutate a
contract. A conflict cluster exists to create a bounded human/contract-authoring
review unit.
The algorithm is deterministic and network-free. Its fingerprints are included
in the doctrine ratchet so new contradiction surfaces cannot silently appear.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from extract_doctrine import (
    ROOT,
    extract_repository,
    load_serialized,
    normalize_space,
    serialize_output,
    stable_digest,
    stable_id,
)

CLUSTERER_VERSION = "1.0.0"
DEFAULT_DUPLICATE_THRESHOLD = 0.78
DEFAULT_CONFLICT_THRESHOLD = 0.64
MIN_SHARED_CONTENT_TOKENS = 2
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.:/-]*", re.I)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "by",
    "do",
    "does",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "may",
    "must",
    "never",
    "not",
    "of",
    "on",
    "only",
    "or",
    "shall",
    "should",
    "that",
    "the",
    "their",
    "then",
    "this",
    "to",
    "when",
    "with",
    "without",
}
TOKEN_CANONICALIZATION = {
    "repos": "repository",
    "repo": "repository",
    "repositories": "repository",
    "ssot": "source_of_truth",
    "github": "git",
    "prs": "pull_request",
    "pr": "pull_request",
    "pull-requests": "pull_request",
    "validates": "validate",
    "validated": "validate",
    "validation": "validate",
    "verifies": "verify",
    "verified": "verify",
    "verification": "verify",
    "forbidden": "prohibit",
    "prohibited": "prohibit",
    "prohibits": "prohibit",
    "requires": "require",
    "required": "require",
    "mandatory": "require",
}
NEGATIVE_EFFECTS = {"prohibit", "stop"}
POSITIVE_EFFECTS = {"permit", "require"}
COMPATIBLE_EFFECT_PAIRS = {
    ("constrain", "require"),
    ("require", "constrain"),
    ("attest", "require"),
    ("require", "attest"),
}


class UnionFind:
    """Minimal deterministic union-find for connected cluster construction."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            self.parent[root_left] = root_right
            return
        if self.rank[root_left] > self.rank[root_right]:
            self.parent[root_right] = root_left
            return
        self.parent[root_right] = root_left
        self.rank[root_left] += 1


def _record_id(record: dict[str, Any]) -> str:
    return str(record["extraction_identity"]["extraction_id"])


def _record_text(record: dict[str, Any]) -> str:
    source = record.get("source", {})
    semantics = record.get("normalized_semantics", {})
    pieces = [
        str(semantics.get("subject") or ""),
        str(semantics.get("action") or ""),
        str(semantics.get("object") or ""),
        str(source.get("exact_text") or ""),
    ]
    return normalize_space(" ".join(pieces)).casefold()


def _canonical_token(token: str) -> str:
    token = token.casefold().strip("._:/-")
    return TOKEN_CANONICALIZATION.get(token, token)


def semantic_tokens(record: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for token in TOKEN_RE.findall(_record_text(record)):
        canonical = _canonical_token(token)
        if not canonical:
            continue
        if canonical in STOPWORDS:
            continue
        if len(canonical) < 2:
            continue
        tokens.add(canonical)
    return tokens


def token_bigrams(tokens: set[str]) -> set[str]:
    ordered = sorted(tokens)
    return {f"{left}::{right}" for left, right in zip(ordered, ordered[1:], strict=False)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def classification_similarity(
    left: dict[str, Any],
    right: dict[str, Any],
) -> float:
    left_class = left.get("classification", {})
    right_class = right.get("classification", {})
    score = 0.0
    if left_class.get("candidate_kind") == right_class.get("candidate_kind"):
        score += 0.40
    if left_class.get("sharedness") == right_class.get("sharedness"):
        score += 0.30
    if left_class.get("doctrine_strength") == right_class.get("doctrine_strength"):
        score += 0.20
    if left_class.get("risk") == right_class.get("risk"):
        score += 0.10
    return score


def semantic_similarity(
    left: dict[str, Any],
    right: dict[str, Any],
) -> float:
    left_tokens = semantic_tokens(left)
    right_tokens = semantic_tokens(right)
    if len(left_tokens & right_tokens) < MIN_SHARED_CONTENT_TOKENS:
        return 0.0
    token_score = jaccard(left_tokens, right_tokens)
    bigram_score = jaccard(
        token_bigrams(left_tokens),
        token_bigrams(right_tokens),
    )
    class_score = classification_similarity(left, right)
    score = 0.62 * token_score + 0.23 * bigram_score + 0.15 * class_score
    return round(score, 4)


def normalized_proposition(record: dict[str, Any]) -> str:
    """Normalize lexical form without attempting semantic rewriting."""
    tokens = sorted(semantic_tokens(record))
    effect = str(record.get("normalized_semantics", {}).get("effect", "unknown"))
    return f"{effect}|{' '.join(tokens)}"


def exact_duplicate_key(record: dict[str, Any]) -> str:
    """Fingerprint normalized source wording while preserving normative effect."""
    source_text = normalize_space(str(record.get("source", {}).get("exact_text", ""))).casefold()
    effect = str(record.get("normalized_semantics", {}).get("effect", "unknown"))
    return stable_digest(
        {
            "text": source_text,
            "effect": effect,
        }
    )


def semantic_fingerprint(record: dict[str, Any]) -> str:
    """Stable semantic-ish fingerprint used by downstream ratcheting."""
    classification = record.get("classification", {})
    semantics = record.get("normalized_semantics", {})
    return stable_digest(
        {
            "proposition": normalized_proposition(record),
            "kind": classification.get("candidate_kind"),
            "sharedness": classification.get("sharedness"),
            "effect": semantics.get("effect"),
        }
    )


def _effects_conflict(left_effect: str, right_effect: str) -> bool:
    if left_effect == right_effect:
        return False
    if (left_effect, right_effect) in COMPATIBLE_EFFECT_PAIRS:
        return False
    if left_effect in NEGATIVE_EFFECTS and right_effect in POSITIVE_EFFECTS:
        return True
    if right_effect in NEGATIVE_EFFECTS and left_effect in POSITIVE_EFFECTS:
        return True
    return False


def _candidate_pairs(
    records: list[dict[str, Any]],
) -> list[tuple[int, int]]:
    """Build candidate pairs through an inverted-token index.
    This avoids an unnecessary full O(n²) comparison once doctrine volume grows.
    """
    token_index: dict[str, set[int]] = defaultdict(set)
    record_tokens: list[set[str]] = []
    for index, record in enumerate(records):
        tokens = semantic_tokens(record)
        record_tokens.append(tokens)
        for token in tokens:
            token_index[token].add(index)
    shared_counts: dict[tuple[int, int], int] = defaultdict(int)
    for indices in token_index.values():
        ordered = sorted(indices)
        for left_offset, left in enumerate(ordered):
            for right in ordered[left_offset + 1 :]:
                shared_counts[(left, right)] += 1
    pairs = [pair for pair, count in shared_counts.items() if count >= MIN_SHARED_CONTENT_TOKENS]
    return sorted(pairs)


def _connected_components(
    size: int,
    edges: list[tuple[int, int]],
) -> list[list[int]]:
    union_find = UnionFind(size)
    for left, right in edges:
        union_find.union(left, right)
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(size):
        groups[union_find.find(index)].append(index)
    return sorted(
        (sorted(group) for group in groups.values() if len(group) > 1),
        key=lambda group: group,
    )


def _cluster_id(
    prefix: str,
    records: list[dict[str, Any]],
    member_indices: list[int],
) -> str:
    member_ids = sorted(_record_id(records[index]) for index in member_indices)
    return stable_id(prefix, *member_ids)


def _member_summary(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source", {})
    classification = record.get("classification", {})
    semantics = record.get("normalized_semantics", {})
    return {
        "extraction_id": _record_id(record),
        "semantic_fingerprint": semantic_fingerprint(record),
        "path": source.get("path"),
        "line_start": source.get("line_start"),
        "section": source.get("section"),
        "candidate_kind": classification.get("candidate_kind"),
        "doctrine_strength": classification.get("doctrine_strength"),
        "sharedness": classification.get("sharedness"),
        "risk": classification.get("risk"),
        "effect": semantics.get("effect"),
    }


def cluster_records(
    records: list[dict[str, Any]],
    *,
    duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
    conflict_threshold: float = DEFAULT_CONFLICT_THRESHOLD,
) -> dict[str, Any]:
    """Build deterministic duplicate and potential-conflict clusters."""
    ordered = sorted(
        records,
        key=lambda record: (
            str(record.get("source", {}).get("path", "")).casefold(),
            int(record.get("source", {}).get("line_start", 0)),
            _record_id(record),
        ),
    )
    exact_groups: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(ordered):
        exact_groups[exact_duplicate_key(record)].append(index)
    duplicate_edges: set[tuple[int, int]] = set()
    duplicate_pair_details: list[dict[str, Any]] = []
    conflict_edges: list[tuple[int, int]] = []
    conflict_pair_details: list[dict[str, Any]] = []
    for indices in exact_groups.values():
        if len(indices) < 2:
            continue
        for offset, left in enumerate(indices):
            for right in indices[offset + 1 :]:
                duplicate_edges.add((left, right))
                duplicate_pair_details.append(
                    {
                        "left": _record_id(ordered[left]),
                        "right": _record_id(ordered[right]),
                        "similarity": 1.0,
                        "relation": "exact_duplicate",
                    }
                )
    for left, right in _candidate_pairs(ordered):
        left_record = ordered[left]
        right_record = ordered[right]
        similarity = semantic_similarity(left_record, right_record)
        if similarity <= 0:
            continue
        left_effect = str(left_record.get("normalized_semantics", {}).get("effect", "unknown"))
        right_effect = str(right_record.get("normalized_semantics", {}).get("effect", "unknown"))
        if _effects_conflict(left_effect, right_effect):
            if similarity >= conflict_threshold:
                conflict_edges.append((left, right))
                pair_fingerprint = stable_digest(
                    {
                        "left": semantic_fingerprint(left_record),
                        "right": semantic_fingerprint(right_record),
                        "effects": sorted([left_effect, right_effect]),
                    }
                )
                conflict_pair_details.append(
                    {
                        "pair_fingerprint": pair_fingerprint,
                        "left": _record_id(left_record),
                        "right": _record_id(right_record),
                        "left_effect": left_effect,
                        "right_effect": right_effect,
                        "similarity": similarity,
                        "status": "potential_conflict_needs_review",
                    }
                )
            continue
        if similarity >= duplicate_threshold:
            duplicate_edges.add((left, right))
            duplicate_pair_details.append(
                {
                    "left": _record_id(left_record),
                    "right": _record_id(right_record),
                    "similarity": similarity,
                    "relation": "near_duplicate",
                }
            )
    duplicate_components = _connected_components(
        len(ordered),
        sorted(duplicate_edges),
    )
    conflict_components = _connected_components(
        len(ordered),
        sorted(set(conflict_edges)),
    )
    duplicate_clusters: list[dict[str, Any]] = []
    for component in duplicate_components:
        member_ids = {_record_id(ordered[index]) for index in component}
        relevant_pairs = [
            pair
            for pair in duplicate_pair_details
            if pair["left"] in member_ids and pair["right"] in member_ids
        ]
        relation = (
            "exact_duplicate"
            if relevant_pairs
            and all(pair["relation"] == "exact_duplicate" for pair in relevant_pairs)
            else "near_duplicate"
        )
        similarity_floor = min(
            (float(pair["similarity"]) for pair in relevant_pairs),
            default=1.0,
        )
        duplicate_clusters.append(
            {
                "cluster_id": _cluster_id(
                    "DUP",
                    ordered,
                    component,
                ),
                "cluster_type": relation,
                "member_count": len(component),
                "similarity_floor": round(similarity_floor, 4),
                "members": [_member_summary(ordered[index]) for index in component],
            }
        )
    conflict_clusters: list[dict[str, Any]] = []
    for component in conflict_components:
        member_ids = {_record_id(ordered[index]) for index in component}
        relevant_pairs = [
            pair
            for pair in conflict_pair_details
            if pair["left"] in member_ids and pair["right"] in member_ids
        ]
        effects = sorted(
            {
                str(ordered[index].get("normalized_semantics", {}).get("effect", "unknown"))
                for index in component
            }
        )
        conflict_clusters.append(
            {
                "cluster_id": _cluster_id(
                    "CONFLICT",
                    ordered,
                    component,
                ),
                "cluster_type": "potential_conflict",
                "status": "unresolved_requires_review",
                "member_count": len(component),
                "competing_effects": effects,
                "members": [_member_summary(ordered[index]) for index in component],
                "conflict_pairs": sorted(
                    relevant_pairs,
                    key=lambda pair: (
                        str(pair["left"]),
                        str(pair["right"]),
                    ),
                ),
            }
        )
    duplicate_clusters.sort(key=lambda cluster: str(cluster["cluster_id"]))
    conflict_clusters.sort(key=lambda cluster: str(cluster["cluster_id"]))
    conflict_pair_details.sort(
        key=lambda pair: (
            str(pair["pair_fingerprint"]),
            str(pair["left"]),
            str(pair["right"]),
        )
    )
    return {
        "format_version": 1,
        "clusterer_version": CLUSTERER_VERSION,
        "algorithm": {
            "name": "deterministic_lexical_semantic_v1",
            "duplicate_threshold": duplicate_threshold,
            "conflict_threshold": conflict_threshold,
            "minimum_shared_content_tokens": MIN_SHARED_CONTENT_TOKENS,
            "authority": "analysis_only",
            "automatic_conflict_resolution": False,
        },
        "statistics": {
            "record_count": len(ordered),
            "duplicate_cluster_count": len(duplicate_clusters),
            "potential_conflict_cluster_count": len(conflict_clusters),
            "potential_conflict_pair_count": len(conflict_pair_details),
        },
        "duplicate_clusters": duplicate_clusters,
        "conflict_clusters": conflict_clusters,
        "conflict_pairs": conflict_pair_details,
    }


def _records_from_loaded(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        records = value.get("records")
    else:
        records = value
    if not isinstance(records, list):
        raise ValueError("input must contain a records list")
    validated: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"records[{index}] must be a mapping")
        validated.append(record)
    return validated


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Cluster extracted doctrine into duplicate and potential-conflict families.")
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root used when extraction input is not supplied.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Existing extraction YAML/JSON/JSONL. Otherwise scan skills now.",
    )
    parser.add_argument(
        "--surface-mode",
        choices=("governance-text", "all-text"),
        default="governance-text",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
    )
    parser.add_argument(
        "--include-code-fences",
        action="store_true",
    )
    parser.add_argument(
        "--duplicate-threshold",
        type=float,
        default=DEFAULT_DUPLICATE_THRESHOLD,
    )
    parser.add_argument(
        "--conflict-threshold",
        type=float,
        default=DEFAULT_CONFLICT_THRESHOLD,
    )
    parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if not 0 <= args.duplicate_threshold <= 1:
            raise ValueError("duplicate threshold must be in [0, 1]")
        if not 0 <= args.conflict_threshold <= 1:
            raise ValueError("conflict threshold must be in [0, 1]")
        if args.input is not None:
            records = _records_from_loaded(load_serialized(args.input))
        else:
            extraction = extract_repository(
                args.root,
                surface_mode=args.surface_mode,
                include_archived=args.include_archived,
                include_code_fences=args.include_code_fences,
            )
            if extraction["statistics"]["error_count"]:
                raise RuntimeError("extraction produced integrity errors; clustering aborted")
            records = extraction["records"]
        result = cluster_records(
            records,
            duplicate_threshold=args.duplicate_threshold,
            conflict_threshold=args.conflict_threshold,
        )
        rendered = serialize_output(result, args.format)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(f"DOCTRINE_CLUSTER_ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
