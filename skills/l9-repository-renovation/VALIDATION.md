# Validation

Run from the skill root:

```bash
python scripts/self_test.py
python scripts/validate_exemplary_skill.py .
python -m compileall -q scripts
```

Package validation is performed by the ChatGPT skill-creator packager. Repository runs additionally require:

1. `validate_contract.py` passes.
2. Every validation command has captured evidence.
3. `compare_audits.py` reports no new high-severity findings.
4. `validate_pr_pack.py` passes.
5. The PR is created only with explicit GitHub write authorization.
