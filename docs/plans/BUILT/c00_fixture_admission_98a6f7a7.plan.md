---
name: C00 fixture admission
overview: 'Execute contract C00 only: prove the live pinned Enterprise template, restore-test
  a backup, and admit `odoo_test_tpl_ee_c9e8a81f52f23680` for the current image and
  Postgres 15. No application source edit, publication, merge, or volume upgrade.'
todos:
- id: e01-inventory
  content: Bind Staging worktree and capture read-only project, image, Postgres 15,
    and template identity without test_env.sh status
  status: completed
- id: e02-restore
  content: Dump the pinned template, filestore, and evidence; restore into odoo_test_c00_restore
    and compare counts
  status: completed
- id: e03-admit
  content: Drop only a proven-stale pin under the template lease, then admit it with
    TEST_ENV_ALLOW_NEW_TEMPLATE
  status: completed
- id: e04-clone-test
  content: Run make test-module m=plasticos_security_base on a fresh owned clone and
    confirm the image digest is unchanged
  status: completed
- id: receipt
  content: Write the uncommitted C00 receipt with A-ENV-IMAGE and A-ENV-POSTGRES dispositions
  status: completed
isProject: false
built: true
status: built
---

# C00 Enterprise fixture admission

Execute [contracts/00_ENTERPRISE_FIXTURE.yaml](docs/campaigns/10-27-26/Odoo_PR_Remediation_Hardened_v2_2026-10-27/contracts/00_ENTERPRISE_FIXTURE.yaml) only. Findings: `A-ENV-IMAGE` (E01–E04) and `A-ENV-POSTGRES` (E01). Result label is `LOCAL_VERIFIED` or `BLOCKED`. No commit.

## Bound state

- Current checkout is dirty `feat/crm-lead-material-identity` at `524f8db2`. Leave it, and leave the preserved worktrees `wt-linda-native-dispatch` (`53cb6316`) and `wt-crm45-pr314` (`ca4f3f26`), alone.
- `origin/Staging` is `e22eb6c0c34d9ea124ae4a04715f7948c3316d86`, the contract base. `scripts/test_env.sh`, [config/test_env_fixture.conf](config/test_env_fixture.conf), `docker-compose.yml`, `Dockerfile`, and `config/odoo_module_order.yaml` match that baseline. The feature-branch Makefile does not; the build uses Staging.
- Fetch, then add one clean worktree at the resolved `origin/Staging` SHA. Do not reuse `wt-origin-staging` or `wt-staging-baseline`; those checkouts are older. Many other worktrees share compose project `odoo19` and volume `odoo19_odoo_pgdata`.

## E01 — read-only inventory before any runner command

Do not run `scripts/test_env.sh status` or `make test-env`. Those start Postgres and build the Odoo image.

Record, with the commands used:

- Compose project `odoo19`, db container, volume `odoo19_odoo_pgdata`, and filestore volume `odoo_data`.
- Existing image content digest from `docker image inspect` of RootFS layers plus config (the same identity as `image_id()` in [scripts/test_env.sh](scripts/test_env.sh)), full digest, not a prefix.
- Enterprise checkout path and revision from `ODOO_ENTERPRISE_PATH` (default `./odoo-enterprise`).
- If the db container is already running: `server_version` and `server_version_num`, database list, the pinned database comment, `pg_stat_activity`, and advisory-lock holders. If it is stopped, record that stopped baseline first; starting db is the first intentional mutation and happens only after this snapshot.
- Module roster from `scripts/get_odoo_module_order.py`. `base.latest_version` is recorded later and is not the image or server version.

Stop before any drop if the Docker endpoint is not the local daemon, the db container is not this project's db service, the pinned name is missing its `plasticos-test-env/2` template comment, another session holds `tpl:odoo_test_tpl_ee_c9e8a81f52f23680`, or a business database (`odoo`, or any name other than the pinned template and explicitly owned `odoo_test_*` clones) would be touched.

