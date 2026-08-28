# ALIGNMENT_REPORT — l9-claude-coding-contract-compiler v2.7.0

## Alignment summary

Status: **PASS** for compiler/package alignment.

v2.7.0 repairs the v2.6.2 ecosystem-specific cold-resume defect and the adjacent chain-lifecycle defect without introducing a second execution authority. The compiler remains a deterministic spec-to-contract projector. Repository validation authority now enters through the canonical campaign spec rather than hidden emitter defaults.

## Authority boundaries

| Concern | Authority |
|---|---|
| Target validation commands | `campaign.validation` in canonical campaign spec |
| Contract ID / chain digest / seam derivation | deterministic compiler scripts |
| Current-contract completion proof | `items[].verify_proof` |
| Contract N+1 resume proof | compiler projection of N's exact commit subject + N dedicated completion proof only |
| Repository scope / ownership | DPK + scope-lock inputs |
| Local commit shape | compiler `git_workflow`: exactly one commit per contract |
| Remote delivery | terminal contract only, exact `make pr`; direct push/PR commands remain denied |
| Promotion readiness | existing DPK readiness gate; compiler does not override it |

No language, package manager, test runner, dependency installer, or validation command is inferred from repository filenames or host state.

## v2.7.0 semantic repair

- Removed implicit `npm ci && npm run validate` from cold resume.
- Removed implicit `npm run validate` from commit gating.
- Made `campaign.validation.cold_resume.commands` and `campaign.validation.commit_gate.commands` mandatory.
- Replaced comment-only branch expectation with executable branch equality.
- Stopped placing the current contract's future completion proof in its own preflight.
- Contract N's completion proof now gates N's local commit; N+1 re-runs only N's dedicated
  completion proof and exact HEAD assertion. Repository-wide commit validation is not replayed.
- Internal seam state is `committed_and_validated`.
- Every contract is fixed to exactly one local commit on one shared campaign branch.
- Nonterminal contracts cannot deliver remotely.
- The terminal contract alone is authorized for exact `make pr` once after its validated local commit.
- Direct `git push`, direct PR creation, merge, and repository-setting mutation remain denied.

## Validation evidence

Executed against the repaired pack:

- JSON schema parse: **15/15 PASS**.
- Python syntax compile across bundled scripts: **PASS**.
- `scripts/test_target_validation.py`: **11/11 PASS**.
- Node explicit-validation fixture: **9/9 contracts VALID**, chain **VALID**.
- Node chain digest: `sha256:03141121760661ccbc13093e5e786d6578de102a91af7f088f52a1c599dfcb3c`, unchanged from the original deterministic fixture.
- Python neutrality fixture: **2/2 contracts VALID**, chain **VALID**, zero undeclared npm validation.
- Go neutrality fixture: **1/1 contract VALID**, chain **VALID**, zero undeclared npm/Python validation.
- Real Git regression: contract 1 preflight succeeds before its own output exists; contract 2 accepts
  the exact predecessor commit + predecessor dedicated completion proof; wrong branch fails closed.
- Deterministic recompile regression: identical spec emits byte-equivalent contract data with one source-commit ordinal per contract.
- Delivery regression: exactly one terminal `make pr` authorization per chain; zero nonterminal delivery authority.
- Commit-gate deduplication regression: repository gate equal to item completion proof remains valid after stable dedupe.
- Exemplary-tier metadata validator: **PASS** after compressing leverage points to the five-item contract.
- Existing Cursor-Governance root-autonomy remediation compatibility projection: **7/7 contracts VALID**, chain **VALID**, original chain digest preserved as `sha256:1da10bc9634e8e18ab022c4dacb75f562af0eea9a840aa5b50785f91ddb1847f`, zero npm fallback, one terminal `make pr` authority. The compatibility projection changes execution transport only; the remediation task/file architecture is not redesigned.

## Known limits / honesty boundary

- The compiler validates command structure and projection, but does not execute target-repository validation during compilation because it may run outside the target checkout.
- The Cursor-Governance compatibility compile proves contract generation and chain semantics, not that the target implementation has been executed. Its DPK readiness remains the supplied current-state score, including `promotion_ready: false` where applicable.
- `make pr` is an explicitly authorized repository wrapper. The compiler does not replace it with direct remote commands.

## Convergence

```yaml
status: complete
version: 2.7.0
compiler_alignment: passed
target_validation_binding: explicit_fail_closed
regression_tests: 11_pass_0_fail
node_fixture: 9_pass_chain_valid
python_fixture: 2_pass_chain_valid
go_fixture: 1_pass_chain_valid
cursor_remediation_compatibility: 7_pass_chain_valid
exemplary_gate: passed
implicit_ecosystem_fallbacks: 0
commits_per_contract: 1
shared_branch_per_chain: 1
terminal_make_pr_authorities_per_chain: 1
direct_push_authority: denied
convergence_status: converged
```
