# Finding ownership and terminal dispositions

| Finding | Grade/status | Owner | Source | Observed problem | Disposition / next action |
|---|---|---|---|---|---|
| D01 | OPEN | DOC | SRC_EIE | Root README absent; AGENTS.md self-claims authority, mixes obsolete review tiers and contains long stale instructions. | OPEN |
| D02 | OPEN | DOC | SRC_EIE | docs/INVARIANTS.md was last reviewed April 2026; lacks domain-neutral product invariants, misstates some enforcement and mislinks AGENTS path. | OPEN |
| D03 | OPEN | DOC | SRC_EIE | Historical ADR-011 identifier collision plus obsolete ADR/current architecture descriptions require an index and source-linked successor. | OPEN |
| D04 | OPEN | DOC | SRC_EIE | EIE docs-consistency.yml silently skips checks of absent root AGENT.md and INVARIANTS.md, while actual Repo.mk owns eight stages. | OPEN |
| D05 | OPEN | ESPEC | SRC_RUNTIME | Published CEG PlasticOS pack/current tenant database unavailable for exact dual-spec verification; historical fixture is not admission. | OPEN |
| D06 | OPEN | SEAM | SRC_RUNTIME | Actual Gate key policy and signed EIE/CEG cross-route live rail not yet observed. | OPEN |

No in-scope finding disappears: FIXED + real proof, ALREADY_SATISFIED + proof, INVALID + disproof, BLOCKED + owner/wake. OUT_OF_SCOPE must cite why the finding is not a prerequisite. Optional adjacent improvements are not compulsory defects.
