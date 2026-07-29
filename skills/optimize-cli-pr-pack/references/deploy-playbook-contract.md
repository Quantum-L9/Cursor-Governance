# Deploy Playbook Contract

## Required sections

1. **Release identity:** repository, base ref, branch, commit or patch digest, package version.
2. **Prerequisites:** exact tools, versions when known, credentials by name only, environment access, approvals.
3. **Pre-deploy checks:** clean state, required validation, artifact digest, backup or rollback readiness.
4. **Build:** exact repository-native commands and expected artifacts.
5. **Install or publish:** exact commands for the real release channel.
6. **Configuration:** flags, environment variables, config files, defaults, and safe initial limits.
7. **Smoke verification:** exact commands, expected exit codes, and observable success criteria.
8. **Progressive rollout:** canary or bounded first use when the environment supports it.
9. **Monitoring:** signals that prove improved throughput, preserved correctness, stable error behavior, and bounded resource use.
10. **Abort conditions:** measurable conditions requiring rollback.
11. **Rollback:** exact restoration commands and verification.
12. **Post-deploy:** final evidence, release note, ownership, and follow-up.

## Rules

- Derive commands from repository release configuration, not generic memory.
- Label unavailable environment values `UNKNOWN`.
- Do not invent registries, package names, hosts, namespaces, secrets, or approvals.
- Make rollback possible before recommending deployment.
- Separate local install, package publication, and production rollout when they differ.
