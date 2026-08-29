# RUNBOOK — l9-claude-coding-contract-compiler v2.7.0

## Setup

```bash
pip install jsonschema pyyaml
```

## 1. Establish target-native validation from repository evidence

Before compiling, identify the repository's real cold-resume and commit-gate commands. Do not infer
from file extensions alone.

Example Python target:

```yaml
campaign:
  validation:
    cold_resume:
      commands:
        - "python -m unittest discover -s tests -v"
    commit_gate:
      commands:
        - "python -m unittest discover -s tests -v"
        - "make pr"
```

Example Node target:

```yaml
campaign:
  validation:
    cold_resume:
      commands:
        - "npm run validate"
    commit_gate:
      commands:
        - "npm run validate"
```

npm is valid only because the target explicitly declares it.

## 2. Author ordered items

Each item must have:

```yaml
verify_proof: "<runnable command proving THIS item completed correctly>"
sizing:
  commits: 1
```

If an item needs multiple commits, split it into ordered contracts.

## 3. Compile

```bash
python scripts/compile_contract.py \
  --spec campaign-spec.yaml \
  --out DIR \
  --validate \
  --emit-artifacts
```

## 4. Execute the chain on one branch

For contract 1:

1. checkout the campaign `target_branch`;
2. run its generated `preflight.sh`;
3. implement only its scope;
4. run every `commit_gate.required_before_commit` command;
5. create the exact compiler-specified local commit;
6. do **not** push;
7. start the next contract on the same branch.

For contract 2+:

1. remain on the same campaign branch;
2. run its generated `preflight.sh` before editing;
3. preflight must prove the immediately previous contract's exact HEAD commit and re-run only that
   predecessor's dedicated `verify_proof`;
4. do not replay the predecessor's repository-wide commit gate; if the predecessor completion proof
   fails, HALT;
5. implement current scope, validate, create exactly one local commit;
6. do **not** push unless this is the terminal contract.

## 5. Terminal delivery

Only the final contract is emitted with:

```yaml
terminal_delivery:
  authorized: true
  command: "make pr"
```

After the final contract's one local commit exists and its commit gate is green:

```bash
make pr
```

Run it once. It is the sole authorized push/PR-opening route for the complete chain. Direct
`git push` and direct `gh pr create` stay in `denied_tools`, where they are denied by the
generated permission list rather than by a governance gate.

## 6. Validate the compiler itself

```bash
python scripts/test_target_validation.py
```

Required result: all tests PASS.

## Failure modes

| Symptom | Meaning | Recovery |
|---|---|---|
| `campaign.validation is required` | target validation authority unresolved | inspect repo and declare real commands |
| multiline/empty command rejected | command is not deterministic input | replace with one explicit shell line |
| `sizing.commits must equal 1` | contract is too coarse | decompose into ordered items |
| preflight wrong-branch failure | session is not on shared campaign branch | checkout the exact target branch |
| predecessor HEAD/proof failure | prior contract did not complete exactly as declared | repair prior contract before continuing |
| chain terminal-delivery mismatch | more/less than one delivery authority | recompile, never hand-edit instances |

## Non-negotiable

Do not modify a target repository to satisfy an incorrect compiler assumption. Fix canonical compiler
input/semantics instead. Missing target evidence blocks compilation rather than triggering a fallback.
