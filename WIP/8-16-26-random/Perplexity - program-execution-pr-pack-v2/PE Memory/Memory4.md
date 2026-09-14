Yes. I would make environment + secret resolution part of the same Session Admission contract we just discussed. It should be deterministic, machine-readable, surface-aware, and mostly invisible when healthy.

There is one rule I would lock in immediately:

Secrets are capabilities, not configuration strings. Resolve them as late as possible, never copy them into model context, never serialize their values into receipts, and never require every surface to obtain them from the same physical backend.

GitHub organization secrets are excellent for GitHub-hosted execution, but they are not a general-purpose pull vault: Actions secrets are injected into authorized jobs, while gh secret list exposes metadata but not secret values. GitHub recommends OIDC instead of stored cloud credentials where supported. 

I would build one canonical L9 Runtime Environment Resolver

Every surface calls the same thing:

                    L9 ENVIRONMENT CONTROL PLANE
                              │
                    env/secret registry
                              │
                   surface capability probe
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
         config           credentials       secrets
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                       Runtime Resolver
                              │
                ┌─────────────┼──────────────┐
                ▼             ▼              ▼
             process      capability      env receipt
              env           handles        NO VALUES
                              │
                              ▼
                       Session Admission
                              │
                              ▼
                    Hydration → PE autonomy

The result is that Cursor, Claude Code desktop, Claude Web/Mobile, CI and autonomous PE workers all ask one resolver for the same logical capabilities.

⸻

1. Create an executable variable/secret registry

Something like:

schema: l9.runtime-env.v1
variables:
  GRAPHITI_MCP_URL:
    class: config
    required_for:
      - hydration
      - pe_autonomous
    default: https://memory.quantumaipartners.com/graphiti/mcp
    allowed_sources:
      - process_env
      - machine_config
      - canonical_default
  GRAPHITI_MCP_TOKEN:
    class: secret
    capability: memory.graphiti.auth
    required_for:
      - hydration
      - pe_autonomous
    sources:
      claude_web:
        - process_env
      claude_mobile:
        - process_env
      darwin:
        - macos_keychain:graphiti-mcp-token
        - process_env
        - secret_file
      linux:
        - process_env
        - secret_file
  GITHUB_AUTH:
    class: credential
    capability: github.repo.write
    sources:
      darwin:
        - gh_credential_store
      claude_web:
        - env:GH_TOKEN
      github_actions:
        - github_token
  AWS_AUTH:
    class: credential
    capability: aws.runtime
    sources:
      github_actions:
        - oidc
      darwin:
        - aws_sso
        - credential_process
  OPENAI_API_KEY:
    class: server_secret
    agent_access: forbidden

Notice GITHUB_AUTH doesn’t insist that every machine have GH_TOKEN.

On your Mac:

gh authenticated
     =
github.repo.write capability available

That’s better than spraying a PAT into every process environment.

The current Claude Web setup explicitly consumes GH_TOKEN from its environment field, which is appropriate for that ephemeral surface. 

⸻

2. Use different secret providers by surface

I would standardize this matrix:

Surface	Configuration	Secret/Credential source
Claude Web/Mobile	committed defaults + injected env	environment fields you place above setup script
Cursor macOS	canonical defaults + machine config	Keychain + gh credential store + AWS SSO
Claude Code desktop	same resolver as Cursor	Keychain + gh credential store + AWS SSO
GitHub Actions / PE CI	workflow + registry	org/repo/environment secrets + OIDC
GitHub Codespaces	registry	Codespaces org/repo/user secrets
VPS/services	deployment config	AWS Secrets Manager/service identity

GitHub supports organization/repository Codespaces secrets as injected development-environment variables, including repository access policies. 

That is uniform semantics, not uniform physical storage.

That’s the right abstraction.

⸻

3. Mobile stays exactly as you want it

For Claude Web/Mobile, you put the bootstrap secrets above the script:

export GH_TOKEN='...'
export GRAPHITI_MCP_TOKEN='...'
# then canonical setup
...

The resolver sees:

GRAPHITI_MCP_TOKEN
  source       process_env
  surface      claude-mobile
  validation   MCP probe PASS
GITHUB_AUTH
  source       GH_TOKEN
  validation   gh auth PASS

Nothing else needs to happen.

Your current Web/Mobile setup already expects credentials from the Claude environment-variable field and uses the cloud Graphiti endpoint by default. 

