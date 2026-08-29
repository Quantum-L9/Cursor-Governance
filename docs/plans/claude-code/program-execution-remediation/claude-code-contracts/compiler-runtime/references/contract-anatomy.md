<!-- L9META
parent: claude-coding-contract-compiler
layer: reference
role: contractanatomy
version: 2.7.0
updated: 2026-08-27
-->

# Contract Anatomy — authority anchors

Resolve these before compiling. Unknown target validation is blocking.

```yaml
executor:
  executor: claude-code

identity:
  contract_id: compiler-derived
  contract_version: semver
  target_repo: org/repo
  target_branch: shared campaign branch

resume_from:
  assumes_already_green: [machine-comparable seam token]
  verify_before_starting:
    - compiler branch assertion
    - previous HEAD assertion      # contract 2+
    - target cold-resume commands
    - previous required-before-commit gate    # contract 2+
  if_assumption_false: HALT RESUME_PRECONDITION_NOT_SATISFIED

execution_authority:
  may_read_repository: true
  may_modify_worktree: true
  may_run_local_tests: true
  may_create_local_commits: true
  may_rewrite_unpushed_local_commits: false
  denied_tools:
    - "Bash(git push:*)"
    - "Bash(git merge:*)"
    - "Bash(gh pr create:*)"
    - "Bash(gh pr merge:*)"
    - "Bash(gh api *repos*:*)"

git_workflow:
  shared_branch: same as target_branch
  commit_policy: exactly_one_local_commit_per_contract
  commit_subject: exact contract_id
  commit_command: git commit -m "<contract_id>"
  completion_proof: current items[].verify_proof
  push_policy: terminal_contract_only_via_make_pr
  terminal_delivery:
    authorized: false | true       # true only on last contract
    command: null | "make pr"

commit_gate:
  required_before_commit:
    - target-native campaign commit gates
    - current item completion proof

scope_lock:
  in_scope: [bounded deliverables]
  hard_out_of_scope: [forbidden capabilities]
  preserved_files: [guarantees]

handoff:
  next_session_may_assume_green:
    - "<contract-id> committed_and_validated"
  next_contract: id | null
  chain_digest: sha256:...
```

Every campaign item creates exactly one local commit. Contract 2+ validates the immediately
previous contract before editing. Only the terminal contract may run `make pr`.
