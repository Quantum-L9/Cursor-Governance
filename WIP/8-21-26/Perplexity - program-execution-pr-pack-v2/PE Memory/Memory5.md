Exactly. Do not make .env.local part of the contract. For a fresh desktop clone, I’d make secret materialization an automatic clone-bootstrap step backed by Infisical.

For Claude Code specifically, I would actually target .claude/settings.local.json, not a generic .env.local. Claude Code natively reads environment variables from the env object in its settings files regardless of how Claude was launched; .claude/settings.local.json is project-local and intended to be gitignored.  That makes it substantially more reliable for Desktop/background sessions than relying on shell exports.

The desired experience becomes:

git clone ...
cd Cursor-Governance
./setup.sh
   ↓
detect desktop surface
   ↓
Infisical CLI installed?
   ↓
Infisical authenticated?
   ↓
pull approved secrets
   ↓
generate .claude/settings.local.json
   ↓
chmod 600
   ↓
validate required capabilities
   ↓
hydrate
   ↓
READY_PE_AUTONOMOUS

I would put this in one canonical command

Something like:

ops/runtime_env/bootstrap.py

with:

python3 ops/runtime_env/bootstrap.py --surface claude-desktop

And your normal clone/setup script simply calls it automatically.

The bootstrap should be idempotent:

file missing
    → generate
file exists + valid + current
    → do nothing
file exists + missing keys
    → merge missing/current managed keys
secret rotated in Infisical
    → update managed value
Infisical unavailable + valid file exists
    → FALLBACK_LOCAL, continue
Infisical unavailable + required file missing
    → BLOCK autonomous PE

No manual copying.

Use a committed Infisical project pointer

Infisical supports a project-local .infisical.json created by infisical init; its purpose is to associate CLI commands with the appropriate Infisical project, and Infisical documents committing that project metadata into the repo. 

So the clone contains metadata, never credentials:

Cursor-Governance/
├── .infisical.json                 # committed: project/domain reference
├── .claude/
│   ├── settings.json               # committed: non-secret Claude policy
│   └── settings.local.json         # GENERATED, gitignored, chmod 600
│
├── environment/contracts/runtime/
│   └── secrets.manifest.json       # committed allowlist/requirements
│
└── ops/runtime_env/
    └── bootstrap.py

The manifest might define:

{
  "schema": "l9.secrets-manifest.v1",
  "infisical": {
    "environment": "dev",
    "path": "/cursor-governance/desktop"
  },
  "claude_desktop": {
    "required": [
      "GRAPHITI_MCP_TOKEN"
    ],
    "optional": [
      "GH_TOKEN"
    ]
  }
}

But I would probably not put GH_TOKEN there on your Mac if gh auth is already healthy. GitHub capability should come from the gh credential store; Infisical should materialize only credentials genuinely needed as environment variables.

Authentication itself should not require another repo secret

On your desktop, I would use your normal Infisical CLI user login.

Infisical’s current CLI can report an authenticated session and identifies login credentials stored through its keyring-backed login mechanism. 

One-time machine setup:

brew install infisical/get-cli/infisical
infisical login

After that, every clone can automatically do:

infisical export ...

without you placing an INFISICAL_TOKEN inside each repository.

Machine identity / Universal Auth remains better for CI and non-human workers; Infisical supports those authentication methods as well. 

⸻

Don’t export the entire Infisical folder blindly

This part matters.

Infisical supports exporting a project environment directly to dotenv, JSON, YAML, and other formats.  But I would not do this:

infisical export > .env

for L9.

Instead:

Infisical
   ↓
JSON export in memory
   ↓
allowlist against secrets.manifest.json
   ↓
required/optional classification
   ↓
Claude renderer
   ↓
.claude/settings.local.json

Therefore a secret accidentally added to the Infisical folder doesn’t automatically become available to Claude.

For example Infisical might contain:

GRAPHITI_MCP_TOKEN
OPENAI_API_KEY
NEO4J_PASSWORD
AWS_ADMIN_SECRET
DEPLOY_PRIVATE_KEY

but the desktop agent manifest allows only:

GRAPHITI_MCP_TOKEN

Then Claude receives exactly that one.

That is a much better security boundary.

⸻

The generated Claude file

The renderer should merge with any existing local settings instead of replacing them:

{
  "env": {
    "GRAPHITI_MCP_URL": "https://memory.quantumaipartners.com/graphiti/mcp",
    "GRAPHITI_MCP_TOKEN": "<materialized-from-infisical>",
    "GRAPHITI_MEMORY_ENABLED": "1"
  }
}

Claude Code explicitly supports env in settings.json, and project-local .claude/settings.local.json is scoped to you and the current project. 

Crucially, Claude also reapplies changes to settings-file environment variables to a running session when the file changes, except for features that only read their values at startup. 

