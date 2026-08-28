#!/usr/bin/env python3
"""Build orchestration state.yaml from an emitted contract set (Stage 1 -> Stage 2 bridge).

    python make_state.py <out_dir> <state.yaml> [--chain-on merged|green]

<out_dir> is the directory compile_contract.py emitted (contains PR-*.contract.json). Produces a
state.yaml with one ordered item per contract, all status: pending.
"""

import argparse
import glob
import json
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("state")
    ap.add_argument("--chain-on", default="green", choices=["green", "merged"])
    a = ap.parse_args()
    import yaml

    files = sorted(glob.glob(str(pathlib.Path(a.out_dir) / "PR-*.contract.json")))
    if not files:
        raise SystemExit(f"no PR-*.contract.json in {a.out_dir}")
    items, campaign = [], None
    for f in files:
        c = json.loads(pathlib.Path(f).read_text())
        if campaign is None:
            campaign = {
                "target_repo": c["target_repo"],
                "target_branch": c["target_branch"],
                "out_dir": a.out_dir,
            }
        pc = c.get("prerequisite_contract")
        # prerequisite is the PRIOR chain contract; only track intra-chain prereqs
        items.append(
            {
                "key": c["contract_id"].split("-PR-")[-1].split("-v")[0],
                "contract_id": c["contract_id"],
                "title": c["pr_title"],
                "prerequisite": None,
                "status": "pending",
                "_prereq_id": pc["id"] if pc else None,
            }
        )
    # wire intra-chain prerequisites (prior item in the emitted order whose id matches)
    ids = {it["contract_id"] for it in items}
    for i, it in enumerate(items):
        pid = it.pop("_prereq_id")
        it["prerequisite"] = pid if (pid in ids) else None
    state = {"campaign": campaign, "chain_on": a.chain_on, "items": items}
    pathlib.Path(a.state).write_text(yaml.safe_dump(state, sort_keys=False))
    print(f"wrote {a.state}: {len(items)} contracts, chain_on={a.chain_on}")


if __name__ == "__main__":
    main()
