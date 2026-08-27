#!/usr/bin/env python3
# ACTIVATION_EVAL: deterministic fixture execution against the declared trigger surface.
import re
import sys

from _common import emit, fail, load_json


def _hit(prompt, terms):
    return any(re.search(re.escape(term), prompt, re.I) for term in terms)


def evaluate(ir, live_skills=None):
    authority = ir.get("authority", {})
    positive = authority.get("activation_triggers", [])
    negative = authority.get("non_activation_triggers", [])
    results = []
    for fixture in ir.get("activation_evals", []):
        prompt = fixture["prompt"]
        fired = _hit(prompt, positive) and not _hit(prompt, negative)
        if fixture["expect"] == "activate":
            ok = fired
        elif fixture["expect"] == "no_activate":
            ok = not fired
        else:
            ok = (not fired) and bool(fixture.get("route_to"))
            if ok and live_skills is not None and fixture["route_to"] not in live_skills:
                ok = False
        results.append(
            {
                "class": fixture["class"],
                "prompt": prompt,
                "expect": fixture["expect"],
                "route_to": fixture.get("route_to"),
                "fired": fired,
                "deterministic": True,
                "status": "pass" if ok else "fail",
            }
        )
    classes = {result["class"] for result in results}
    gaps = [name for name in ("positive", "negative", "sibling_collision") if name not in classes]
    failed = [result for result in results if result["status"] == "fail"]
    return {
        "stage": "ACTIVATION_EVAL",
        "status": "FAIL" if failed or gaps else "PASS",
        "results": results,
        "missing_classes": gaps,
        "failed_count": len(failed),
    }


def main(argv):
    if len(argv) < 2:
        return fail("usage: evaluate_activation.py <skill-ir.json>")
    result = evaluate(load_json(argv[1]))
    return emit(result, 2 if result["status"] == "FAIL" else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
