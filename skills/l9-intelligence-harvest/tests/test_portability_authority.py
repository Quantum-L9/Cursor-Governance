import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from qualify_nuggets import portability_closed


def test_runtime_dependency_requires_probe_and_failure_behavior():
    portability = {
        "donor_identity_independent": True,
        "donor_execution_authority_independent": True,
        "donor_infrastructure_independent": True,
        "incidental_implementation_independent": True,
        "donor_runtime_required": True,
        "external_dependency": {
            "target": "donor-runtime",
            "probe": "runtime --version",
            "failure_behavior": "BLOCKED",
        },
    }
    assert portability_closed({"portability": portability}) is True
    portability["external_dependency"]["probe"] = ""
    assert portability_closed({"portability": portability}) is False


def test_donor_machinery_cannot_qualify_as_portable_without_independence():
    portability = {
        "donor_identity_independent": True,
        "donor_execution_authority_independent": False,
        "donor_infrastructure_independent": True,
        "incidental_implementation_independent": True,
        "donor_runtime_required": False,
        "external_dependency": None,
    }
    assert portability_closed({"portability": portability}) is False
