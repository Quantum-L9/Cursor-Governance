# Memory Context Reader

Read-only integration with the canonical memory control plane
(`python -m ops.memory.cli search`, realignment stage C11). No write, claim,
phase-lock, or memory-promotion command is exposed here, and no provider is
called: memory answers the search and its receipt is the evidence.
