# Topology judgment

Scan tool: `skills/l9-skill-compiler/scripts/scan_skill_topology.py`. Live skills enumerated: 56. Archived directories are not candidates.

## First subject

Domain text included the word "storage". Decision: `EXTEND_EXISTING`. Nearest name: `l9-mac-storage-triage`. Capability tokens in common: `skill`, `storage`.

That skill diagnoses macOS disk pressure and reclaims caches. It does not own violation briefs. The overlap is the word "storage" in the subject, not a shared capability.

## Corrected subject

- proposed_name: `l9-violations`
- domain: `governance violation reporting`
- stated_objective: `report a governance or process violation, keep the brief only inside this pack, and retain prior briefs until they are addressed`

Decision: `ESCALATE_TO_BOUNDED_LLM`. Nearest capability token: `governance` on `l9-governance-symlinks` (overlap 1). That skill wires governance symlinks. It does not store violation briefs.

## Judgment

`CREATE_NEW`.

| Candidate | Owns this capability? |
|---|---|
| `l9-mac-storage-triage` | No. Disk triage. |
| `l9-governance-symlinks` | No. Symlink wiring. |
| `l9-incident-response` | No. Production SEV triage and postmortems. |
| `l9-chat-extraction` | No. It sends a lesson to memory. This pack does not. |
| `commands/_archived/violation.md` | Not live. The slash command stays archived. |
| `skills/_archived/l9-governance-wiring` | Not live. Its replacements do not record a violation. |

No live skill owns "record a governance breach and keep the brief in one pack".
