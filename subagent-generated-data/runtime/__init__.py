"""Runtime for the L9 Subagent-Generated Data Law (l9.subagent_generated_data_law.v1).

Deterministic, dependency-light implementation of the enforcement sequence in
law §29: validate -> harvest -> classify -> dedupe -> conflict -> route ->
promote -> learning-closure. See ``law/SUBAGENT_GENERATED_DATA_LAW.md``.
"""

from __future__ import annotations

SCHEMA_VERSION = "l9.subagent_generated_data_law.v1"

__all__ = ["SCHEMA_VERSION"]
