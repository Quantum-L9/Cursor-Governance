"""The pipeline loads whatever order `sys.path` happens to be in.

Two modules are named `receipts`: this directory's, and
`orchestration/receipts.py`, which the pipeline's modules import by the bare
name. Both directories sit on `sys.path`, so the bare name used to resolve to
whichever came first -- and an unrelated caller that had put the ingress
directory first made the pipeline fail with an `ImportError` that outcome
publication swallowed as "non-blocking".
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

INGRESS = Path(__file__).resolve().parents[1]
ORCHESTRATION = INGRESS.parent / "orchestration"
REPO = Path(__file__).resolve().parents[5]
for entry in (str(INGRESS), str(REPO)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import ingest  # noqa: E402

PIPELINE_MODULES = ("receipts", "delivery_worker", "processor", "state_store")


@pytest.fixture
def pristine_imports() -> Iterator[None]:
    """Forget the pipeline modules and restore the interpreter state afterwards."""
    saved_modules = {
        name: sys.modules.pop(name) for name in PIPELINE_MODULES if name in sys.modules
    }
    saved_path = list(sys.path)
    try:
        yield
    finally:
        for name in PIPELINE_MODULES:
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        sys.path[:] = saved_path


def _path_with_first(first: Path, second: Path) -> list[str]:
    rest = [entry for entry in sys.path if entry not in {str(first), str(second)}]
    return [str(first), str(second), *rest]


def test_the_pipeline_loads_when_ingress_precedes_orchestration(pristine_imports: None) -> None:
    sys.path[:] = _path_with_first(INGRESS, ORCHESTRATION)
    loaded = ingest._load_pipeline()
    assert [item.__name__ for item in loaded][:1] == ["GeneratedDataProcessor"]
    assert Path(sys.modules["receipts"].__file__).resolve() == ORCHESTRATION / "receipts.py"


def test_the_pipeline_loads_when_orchestration_precedes_ingress(pristine_imports: None) -> None:
    sys.path[:] = _path_with_first(ORCHESTRATION, INGRESS)
    ingest._load_pipeline()
    assert Path(sys.modules["receipts"].__file__).resolve() == ORCHESTRATION / "receipts.py"


def test_a_cached_ingress_module_under_the_bare_name_is_replaced(pristine_imports: None) -> None:
    """The state the campaign suite reached: the wrong module already cached."""
    sys.modules["receipts"] = ingest.ingress_receipts
    ingest._load_pipeline()
    bound = sys.modules["receipts"]
    assert hasattr(bound, "ProcessingReceiptChain")
    assert bound is not ingest.ingress_receipts


def test_the_ingress_module_keeps_its_own_key(pristine_imports: None) -> None:
    ingest._load_pipeline()
    assert Path(ingest.ingress_receipts.__file__).resolve() == INGRESS / "receipts.py"
    assert hasattr(ingest.ingress_receipts, "write_ingress")
