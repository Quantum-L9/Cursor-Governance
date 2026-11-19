# Finding ownership and terminal dispositions

| Finding | Grade/status | Owner | Source | Observed problem | Disposition / next action |
|---|---|---|---|---|---|
| R01 | OPEN | OUT | SRC_EIE | SideEffectCoordinator pending/complete markers are process-local and can lose deferred CEG graph work on crash. | OPEN |
| R02 | OPEN | IN | SRC_EIE | GraphReturnChannel accepts graph inference to bounded process-local queue; queue full drops targets. | OPEN |
| R03 | OPEN | FEED | SRC_CEG | CEG feedback sender is admin-triggered and default-off; live automatic loop and signed caller key not demonstrated. | OPEN |
| R04 | OPEN | OUT | SRC_CEG | Predeployment report identifies unsupported score-invalidate action; current cache need unproven. | OPEN |
| R05 | OPEN | BASE | SRC_RUNTIME | No actual cross-restart two-direction replay receipt. | OPEN |

No in-scope finding disappears: FIXED + real proof, ALREADY_SATISFIED + proof, INVALID + disproof, BLOCKED + owner/wake. OUT_OF_SCOPE must cite why the finding is not a prerequisite. Optional adjacent improvements are not compulsory defects.
