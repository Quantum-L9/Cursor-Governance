# Judgement escalation

The deterministic digest runs first. Use model judgement only for unresolved semantic questions.

Invoke judgement for intent-to-change ambiguity, semantic duplicate ownership, proportionality, domain-vs-global ownership, or competing implementation shapes. Do not invoke it for file counts, diff parsing, CI collection, changed paths, dependency detection, generated-file detection, or machine-readable policy rules.

For every judgement record:

- question
- deterministic evidence supplied
- cited repository authority or owner
- finding and expansion classification
- decision impact
- evidence quality: `high | medium | low | unknown`

A judgement may tighten the gate. It may never convert a proven deterministic failure into success. If material evidence remains unavailable, preserve `UNKNOWN`.
