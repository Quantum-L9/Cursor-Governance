import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from rank_nuggets import rank


def test_ranking_deterministic_tie_break():
    base = {
        "concepts": [
            {"id": "b", "nugget": True, "disposition": "PORT", "leverage": 5, "compounding": 5},
            {"id": "a", "nugget": True, "disposition": "PORT", "leverage": 5, "compounding": 5},
        ]
    }
    assert rank(base)["highest_leverage_nugget"] == "a"
