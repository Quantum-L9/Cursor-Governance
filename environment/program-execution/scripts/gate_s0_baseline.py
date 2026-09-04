"""GATE-S0-BASELINE-CHARACTERIZED (W8/S0).

S0 requires the v2 baseline to be *frozen*: the counterexamples that
characterize v2 behavior must reproduce, and the freeze must name which commit
they were characterized against. Until now the gate existed only as prose in
the pipeline tracker, so the freeze could only ever be discharged by a person
re-reading it -- the same failure mode that let the registry assert a
reproduction claim that was false.

This module makes the gate runnable. It reports every condition individually
and exits non-zero naming the unmet ones, so "what blocks W8" is answered by a
command rather than by a document.

Three kinds of pin are deliberately distinct, because one field holding all
three is what let a forensic SHA sit in a position that reads as live:

``forensic_commit``
    The pe-v3-hardening baseline. Historical evidence, never a live pin.
``characterized_at``
    The commit at which every counterexample was proven to reproduce.
``pinned_to_main``
    Set once that work reaches ``origin/main``. ``null`` before then.

Drift is measured over the reproduction surface -- the counterexample entries
and the test files that reproduce them -- not over the repository manifest.
The manifest digests the registry, so recording a manifest digest *inside* the
registry would be self-referential and could never settle.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "conformance/counterexamples/v2-gaps-registry.yaml"
HARDENING = ROOT / "tests/hardening"

GATE_ID = "GATE-S0-BASELINE-CHARACTERIZED"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
BASELINE_REQUIRED_KEYS = (
    "forensic_commit",
    "characterized_at",
    "characterized_reproduction_digest",
    "orchestrator_plane_a",
    "pinned_to_main",
)


@dataclass(frozen=True)
class Condition:
    """One gate condition and why it did or did not hold.

    ``blocking`` separates what S0 is *about* from what merely travels with it.
    S0 asks whether the v2 baseline is characterized and frozen. Whether that
    characterization has reached ``origin/main`` is a release property, not a
    characterization property, and gating S0 on it makes the gate unclearable by
    any action available before merge - the failure mode where an
    uncleanable gate teaches people to route around it. A non-blocking
    condition is still evaluated, still printed, and still in the JSON; it just
    does not decide the exit code.
    """

    id: str
    passed: bool
    detail: str
    blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "passed": self.passed,
            "blocking": self.blocking,
            "detail": self.detail,
        }


def xfail_reasons(path: Path) -> dict[str, list[str]]:
    """Map each top-level test function to the reasons of its xfail markers.

    Reading decorators rather than importing keeps callers independent of
    whether a counterexample's mock code happens to import. Shared with the
    registry conformance suite so the two cannot disagree about what counts as
    a reproduction.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        reasons: list[str] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not (isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "xfail"):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "reason" and isinstance(keyword.value, ast.Constant):
                    value = keyword.value.value
                    if isinstance(value, str):
                        reasons.append(value)
        found[node.name] = reasons
    return found


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def reproduction_digest(
    registry: dict[str, Any],
    hardening: Path = HARDENING,
) -> str:
    """Fingerprint the reproduction surface.

    Covers each counterexample's identity triple and the bytes of the file that
    reproduces it. A counterexample renamed, repointed, or edited moves the
    digest; unrelated repository churn does not. Missing files contribute a
    sentinel rather than raising, so a drift report and a missing-file report
    stay separate findings.
    """
    digest = hashlib.sha256()
    for entry in sorted(registry.get("counterexamples", []), key=_entry_key):
        path = hardening / str(entry.get("test_file", ""))
        if path.is_file():
            body = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            body = "missing"
        digest.update(
            "\x1f".join(
                [
                    str(entry.get("id", "")),
                    str(entry.get("test_file", "")),
                    str(entry.get("test_function", "")),
                    body,
                ]
            ).encode("utf-8")
        )
        digest.update(b"\x1e")
    return "sha256:" + digest.hexdigest()


