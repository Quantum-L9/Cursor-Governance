"""Coding ontology entity types for Graphiti --use-custom-entities."""

from __future__ import annotations

from pydantic import BaseModel, Field

ENTITY_TYPE_NAMES = [
    "RepoManifest",
    "Module",
    "ADRDecision",
    "GMPPhase",
    "ModificationLock",
    "CIGotcha",
    "TechDebtItem",
    "Preference",
]

EDGE_TYPE_NAMES = [
    "DependsOn",
    "Supersedes",
    "IntegratesWith",
    "Blocks",
    "Documents",
    "ConflictsWith",
]


class RepoManifest(BaseModel):
    repo_slug: str
    github: str = ""
    stack: str = ""
    branch_model: dict = Field(default_factory=dict)


class Module(BaseModel):
    name: str
    layer: str = ""


class ADRDecision(BaseModel):
    adr_id: str
    title: str
    status: str = "accepted"


class GMPPhase(BaseModel):
    phase: str
    run_id: str = ""


class ModificationLock(BaseModel):
    locked_paths: list[str] = Field(default_factory=list)


class CIGotcha(BaseModel):
    rule: str
    module: str = ""


class TechDebtItem(BaseModel):
    summary: str
    module: str = ""


class Preference(BaseModel):
    key: str
    value: str = ""