I would preserve that behavior.

⸻

4. Cursor / Claude Code desktop should require zero exports

This is where I agree with “work like magic.”

Once per Mac:

L9 machine bootstrap
     │
     ├── establishes gh authentication
     ├── establishes AWS SSO if needed
     ├── installs GRAPHITI token into Keychain
     ├── installs runtime resolver
     └── validates everything

After that:

open Cursor

or:

claude

should be enough.

The repo already has most of this concept for Graphiti: graphiti_env_loader.py checks the environment, machine overlays, and macOS Keychain service graphiti-mcp-token; Linux skips Keychain and uses env or a secret overlay. 

I would generalize that pattern into one runtime resolver instead of Graphiti owning a one-off resolver.

So this:

ops/graphiti/graphiti_env_loader.py

eventually becomes a thin consumer of:

ops/runtime_env/
    registry.py
    resolver.py
    providers/
        process_env.py
        macos_keychain.py
        gh_auth.py
        aws_sso.py
        secret_file.py

⸻

5. Don’t export GitHub credentials locally unless necessary

For Mac/Desktop I would strongly prefer:

gh auth

as the capability provider rather than:

export GH_TOKEN=...

Your subprocesses can use:

gh api
gh pr
gh run
gh issue
git via gh credential helper

without making the PAT a general-purpose environment variable.

GitHub also recommends fine-grained credentials and GitHub Apps over broad personal credentials where practical. 

For your Claude Web sandbox, keeping GH_TOKEN is reasonable because there’s no persistent desktop credential store.

⸻

6. Use OIDC/SSO for AWS, never shared AWS keys

For PE workers:

GitHub Actions
     │
     ▼
GitHub OIDC
     │
     ▼
AWS temporary role

For Mac:

AWS SSO / credential_process

Not:

AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

sitting in a dotfile.

GitHub explicitly recommends OIDC for workflows accessing compatible cloud providers because it avoids maintaining long-lived cloud credentials. 

This is especially important once autonomous PE can launch infrastructure-capable workers.

⸻

7. Server-only secrets must never reach agents

You already have a good example.

The repo’s Graphiti example identifies OPENAI_API_KEY as a VPS-only secret with AWS Secrets Manager as its source, rather than something every Cursor clone should receive. 

Keep that separation.

For example:

GRAPHITI_MCP_TOKEN
    → agent needs it
OPENAI_API_KEY
    → Graphiti service needs it
    → agent MUST NOT receive it
NEO4J_PASSWORD
    → Graphiti infrastructure only
AWS database credentials
    → workload identity only

This dramatically reduces blast radius.

⸻

8. Add a credential broker for the GUI/MCP seam

There is one remaining desktop issue I would fix.

Your Claude MCP template currently contains:

"url": "${GRAPHITI_MCP_URL}",
"Authorization": "Bearer ${GRAPHITI_MCP_TOKEN}"

so the MCP launcher expects those variables to already exist in the process environment. 

But your local resolver can retrieve the token from Keychain after the process has started. 

Those models don’t perfectly align.

For true “open the app and it works” behavior, I would introduce a tiny credential-aware MCP transport:

Cursor / Claude
      │
      ▼
l9-mcp connect graphiti-memory
      │
      ├── resolve GRAPHITI URL
      ├── resolve token from Keychain/env
      ├── never print token
      │
      ▼
Cursor Graphiti MCP

This is not another memory plane.

It is an authenticated transport adapter to the same Graphiti MCP endpoint.

Then neither Cursor nor Claude needs the actual token globally exported.

⸻

9. Give the environment resolver its own receipt

At SessionStart:

{
  "schema": "l9.runtime-env-receipt.v1",
  "surface": "cursor-desktop",
  "capabilities": {
    "memory.graphiti.auth": {
      "state": "READY",
      "source": "macos_keychain",
      "validated": true
    },
    "github.repo.write": {
      "state": "READY",
      "source": "gh_credential_store",
      "validated": true
    },
    "aws.runtime": {
      "state": "READY",
      "source": "aws_sso",
      "validated": true
    }
  },
  "config": {
    "GRAPHITI_MCP_URL": {
      "state": "RESOLVED",
      "source": "canonical_default"
    }
  },
  "missing": [],
  "fallbacks": [],
  "decision": "READY"
}

No secret values.

Not even:

first four characters
secret hashes
masked values

They aren’t needed.

