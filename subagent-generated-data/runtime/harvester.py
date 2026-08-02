"""Harvesting: extract generated data units from a validated packet (law §5.5).

Capture-before-distillation (law §13): harvesting only lifts already-validated
units out of the packet; it never rewrites statements or drops provenance.
"""

from __future__ import annotations

from .models import GeneratedDataUnit, SubagentDataPacket


def harvest(packet: SubagentDataPacket) -> list[GeneratedDataUnit]:
    """Return the generated data units carried by a validated packet."""

    return list(packet.generated_data_units)
