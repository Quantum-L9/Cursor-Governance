# Operator Guide

## When to Run

Run this kernel at the end of a session when:

1. Context is nearly full.
2. Drift has appeared and been corrected.
3. Multiple artifacts were generated.
4. Architecture boundaries changed.
5. A next-session handoff is needed.

## Operating Rule

Do not summarize the chat. Extract reusable signals only.

## Output

Emit a `SessionSignalPacket` using the canonical schema and templates.
