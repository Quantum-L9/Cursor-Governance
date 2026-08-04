# L9 Repository Renovation

An end-to-end repository control-plane renovation skill. It begins with live-state discovery, converts evidence into a bounded implementation contract, replaces fragmented authorities with canonical ones, validates before and after state, and ends with one governed pull request or an explicit blocked pack.

## Typical invocation

> Renovate `owner/repo` from its current state into a coherent, locked, fully validated repository and open a draft PR. Keep product behavior unchanged and remediate the PR until required checks are green.

## Deterministic tools

The bundled scripts use the Python standard library. Run `python scripts/self_test.py` from the skill root before distribution.
