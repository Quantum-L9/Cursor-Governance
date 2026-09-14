# Infisical GHA OIDC on existing secrets plane

owner: Igor Beylin
target: Quantum-L9/Cursor-Governance

## Final architectural judgment

It is:
Put GitHub Actions OIDC on the existing Infisical secrets plane
(capability_broker oidc-workload-identity and hydrate_infisical /
port_aws_to_infisical.login). Leave Claude bootstrap as
make claude-install → install.sh → bootstrap_agent_environment.sh →
bootstrap_agent_env.sh --check. Do not add Infisical/secrets-action,
claude-code-bootstrap.yml, an Infisical /claude-code folder, or GitHub
Environment production.

## Program ordering

1. Record gha_oidc identity in infisical-cursor-governance.yaml and infisical-protocol.md. Do not add INFISICAL_OIDC_SETUP.md.
2. Add one shared OIDC login helper next to port_aws_to_infisical.login. Broker and hydrate call it. Model surfaces still cannot export values.
3. Add mocked OIDC login tests in ops/secrets/test_aws_secrets.py.
4. Comment-only on install.sh, bootstrap_agent_environment.sh, and setup_claude_code_plugins.sh that they are not Infisical consumers.
5. Probe U1 AWS role trust and U2 existing Infisical identity, then bind or record identity_id. Set INFISICAL_IDENTITY_ID via gh api. Do not create GitHub Environment production.
6. Prove no claude-code-bootstrap.yml and no Infisical/secrets-action. Run capability-contract-validate.

## Do not

- A new Claude bootstrap workflow
- Injecting API keys into SessionStart or GHA session env
- Running plugin setup on ubuntu-latest
- Touching the Claude env-contract campaign
