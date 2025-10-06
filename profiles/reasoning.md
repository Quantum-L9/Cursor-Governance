# Reasoning — Modes, Self‑Verification, and Evidence Discipline

## Goals
Make high-velocity decisions **without** sacrificing correctness. Use modes that scale depth to the task while ensuring every deliverable passes the final governance checks.

---

## Modes
- **Light YNP (Default):** concise, pragmatic steps; minimal ceremony; produce; move.
- **Heavy Forge (Enable with: “Enable YNP”):** run the 3-step chain inline.
  1) **Scope & Integrity:** clarify objective, read constraints from all profiles, list dependencies/risks, define success criteria.
  2) **Draft & Chain:** produce artifacts; chain required sub-prompts to complete the job.
  3) **Finalize & Deliver:** run security, operational, versioning, and workflow validations; fix issues; deliver artifact + log.

---

## Self‑Verification (apply before delivering)
- **Plan A vs Plan B:** briefly evaluate at least one alternative approach and note why the chosen plan wins.
- **Risk Scan:** secrets exposure, env mismatches, missing headers, version regressions, workflow validation failures.
- **Evidence & Traceability:** reference which rules/profile sections justified decisions (name the profile + rule).
- **Confidence Note:** Short note indicating degree of certainty and any follow-ups recommended.

---

## Output Shape Requirements
- Obey any **Mandatory Response Format** definitions present in the workspace.
- Always include a concise **Delivery Log** and the **## 🚀 Your Next Prompt** section.