`A-ENV-POSTGRES`: Compose pins `postgres:15`. Record the live major (expected 15.x). The platform note of PostgreSQL 16 stays a documented distinction. Do not upgrade the volume or claim production parity.

## E02 — backup, then a real restore

Under the exclusive template lease, and only for `odoo_test_tpl_ee_c9e8a81f52f23680`:

- Temporarily allow connections, `pg_dump -Fc`, then put `ALLOW_CONNECTIONS false` / `IS_TEMPLATE true` back.
- Copy that database's filestore from `odoo_data` and the existing `.l9/runtime/test-env/odoo_test_tpl_ee_c9e8a81f52f23680.inputs.txt` and `.admission.txt` if present.
- Hash and size every artifact. A truncated dump or missing filestore stops the slice.

Restore into one new owned database `odoo_test_c00_restore` plus its filestore. Compare module, attachment, and object counts to the source. Mismatch stops retirement. Keep the dump. Drop only the restore-check database after the counts match; it is not the template.

## E03 — retire only a proven-stale pin, then admit

`certify_pinned_fixture` never rebuilds. `build_template` creates the pinned name only when that database is absent and `TEST_ENV_ALLOW_NEW_TEMPLATE` equals it.

- If the comment `fp` already equals the current fixture inputs, do not drop it. `A-ENV-IMAGE` is `ALREADY_SATISFIED` on this host. Continue to E04.
- If it is admitted for other inputs (the reported image drift), hold the exclusive lease, confirm `template_references` is empty and no clone stage container is running, then drop that one database with Odoo's db manager using `-c /dev/null` (so [config/odoo.conf](config/odoo.conf) cannot redirect onto the business database `odoo`) and clear its filestore. Any other database stays.
- From the clean Staging worktree:

```bash
TEST_ENV_ALLOW_NEW_TEMPLATE=odoo_test_tpl_ee_c9e8a81f52f23680 make test-env
```

Admission must show one US company, chart `us`, USD, sale and purchase taxes, sale/purchase/bank/general journals, the declared module set installed, and no mid-transition modules. The runner writes `.l9/runtime/test-env/odoo_test_tpl_ee_c9e8a81f52f23680.admission.txt` and `.inputs.txt` only after that. A failed build stays on `odoo_test_bld_ee_<fp>`; it is not renamed onto the pin and gets no ready comment. Backups stay.

## E04 — one fresh clone, nonzero tests

From the same worktree, `make test-module m=plasticos_security_base`. The native runner upgrades the declared PlasticOS roster on a new owned clone, then runs that module's tests (`plasticos_security_base/tests/test_purchase_order_access.py`). Zero tests, a failure, an error, a missing Odoo summary, or a run aimed at the template or the `odoo` database fails the slice.

Before the run, confirm Compose has no live SMTP server and that Gate URL/signing material are empty or unused by this test path. Re-read the image content digest after the run. If `compose build` inside the runner changed it, E04 fails and the ready marker is not treated as current.

App source edits later upgrade clones. They do not rebuild this template.

## Receipt

Write an uncommitted receipt at [evidence/C00_FIXTURE_RECEIPT.yaml](docs/campaigns/10-27-26/Odoo_PR_Remediation_Hardened_v2_2026-10-27/evidence/C00_FIXTURE_RECEIPT.yaml) with the inventory, backup hashes, restore counts, admission line, clone owner, source SHA, addon digest, server and Enterprise versions, test counts, and both finding dispositions. No PR, merge, deploy, or branch deletion.

## Build evidence (auto)

- detected_at: `2026-10-27T19:16:11Z`
- conversation_id: `e4bd7a32-3211-4dde-b150-c2f9fe7296a0`
- generation_id: `fee9c9f0-f32b-4d2e-82c4-118324793ce3`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/e4bd7a32-3211-4dde-b150-c2f9fe7296a0/e4bd7a32-3211-4dde-b150-c2f9fe7296a0.jsonl`
- todos at build time:
- `e01-inventory`: completed
- `e02-restore`: completed
- `e03-admit`: completed
- `e04-clone-test`: completed
- `receipt`: completed
