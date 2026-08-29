<!-- L9META
parent: claude-coding-contract-compiler
layer: reference
role: claudefillpolicy
version: 2.7.0
updated: 2026-08-27
sources: Claude Code executor model; compiler v2.7.0 execution law
-->

# Claude Fill Policy

This compiler emits bounded contracts for cold Claude Code sessions. The chain is one shared local
branch, exactly one local commit per contract, and one terminal `make pr` delivery.

## Claude-specific fill differences
| Concern | Binding fill |
|---|---|
| Scope | One focused session per contract; decompose oversized work |
| Resume | Executable preflight, mandatory |
| Validation | Explicit target-native campaign commands; no ecosystem inference |
| Item proof | `verify_proof` proves the current item at commit time; on next resume only that proof is re-run for predecessor validation |
| Commit | Exactly one local commit with compiler-owned subject = contract ID |
| Internal seam | `<id> committed_and_validated` |
| Delivery | No push between contracts; terminal contract runs exactly `make pr` once |
| Authority | Direct push/PR commands remain denied |
| Determinism | IDs, seams, digest, commit ordinals, commit command, terminal delivery derived by scripts |

## Cold-resume layers
Every preflight executes, in deterministic order:

1. compiler-derived target-branch equality assertion;
2. for contract 2+, compiler-derived HEAD subject assertion for the immediately previous contract;
3. `campaign.validation.cold_resume.commands`;
4. for contract 2+, every command from the previous contract's exact `required_before_commit` gate.

The current contract's own `verify_proof` MUST NOT appear merely because the current contract exists;
it may depend on outputs that have not been built yet.

## Seam Vocabulary Contract
Internal seams are machine-comparable and use exactly:

```yaml
handoff:
  next_session_may_assume_green:
    - "<this-contract-id> committed_and_validated"
```

The next contract consumes exactly:

```yaml
prerequisite_contract:
  id: "<prior-contract-id>"
  required_state: committed_and_validated
resume_from:
  assumes_already_green:
    - "<prior-contract-id> committed_and_validated"
```

Capabilities do not belong in the seam token. They are executable preflight commands.

## Completion proof lifecycle
For item N:

```text
implement N
  -> run campaign commit-gate commands
  -> run every command from N.commit_gate.required_before_commit
  -> create exactly one local commit with subject N.contract_id
  -> publish handoff N committed_and_validated
```

For item N+1:

```text
preflight
  -> same branch
  -> HEAD subject == N.contract_id
  -> campaign cold-resume commands
  -> N.commit_gate.required_before_commit in full
  -> begin N+1
```

This is the required meaning of "validate the previous contract executed in full and correctly."

## Git execution law
- Every campaign item has `sizing.commits: 1`.
- Every emitted contract has `commit_policy: exactly_one_local_commit_per_contract`.
- `commit_subject` equals the exact contract ID.
- `commit_command` is compiler-derived as `git commit -m "<contract-id>"`.
- `may_rewrite_unpushed_local_commits` is false.
- Do not push after any nonterminal contract.
- Do not run direct `git push` or direct `gh pr create` from any contract.
- Only the terminal contract receives `terminal_delivery.authorized: true` with command `make pr`.
- After the terminal contract's commit is green, run `make pr` exactly once.

## Target-validation law
The compiler never inserts npm, Python, Go, Cargo, Maven, Gradle, Make, or another ecosystem command
unless it appears in canonical campaign input or an item `verify_proof`. Missing validation is a
compile-time blocker. Bootstrap/install commands are never silently substituted for proof.

## Authority Mapping
Direct remote mutation remains denied:

```yaml
denied_tools:
  - "Bash(git push:*)"
  - "Bash(git merge:*)"
  - "Bash(gh pr create:*)"
  - "Bash(gh pr merge:*)"
  - "Bash(gh api *repos*:*)"
```

The terminal `make pr` wrapper is the explicit narrow exception for push/PR opening. Merge remains
outside the contract chain.

## Session sizing
Defaults:
- max new files: 20
- max commits: 1
- max matrix cases: 25
- max deliverables: 10

Any exceeded threshold means `DECOMPOSE_REQUIRED`; never compress scope to dodge decomposition.
