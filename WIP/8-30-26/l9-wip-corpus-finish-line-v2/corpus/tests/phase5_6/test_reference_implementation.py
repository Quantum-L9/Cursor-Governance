from implementation.phase5_6.models import *
from implementation.phase5_6.work_context_compiler import WorkContextCompiler, ContextBudgetError
from implementation.phase5_6.work_unit_compiler import WorkUnitCompiler
from implementation.phase5_6.leverage_planner import LeveragePlanner
from implementation.phase5_6.build_wave_planner import BuildWavePlanner

class FakePort:
    def __init__(self, records): self.records = tuple(records)
    def resolve_entities(self, objective): return ("repo:cog",)
    def search(self, objective, focal_entities, limit): return self.records
    def traverse(self, entity_ids, edge_types, depth):
        assert "REFERENCES" not in edge_types and "DUPLICATE_OF" not in edge_types
        return ()
    def hydrate(self, record_ids):
        ids = set(record_ids); return tuple(r for r in self.records if r.record_id in ids)

def fixture():
    return (
        CandidateRecord("r1", "a1", "spec", "task", authority=5, relevance=5, dependency_necessity=5, evidence_quality=5, estimated_tokens=50, metadata={"work_key":"context", "work_title":"Build context", "work_objective":"Implement context compiler", "capabilities_unlocked":["compiled-context"], "completion_evidence":["tests-pass"]}),
        CandidateRecord("r2", "a2", "conflict", "task", authority=4, relevance=4, evidence_quality=4, estimated_tokens=30, conflict_ids=("c1",), metadata={"work_key":"context", "work_title":"Build context", "work_objective":"Implement context compiler"}),
        CandidateRecord("r3", "a3", "noise", "other", relevance=0, estimated_tokens=200),
    )

def test_pipeline():
    packet = WorkContextCompiler(FakePort(fixture())).compile("build context", "snap:1", 100)
    assert {i.disposition for i in packet.items} == {Disposition.REQUIRED, Disposition.CONFLICTING}
    assert any(x.record.record_id == "r3" for x in packet.exclusions)
    units = WorkUnitCompiler().compile(packet)
    assert len(units) == 1
    d = LeverageDimensions(5,5,5,4,5,4,2,2,1)
    planned = (LeveragePlanner().apply(units[0], d),)
    assert planned[0].priority_class == PriorityClass.FOUNDATIONAL_UNLOCK
    waves = BuildWavePlanner().compile(packet.objective, planned, packet.graph_snapshot_id)
    assert len(waves.waves) == 1

def test_budget_fails_closed():
    try:
        WorkContextCompiler(FakePort(fixture())).compile("build context", "snap:1", 60)
    except ContextBudgetError:
        return
    raise AssertionError("expected budget failure")
