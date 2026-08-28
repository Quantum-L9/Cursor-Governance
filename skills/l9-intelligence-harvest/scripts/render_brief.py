#!/usr/bin/env python3
import sys

from _common import load_json
from validate_harvest import validate


def table_rows(items, fields):
    if not items:
        return ["_None._"]
    out = []
    for item in items:
        vals = []
        for field in fields:
            value = item.get(field, "UNKNOWN") if isinstance(item, dict) else item
            vals.append(str(value))
        out.append("- " + " | ".join(vals))
    return out


def render(h):
    errors = validate(h)
    if errors:
        raise ValueError(
            "harvest validation failed; renderer write forbidden: " + "; ".join(errors)
        )

    r = h["request"]
    lines = (
        [
            f"# Donor Harvest Brief — {r['donor']} → {r['beneficiary']} [{r['harvest_target']}]",
            "",
            "## Executive Picture",
            f"Status: {h['status']}. Highest-leverage nugget: {h.get('highest_leverage_nugget') or 'UNKNOWN'}.",
            "",
            "## Source Identity",
            f"```json\n{h.get('source_identity', {})}\n```",
            "",
            "## Inventory",
        ]
        + table_rows(h.get("inventory", []), ["path", "classification"])
        + [
            "",
            "## System Reconstruction",
            f"```json\n{h.get('system', {})}\n```",
            "",
            "## Surface / Target Graph",
        ]
        + table_rows(h.get("surfaces", []), ["item", "source", "visibility"])
        + [
            "",
            "## Duplicate and Drift Register",
        ]
        + table_rows(h.get("drift", []), ["behavior", "canonical_candidate", "resolution"])
        + [
            "",
            "## Nugget Register",
        ]
    )
    for concept in h.get("concepts", []):
        if concept.get("nugget"):
            lines.append(
                f"- {concept['id']} | {concept['name']} | {concept['disposition']} | "
                f"leverage={concept.get('leverage')} | destination={concept.get('beneficiary_destination')}"
            )
    lines += (
        ["", "## Beneficiary Fit"]
        + table_rows(
            [
                concept
                for concept in h.get("concepts", [])
                if concept.get("disposition")
                in {"PORT", "PORT_WITH_HARDENING", "CONFIGURE", "MERGE_WITH_EXISTING"}
            ],
            ["id", "disposition", "beneficiary_destination"],
        )
        + ["", "## Safety and Portability Audit"]
        + table_rows(h.get("safety", []), ["epistemic", "claim"])
        + ["", "## Concept Acceptance Tests"]
    )
    for concept in h.get("concepts", []):
        for test in concept.get("acceptance_tests", []):
            lines.append(
                f"- {concept['id']} | Given {test['given']} | When {test['when']} | "
                f"Then {test['then']} | Must not {test['must_not']}"
            )
    lines += (
        ["", "## Rejected and Local Concepts"]
        + table_rows(
            [
                concept
                for concept in h.get("concepts", [])
                if concept.get("disposition")
                in {"KEEP_LOCAL", "MIGRATION_CONTEXT", "REJECT", "UNKNOWN"}
            ],
            ["id", "disposition", "name"],
        )
        + [
            "",
            "## Highest-Leverage Next Action",
            h.get("highest_leverage_nugget") or "UNKNOWN",
            "",
            "## UNKNOWNs",
        ]
        + ["- " + unknown for unknown in h.get("unknowns", [])]
    )
    return "\n".join(lines) + "\n"


def main():
    harvest = load_json(sys.argv[1])
    output = render(harvest)
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        handle.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
