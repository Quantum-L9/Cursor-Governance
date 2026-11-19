# Finding ownership and terminal dispositions

| Finding | Grade/status | Owner | Source | Observed problem | Disposition / next action |
|---|---|---|---|---|---|
| B01 | OPEN | CRM | SRC_EIE | Live CRM metadata/record intake is not yet connected to a comprehensive graph seeding flow. | OPEN |
| B02 | OPEN | GRAPH | SRC_CEG | CEG graph sync primitives need an integrated source-aware node/relationship fixture and typed readback. | OPEN |
| B03 | OPEN | ASSOC | SRC_EIE | Observed associations need source-specific namespace and existing node dependencies enforced end to end. | OPEN |
| B04 | OPEN | QA | SRC_RUNTIME | CRM bootstrap graph is not proven in running Neo4j/Gate rail. | OPEN |

No in-scope finding disappears: FIXED + real proof, ALREADY_SATISFIED + proof, INVALID + disproof, BLOCKED + owner/wake. OUT_OF_SCOPE must cite why the finding is not a prerequisite. Optional adjacent improvements are not compulsory defects.