⸻

10. Fold that directly into your hydration status

Your startup report becomes:

L9 SESSION · READY_PE_AUTONOMOUS
────────────────────────────────────────────
ENVIRONMENT
  ✓ Graphiti auth    Keychain
  ✓ GitHub auth      gh credential store
  ✓ AWS identity     SSO · role l9-dev
  ✓ Memory endpoint  canonical config
SECRETS
  ✓ required         3 / 3
  ○ optional         1 unavailable
  ! fallback         none
  values             NEVER DISPLAYED
HYDRATION
  ✓ Continuity       Graphiti · fresh
  ✓ Repo memory      4 selected
  ✓ Governance       canonical
  ✓ Workspace        loaded
PE
  ✓ Provider         capable
  ✓ Autonomy         L4 local
  ✓ Session receipt  valid
Autonomous PE         ✓ ADMITTED
────────────────────────────────────────────

If something fails:

ENVIRONMENT
  ✗ Graphiti auth
    required: memory.graphiti.auth
    attempted:
      macOS Keychain → missing
      process env    → missing
      secret overlay → missing
HYDRATION
  ! local ResumeCapsule fallback
Autonomous PE
  ✗ BLOCKED — required memory capability unavailable

That gives you the transparency you’re after without leaking anything.

⸻

11. Add machine validation

I would make these real commands:

l9 env status
l9 env status --json
l9 env doctor
l9 env probe
l9 env sync
l9 env validate --require pe-autonomous

And CI:

ENV-001  every registered variable has a classification
ENV-002  every secret declares allowed providers
ENV-003  secrets cannot have committed values
ENV-004  server-only secrets cannot materialize agent-side
ENV-005  required capabilities have provider for every required surface
ENV-006  receipt never contains secret values
ENV-007  Desktop Graphiti works from Keychain with clean process env
ENV-008  Desktop GitHub works with GH_TOKEN unset
ENV-009  Web works from injected process env
ENV-010  GitHub Action uses native secret/OIDC provider
ENV-011  missing credential yields explicit BLOCKED/FALLBACK
ENV-012  PE autonomy requires environment receipt PASS

Then:

Session Readiness
    requires
        Environment Receipt
        Hydration Receipt
        Capability Receipt
        Autonomy Receipt
        Program Receipt

⸻

There is some drift in the repo I’d clean up immediately

Right now graphiti_env_loader.py says the hosted/managed authoritative path uses GRAPHITI_MCP_URL / GRAPHITI_MCP_TOKEN, matching the MCP template. 

But graphiti.env.defaults still contains comments saying the hosted path uses L9_MEMORY_HTTP_URL / L9_MEMORY_CLIENT_TOKEN, even though the referenced MCP template actually uses the Graphiti variables. 

That’s precisely the kind of configuration drift the new registry eliminates.

The Web setup also defaults GRAPHITI_MCP_URL to the public cloud endpoint but later logs a 127.0.0.1:8100 description, which can mislead your startup telemetry. 

Those should become machine-generated from the same registry instead of maintained as prose in several files.

The final model

I would lock the hierarchy to:

SAFE CONFIG
  committed registry/defaults
        │
        ├── optional GitHub org variables
        │
        ▼
CREDENTIAL PROVIDERS
  Desktop       → Keychain / gh / AWS SSO
  Claude Web    → injected environment
  Mobile        → injected environment
  GitHub CI     → Actions secrets + OIDC
  Codespaces    → Codespaces secrets
  VPS           → Secrets Manager / workload identity
        │
        ▼
CANONICAL L9 ENV RESOLVER
        │
        ├── capability validation
        ├── provenance
        ├── fallback decisions
        └── NO SECRET VALUES IN RECEIPTS
        │
        ▼
SESSION ADMISSION
        │
        ▼
HYDRATION
        │
        ▼
PE AUTONOMOUS ADMISSION

So on your Mac the experience eventually becomes literally:

open Cursor
→ governance loaded
→ Keychain resolved
→ gh authenticated
→ Graphiti connected
→ hydration complete
→ PE capability verified
→ READY_PE_AUTONOMOUS

And on mobile:

env values above setup script
→ same resolver
→ same receipts
→ same hydration semantics
→ same PE admission contract

That gives you the magic UX without magical hidden behavior: every credential source is explicit in machine policy, every resolution is validated, every fallback is visible, and none of the agents need to understand how the secret got there.