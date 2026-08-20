---
name: Hetzner Restore Plan Refinement
overview: Rewrite the Hetzner restore prompt to use the current AWS secret naming/region, drive off the existing deploy.sh instead of duplicating it, and wire OpenClaw's native exec-provider secrets system so only the 3 LLM API keys live in local config while everything else resolves live from AWS Secrets Manager — then fix the AWS secrets manifest repo-wide so IgorBot's own bootstrap docs are accurate and internally consistent.
todos:
  - id: resolver-script
    content: Write bin/openclaw-aws-resolver.py implementing the OpenClaw exec-provider stdin/stdout JSON protocol against AWS Secrets Manager (region us-east-1)
    status: completed
  - id: openclaw-json-secrets
    content: Add secrets.providers/defaults block to config/openclaw.json; convert gateway.auth.token_env to full gateway.auth.token SecretRef and add channels.telegram.botToken SecretRef, both on the new aws exec provider (the only two confirmed-active native SecretRef fields today)
    status: completed
  - id: trim-secure-env
    content: Remove only the 3 LLM key fetch lines from bin/secure-env.sh (region already correct at us-east-1) — keep every other line, since custom skill scripts under workspace/skills/ read those secrets as plain os.environ vars, not through OpenClaw's config-level SecretRef system
    status: completed
  - id: patch-deploy-sh
    content: Patch deploy.sh's generated systemd unit to source bin/secure-env.sh before exec'ing openclaw gateway
    status: completed
  - id: trim-env-template
    content: Trim .env.template to the 3 LLM keys + NEO4J_PASSWORD + non-secret defaults (region us-east-1)
    status: completed
  - id: fix-wip-manifest-csv
    content: Rewrite WIP-IGOR/config/secrets-manifest.csv with openclaw-igorbot/* naming, correct field names, region us-east-1, and a resolution_path column (local-only / exec-native / secure-env-only / provisioned-dormant) per secret
    status: completed
  - id: fix-provider-template
    content: Replace WIP-IGOR/config/provider-template.json with the real exec-provider shape pointing at the new resolver script, scoped to the 2 fields it actually serves (gateway.auth.token, channels.telegram.botToken)
    status: completed
  - id: rewrite-restore-prompt
    content: Rewrite WIP-IGOR/cursor-prompt-igorbot-hetzner-restore.md to use deploy.sh, correct secret naming/region, and the corrected (narrow) exec-provider wiring
    status: completed
  - id: manifest-cleanup-repo
    content: Fix region/naming in workspace/TOOLS.md (incl. "Used by" accuracy + UFW egress entries), bin/ufw-docker-egress.sh, credentials/aws-secrets-setup.sh, docs/secrets_structure.md, workspace/contracts/03-credential-provisioning.md, and CLAUDE.md
    status: completed
isProject: false
---

## Confirmed facts (from repo archaeology + your answers + a hardening re-audit)

- **Naming drift is real**: AWS namespace was renamed `clawdbot/*` → `openclaw-igorbot/*` on 2026-03-26 (commit `024dd30`). [WIP-IGOR/cursor-prompt-igorbot-hetzner-restore.md](WIP-IGOR/cursor-prompt-igorbot-hetzner-restore.md) and [WIP-IGOR/config/secrets-manifest.csv](WIP-IGOR/config/secrets-manifest.csv) still use the old bare `openclaw/*` naming (no `-igorbot`, wrong field names) — that's the flaw you flagged.
- **Region = us-east-1** (your confirmation). [bin/secure-env.sh](bin/secure-env.sh) already defaults there; [workspace/TOOLS.md](workspace/TOOLS.md), [.env.template](.env.template), [credentials/aws-secrets-setup.sh](credentials/aws-secrets-setup.sh), [bin/ufw-docker-egress.sh](bin/ufw-docker-egress.sh), [docs/secrets_structure.md](docs/secrets_structure.md), and `CLAUDE.md` all still say `us-east-2` and need correcting.
- **`deploy.sh` is the real current deploy path** (npm-installed OpenClaw, `openclaw.service` systemd unit, Docker/Neo4j/Graphiti, UFW) — more complete than the WIP-IGOR prompt's from-scratch steps, but its systemd unit currently does **not** source any secret loader at all.
- **OpenClaw has a native `SecretRef` system** (`source: env|file|exec`) for a defined credential surface (`skills.entries.*.apiKey`, `gateway.auth.token`, `channels.telegram.botToken`, etc. — confirmed via docs.openclaw.ai). The `exec` provider talks a stdin/stdout JSON batch protocol; [WIP-IGOR/config/provider-template.json](WIP-IGOR/config/provider-template.json)'s "call `aws` CLI directly, id appended as an arg" design does not match that protocol — it needs a small wrapper script, not a bare `aws` invocation.
- **Correction found on re-audit — the native SecretRef surface only covers 2 fields that are actually active today, not the ~10 I first assumed.** I re-checked `config/openclaw.json` directly: there is no `registry.clawhub` block, and none of `notion`/`goplaces`/`openai-whisper-api`/`nano-banana-pro`/`sag` exist as `skills.entries` at all (the old CSV's skill list is stale, not just its secret names). Only `skills.entries.github.apiKey` exists today as a real `{source:"env",...}` SecretRef. So the only fields worth migrating to the new `aws` exec provider are `gateway.auth.token` (currently a `token_env` shorthand) and `channels.telegram.botToken` (currently absent — a doc-confirmed field, added net-new since Telegram is an active, already-wired channel). `skills.entries.github.apiKey` is left on its current `env` source — it already works, migrating it has no benefit.
- **Correction found on re-audit — most "extended" secrets are dormant, not consumed by any skill code.** Grepped every script under `workspace/skills/` for `NOTION_API_KEY`, `CEG_API_KEY`, `NANO_BANANA*`, `OPENAI_WHISPER*`, `GOOGLE_PLACES_API_KEY`, `CLAWHUB_API_KEY`: zero functional hits (only `HCLOUD_TOKEN` and `TELEGRAM_BOT_TOKEN` are genuinely referenced, by `env_check`). `workspace/TOOLS.md`'s "Used by: Material match, geo lookups" claim for `GOOGLE_PLACES_API_KEY` is unsupported — `material_match`'s scripts don't reference it. These secrets stay provisioned in AWS (no harm in leaving them) but the manifest must say "provisioned, not currently consumed by any active skill" instead of asserting a specific consumer that doesn't exist in code.
- Custom skill scripts (the ~48 domain skills under `workspace/skills/`) read secrets via plain `os.environ`/`${VAR}`, not through OpenClaw's config-level `SecretRef` system — so `bin/secure-env.sh` remains the *primary* delivery mechanism for the majority of secrets (Telegram, GitHub, Hetzner, Neo4j, Cloudflare, Coolify, Vercel, ClawHub, Sonar, GitGuardian, and the dormant Tier-3 set). The exec provider only replaces the sliver that OpenClaw's own core resolves natively.
- Some fields in the live [config/openclaw.json](config/openclaw.json) use an alternate `_env`-suffix convention (`gateway.auth.token_env`, `channels.telegram.allowFrom_env`, `plugins.entries.graphiti.config.neo4j_password_env`) instead of full `SecretRef` objects. `allowFrom_env` and `neo4j_password_env` are **not** on the documented credential surface at all, so they keep needing real environment variables from `secure-env.sh` regardless of the exec-provider work.
- No `models.providers.*` block exists in the current `config/openclaw.json` at all — the bot already resolves `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `MISTRAL_API_KEY` by plain env-var convention. Per "existing code is source of truth," the plan does **not** invent a new `models.providers` block — it just guarantees those 3 vars are set from local `.env`.

## Changes

1. **New `bin/openclaw-aws-resolver.py`** — implements OpenClaw's exec-provider protocol: reads `{protocolVersion, provider, ids}` from stdin (ids shaped like `openclaw-igorbot/telegram#bottoken`), batches one `aws secretsmanager get-secret-value` call per unique base secret id (region `us-east-1`), extracts the `#field` selector, returns `{protocolVersion, values, errors}` JSON. Fails closed per-id with a `NOT_FOUND`/`RESOLUTION_ERROR` code on any lookup problem — never crashes the whole batch for one bad id, never logs a resolved secret value. Shells out to the `aws` CLI (already a dependency) — no new Python packages.

2. **`config/openclaw.json`** — add `secrets.providers.default` (`env`) + `secrets.providers.aws` (`exec`, pointing at the new resolver, `passEnv: [PATH, HOME, AWS_REGION, AWS_PROFILE]`) and `secrets.defaults.exec: "aws"`. Rewire only the **2 fields confirmed active today**: convert `gateway.auth.token_env` → full `gateway.auth.token` SecretRef (`openclaw-igorbot/igorbot-gateway-secret#token`), and add `channels.telegram.botToken` (`openclaw-igorbot/telegram#bottoken`, currently absent — added because Telegram is an already-active channel, not new scope). Leave `skills.entries.github.apiKey` on its current `env` source (already works, no benefit to migrating) and the 3 LLM keys on plain env convention (local `.env`, never AWS). **Flag for on-VPS verification**: run `openclaw config schema` / `openclaw secrets audit --check` against the actual installed OpenClaw version before applying — confirm `token_env` and `token` don't conflict, and that `channels.telegram.botToken` is recognized by this install's version.

3. **`bin/secure-env.sh`** — remove only the 3 LLM key fetch lines (Anthropic/OpenAI/Mistral — now local-only). Keep every other line as-is: region is already `us-east-1`, and everything else (Telegram, GitHub, Hetzner, Neo4j, Cloudflare, Coolify, Vercel, ClawHub, Sonar, GitGuardian, Notion, Google Places, Whisper, Nano Banana, CEG) is consumed by custom skill scripts via plain `os.environ`/`${VAR}` lookups, not through OpenClaw's config — those need real process env vars regardless of the new exec provider.

4. **`deploy.sh`** — patch the generated systemd unit's `ExecStart` to source `bin/secure-env.sh` before exec'ing the gateway (`ExecStart=/bin/bash -c 'source /opt/igorbot/bin/secure-env.sh && exec openclaw gateway --port 18789'`), so the (still-large) set of secure-env.sh-sourced vars actually reach the running process — this is now more necessary than in the first draft, not less, since secure-env.sh keeps its full scope minus the 3 LLM lines. Add a preflight: `command -v aws >/dev/null && aws sts get-caller-identity >/dev/null 2>&1`, failing loud with the same `_die`-style message pattern already used in `secure-env.sh`, before the systemd unit is written.

5. **`.env.template`** — trim to the real "core config": `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `NEO4J_PASSWORD`, plus existing non-secret defaults (`NEO4J_URI`, `NEO4J_USER`, `GRAPHITI_URL`, `AWS_REGION=us-east-1`, `AWS_PROFILE`). Everything else removed — it's resolved via the trimmed `secure-env.sh` at process start, never written to disk. This absorbs the intent behind [WIP-IGOR/config/core.env.example](WIP-IGOR/config/core.env.example).

6. **`WIP-IGOR/config/secrets-manifest.csv`** — rewrite: `openclaw/*` → `openclaw-igorbot/*`, correct `json_key` values to match real AWS field names (e.g. telegram's field is `bottoken`, not `apikey`), remove the stale perplexity/notion/goplaces/whisper/nano-banana/sag *config_path* rows (no such plugin or skill entries exist in `config/openclaw.json` today), and add a `resolution_path` column per row: `local-only` (3 LLM keys), `exec-native` (gateway token, telegram bot token), `secure-env-only` (everything else actively consumed — Telegram allowlist, GitHub, Hetzner, Neo4j, Cloudflare, Coolify, Vercel, ClawHub, Sonar, GitGuardian), or `provisioned-dormant` (Notion, Google Places, Whisper, Nano Banana, CEG — provisioned in AWS, zero references found in any `workspace/skills/**` script as of this audit).

7. **`WIP-IGOR/config/provider-template.json`** — replace with the real exec-provider shape pointing at `bin/openclaw-aws-resolver.py`, scoped to the 2 fields it actually serves (`gateway.auth.token`, `channels.telegram.botToken`) — not a generic "works for everything" template.

8. **`WIP-IGOR/cursor-prompt-igorbot-hetzner-restore.md`** — rewrite:
   - Phase 0: fix secret-existence checks to `openclaw-igorbot/*` / `us-east-1`.
   - Phase 1/2: provision the VPS via `hcloud`, then clone the repo and run the existing `deploy.sh` instead of hand-rolled Docker/Node/OpenClaw steps.
   - Phase 2.2: write only the 3 LLM keys + `NEO4J_PASSWORD` into `.env` (fetched from AWS once at provisioning time, then static); everything else resolved by the exec provider (2 fields) or the trimmed `secure-env.sh` (everything else) at gateway start.
   - Phase 3: replace the `openclaw config set models.providers...` calls (no such block exists in the real running config) with the corrected, narrow exec-provider wiring, including the schema-verification step from #2.
   - Phase 4–6: keep validation/Telegram-response checks; update secret names in health-check commands.

9. **Manifest consistency cleanup (repo-wide)**:
   - [workspace/TOOLS.md](workspace/TOOLS.md) — fix region references (us-east-2 → us-east-1) in every command block and the legacy-vars table; correct the "Used by" column for rows that named a skill/feature not actually present in the codebase (e.g. `GOOGLE_PLACES_API_KEY` → "provisioned, not currently consumed by any active skill" instead of "Material match, geo lookups"); fix the two AWS endpoints in the UFW egress table if that section still lists them; document the exec-resolver + LLM-local-only split as the new canonical manifest.
   - [bin/ufw-docker-egress.sh](bin/ufw-docker-egress.sh) — fix the 2 hardcoded `us-east-2` AWS endpoints (`secretsmanager.us-east-2.amazonaws.com`, `sts.us-east-2.amazonaws.com`) to `us-east-1`. Note: these entries are in the **container-only** `DOCKER-USER` egress chain; the gateway process and `secure-env.sh` run at host level and are unaffected by this allowlist either way — this is a correctness fix, not a functional blocker.
   - [credentials/aws-secrets-setup.sh](credentials/aws-secrets-setup.sh) — header region fix.
   - [docs/secrets_structure.md](docs/secrets_structure.md) — fully stale (`clawdbot/*`, us-east-2); rewrite to point at `workspace/TOOLS.md` as the single source of truth with corrected naming/region.
   - [workspace/contracts/03-credential-provisioning.md](workspace/contracts/03-credential-provisioning.md) — fix stale `clawdbot/*` references.
   - `CLAUDE.md` — fix the "Secret namespace" line (`clawdbot/*` us-east-2 → `openclaw-igorbot/*` us-east-1).
   - `workspace/.brv/context-tree/infrastructure/igorbot/aws_secrets_configuration.md` left as-is (dated ByteRover historical record, not living docs).

## Validation (per change, concrete and non-fake)

- **Resolver script**: manual invocation with a hand-built stdin payload against one real secret id (e.g. `openclaw-igorbot/github#token`) and one deliberately-missing id — confirm the JSON output shape matches the documented protocol and the missing id comes back as a `NOT_FOUND` error, not a crash. `python3 -m py_compile bin/openclaw-aws-resolver.py`.
- **`config/openclaw.json`**: `python3 -c "import json; json.load(open('config/openclaw.json'))"` (already the `make health` check) for syntax; `openclaw config validate` and `openclaw secrets audit --check` / `--allow-exec` run on the VPS (or a matching local install) before it's treated as done.
- **`bin/secure-env.sh` / `deploy.sh`**: `bash -n` syntax check on both; dry-run `secure-env.sh` with real AWS credentials present and confirm the 3 LLM vars are absent from its output while everything else still resolves.
- **Restore prompt / manifest docs**: cross-check every secret id and field name mentioned against the corrected `workspace/TOOLS.md` table for consistency — no two files should disagree on namespace, region, or field name after this change.
- Report results honestly per the repo's GMP-report convention (`reports/GMP-Report-###-...`) if/when this plan is executed — not as a separate zip bundle or ad-hoc doc set.

## Not in scope

- Not touching `provision/provision_igorbot.sh` (older, Python-based, inconsistent with `deploy.sh` — flagged as legacy but not part of this restore path unless you want it reconciled too).
- Not changing the GitHub remote/clone URL — confirmed `git remote -v` matches `Quantum-L9/igorbot`, same as the restore prompt.
- Not adding config wiring for any skill/plugin that doesn't already exist in `config/openclaw.json` (Notion, Google Places, Whisper, Nano Banana, CEG, ClawHub registry) — those stay dormant-but-provisioned until you decide to actually add those skills.