def _entry_key(entry: dict[str, Any]) -> str:
    return str(entry.get("id", ""))


def _git(*args: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout.strip()


def _check_baseline_shape(baseline: Any) -> Condition:
    if not isinstance(baseline, dict):
        return Condition("baseline_block_present", False, "registry has no baseline block")
    missing = [key for key in BASELINE_REQUIRED_KEYS if key not in baseline]
    if missing:
        return Condition(
            "baseline_block_present",
            False,
            f"baseline block missing {', '.join(missing)}",
        )
    return Condition("baseline_block_present", True, "all baseline keys present")


def _check_pin_separation(registry: dict[str, Any], baseline: dict[str, Any]) -> Condition:
    forensic = baseline.get("forensic_commit")
    legacy = registry.get("baseline_commit")
    if forensic != legacy:
        return Condition(
            "forensic_pin_not_live",
            False,
            f"baseline.forensic_commit {forensic} != baseline_commit {legacy}",
        )
    for field in ("characterized_at", "orchestrator_plane_a", "pinned_to_main"):
        value = baseline.get(field)
        if value is not None and value == forensic:
            return Condition(
                "forensic_pin_not_live",
                False,
                f"{field} holds the forensic commit {forensic}; it is evidence, not a live pin",
            )
    characterized = baseline.get("characterized_at")
    if not isinstance(characterized, str) or not SHA_PATTERN.match(characterized):
        return Condition(
            "forensic_pin_not_live",
            False,
            f"characterized_at is not a 40-character lowercase sha: {characterized!r}",
        )
    return Condition(
        "forensic_pin_not_live",
        True,
        "forensic, characterized, and main pins are distinct and well formed",
    )


def _check_reproduction(registry: dict[str, Any], hardening: Path) -> Condition:
    unmet: list[str] = []
    for entry in registry.get("counterexamples", []):
        entry_id = entry.get("id", "<unidentified>")
        path = hardening / str(entry.get("test_file", ""))
        if not path.is_file():
            unmet.append(f"{entry_id}: {entry.get('test_file')} does not exist")
            continue
        reasons = xfail_reasons(path).get(str(entry.get("test_function", "")), [])
        if not reasons:
            unmet.append(f"{entry_id}: {entry.get('test_function')} carries no xfail marker")
        elif not any(str(entry_id) in reason for reason in reasons):
            unmet.append(f"{entry_id}: xfail reason does not name it")
    if unmet:
        return Condition("counterexamples_reproduce", False, "; ".join(unmet))
    total = len(registry.get("counterexamples", []))
    return Condition(
        "counterexamples_reproduce",
        True,
        f"all {total} counterexamples reproduce as identified xfail tests",
    )


def _check_drift(
    registry: dict[str, Any],
    baseline: dict[str, Any],
    hardening: Path,
) -> Condition:
    recorded = baseline.get("characterized_reproduction_digest")
    actual = reproduction_digest(registry, hardening)
    if recorded != actual:
        return Condition(
            "reproduction_not_drifted",
            False,
            "reproduction surface moved since characterization: "
            f"recorded {recorded}, actual {actual}",
        )
    return Condition(
        "reproduction_not_drifted",
        True,
        "reproduction surface matches the characterized digest",
    )


def _check_main_pin(baseline: dict[str, Any], *, verify_ancestry: bool) -> Condition:
    """Durability of the pin. Advisory here; enforced at promotion.

    A branch commit is already immutable, so the freeze is verifiable without
    ``main``. What ``main`` adds is durability: a squash merge lands the same
    tree under a different sha, after which a pin naming only the branch commit
    survives solely on a closed PR ref. That matters when the baseline is
    promoted - S8's v2-to-v3 migration - not when it is characterized.
    """
    pinned = baseline.get("pinned_to_main")
    if pinned is None:
        return Condition(
            "pinned_to_main",
            False,
            "not pinned: the characterized work has not reached origin/main yet. "
            "Advisory at S0 - the baseline is frozen and verifiable without it. "
            "Set baseline.pinned_to_main to the merge commit for durability; "
            "promotion (S8) is where it becomes required.",
            blocking=False,
        )
    if not isinstance(pinned, str) or not SHA_PATTERN.match(pinned):
        return Condition(
            "pinned_to_main",
            False,
            f"pinned_to_main is not a 40-character lowercase sha: {pinned!r}",
            blocking=False,
        )
    if not verify_ancestry:
        return Condition(
            "pinned_to_main",
            True,
            f"pinned to {pinned} (ancestry not verified)",
            blocking=False,
        )
    code, _ = _git("merge-base", "--is-ancestor", pinned, "origin/main")
    if code != 0:
        return Condition(
            "pinned_to_main",
            False,
            f"{pinned} is not reachable from origin/main",
            blocking=False,
        )
    return Condition(
        "pinned_to_main",
        True,
        f"pinned to {pinned}, reachable from origin/main",
        blocking=False,
    )


def evaluate(
    *,
    registry_path: Path = REGISTRY,
    hardening: Path = HARDENING,
    verify_ancestry: bool = True,
) -> list[Condition]:
    """Run every gate condition. Conditions are independent by design.

    A single unmet condition must not hide the others: the point of the gate is
    to name everything still standing between here and a frozen baseline.
    """
    try:
        registry = load_registry(registry_path)
    except (OSError, yaml.YAMLError) as exc:
        return [Condition("registry_parses", False, f"{registry_path}: {exc}")]
    if not isinstance(registry, dict):
        return [Condition("registry_parses", False, "registry is not a mapping")]

    conditions = [Condition("registry_parses", True, str(registry_path))]
    shape = _check_baseline_shape(registry.get("baseline"))
    conditions.append(shape)
    conditions.append(_check_reproduction(registry, hardening))
    if not shape.passed:
        return conditions
    baseline = registry["baseline"]
    conditions.append(_check_pin_separation(registry, baseline))
    conditions.append(_check_drift(registry, baseline, hardening))
    conditions.append(_check_main_pin(baseline, verify_ancestry=verify_ancestry))
    return conditions


def blocking_failures(conditions: list[Condition]) -> list[Condition]:
    return [item for item in conditions if item.blocking and not item.passed]


def advisories(conditions: list[Condition]) -> list[Condition]:
    return [item for item in conditions if not item.blocking and not item.passed]


def render(conditions: list[Condition], *, as_json: bool) -> str:
    blocked = blocking_failures(conditions)
    advisory = advisories(conditions)
    if as_json:
        return json.dumps(
            {
                "gate": GATE_ID,
                "status": "pass" if not blocked else "blocked",
                "conditions": [item.to_dict() for item in conditions],
                "unmet_blocking": [item.id for item in blocked],
                "unmet_advisory": [item.id for item in advisory],
            },
            indent=2,
        )
    lines = [f"{GATE_ID}"]
    for item in conditions:
        if item.passed:
            mark = "PASS"
        else:
            mark = "FAIL" if item.blocking else "ADVISORY"
        lines.append(f"  [{mark}] {item.id}: {item.detail}")
    if blocked:
        lines.append(f"BLOCKED: {', '.join(item.id for item in blocked)}")
    else:
        lines.append("PASS: baseline characterized and frozen")
        if advisory:
            # Never silent. A passing gate that is carrying an unmet advisory
            # has to say so on the same screen, or "advisory" becomes "hidden".
            lines.append(f"  carrying advisory: {', '.join(item.id for item in advisory)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Evaluate {GATE_ID}")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    parser.add_argument(
        "--no-verify-ancestry",
        action="store_true",
        help="skip the origin/main reachability probe (offline or detached clones)",
    )
    args = parser.parse_args(argv)
    conditions = evaluate(verify_ancestry=not args.no_verify_ancestry)
    print(render(conditions, as_json=args.json))
    return 1 if blocking_failures(conditions) else 0


if __name__ == "__main__":
    sys.exit(main())