So this integrates far more naturally than inventing .env.local.

⸻

I would make generation atomic

Never write secrets directly into the final file progressively.

Do:

1. authenticate
2. fetch into process memory
3. validate expected keys
4. load existing settings.local.json
5. merge env section
6. serialize temp file
7. chmod temp file 0600
8. fsync
9. atomic rename → settings.local.json
10. validate Claude settings
11. zero/discard in-memory structures

If Infisical fails at step 2, the known-good file is untouched.

That’s important for clone boot reliability.

⸻

And never print values

The bootstrap output should look like:

L9 SECRET BOOTSTRAP
──────────────────────────────────────
Infisical       ✓ authenticated · user/keyring
Project         ✓ Cursor-Governance
Environment     ✓ dev
Path            ✓ /cursor-governance/desktop
GRAPHITI_MCP_TOKEN
  source        Infisical
  destination   Claude local settings
  status        ✓ materialized
GRAPHITI_MCP_URL
  source        canonical config
  status        ✓ resolved
Claude settings
  target        .claude/settings.local.json
  permissions   0600
  status        ✓ READY
Values displayed: NEVER
──────────────────────────────────────

And the machine receipt:

{
  "decision": "READY",
  "source": "infisical",
  "target": ".claude/settings.local.json",
  "credentials": {
    "GRAPHITI_MCP_TOKEN": {
      "state": "RESOLVED",
      "source": "infisical",
      "value": null
    }
  }
}

No hash of the secret either.

⸻

Add provenance so stale files aren’t silently trusted

Put a non-secret companion receipt next to the generated file:

.l9/runtime/env-receipt.json

For example:

{
  "schema": "l9.runtime-env-receipt.v1",
  "generated_at": "2026-08-15T18:50:00Z",
  "surface": "claude-desktop",
  "provider": "infisical",
  "environment": "dev",
  "path": "/cursor-governance/desktop",
  "keys": [
    "GRAPHITI_MCP_TOKEN"
  ],
  "required_missing": [],
  "decision": "READY"
}

Then SessionStart can say:

ENVIRONMENT
  ✓ Infisical        authenticated
  ✓ Claude secrets   materialized
  ✓ Graphiti auth    available
  ✓ GitHub           gh credential store
HYDRATION
  ...

And your PE admission gate consumes that receipt.

⸻

Fresh-clone trigger

I would wire it into whatever canonical clone bootstrap becomes:

#!/usr/bin/env bash
set -euo pipefail
python3 ops/runtime_env/bootstrap.py \
    --detect-surface \
    --if-required
python3 ops/session_runtime/cli.py boot

But also make sessionStart defensive:

sessionStart
    │
    ├── env receipt fresh?
    │       YES → continue
    │
    └── NO
          ↓
       runtime_env bootstrap
          ↓
       continue hydration

That means even if you forget to run setup after cloning, the first Claude session self-heals the clone.

⸻

I’d add a freshness policy too

Something like:

secret file exists + receipt < 12h
    → use immediately
receipt > 12h
    → attempt refresh from Infisical
       ├── succeeds → update
       └── fails → use existing credential if live probe succeeds

Better yet, don’t use time alone:

local credential exists
        +
Graphiti authenticated probe succeeds
        =
credential usable

If Graphiti returns 401:

refresh Infisical
→ regenerate
→ probe again

That’s “magic” that is still deterministic.

⸻

Infisical should become the source of secret values, not runtime policy

I would keep this separation rigid:

Git repository
  owns:
    which secret names are allowed
    which surfaces require them
    Infisical path/environment
    fallback policy
    readiness policy
Infisical
  owns:
    secret values
Generated local file
  owns:
    temporary materialization for this clone
Session receipt
  owns:
    proof that everything resolved

That avoids letting the secret manager accidentally become configuration governance.

⸻

The final desktop flow

On a completely new Mac, once:

brew install infisical/get-cli/infisical
infisical login
gh auth login

After that, forever:

git clone git@github.com:Quantum-L9/Whatever.git
cd Whatever
./setup.sh

and:

✓ detects Infisical project from clone
✓ pulls only declared secrets
✓ creates .claude/settings.local.json
✓ permissions 0600
✓ validates Graphiti
✓ validates GitHub identity
✓ hydrates session
✓ generates readiness receipt
✓ READY_PE_AUTONOMOUS

Then you can delete that clone tomorrow, clone it somewhere else, and do it again.

No .env.local to preserve. No secrets copied from old clones. No shell-profile dependency. No manual Graphiti token. No provider-specific secret drift.

And I would make the same bootstrap.py support --surface cursor-desktop as a second renderer, so the source/resolution brain remains one piece of code and only the final materialization format differs. 