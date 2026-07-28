# Network access — Claude Code Web & Mobile

Set once in `claude.ai/code` → open your environment → edit → **Network access**.
The environment is **account-level**, so the same policy applies to **Claude Code
Mobile** — sessions started from the phone inherit it. Changes apply to **new
sessions only**; start a fresh session after saving.

## Option A — Full (simplest, most friction removed)

**Network access → Full.** Removes every egress block a governance/remediation
session tends to hit (package registries, `github.com`, scanner APIs). Choose this
when the sandbox is trusted and you want zero allowlist maintenance.

## Option B — Custom (least privilege)

**Network access → Custom**, keep the defaults, and add only what the workflow
needs. Baseline allowlist for L9 work:

| Host | Why |
|---|---|
| `github.com`, `*.githubusercontent.com` | clone governance + consumer repos, `gh` API, pushes |
| `api.github.com` | `gh` CLI (CI logs, reviews, PR/thread operations) |
| `pypi.org`, `files.pythonhosted.org` | Python toolchain (`ruff`, `mypy`, `pytest`) |
| `registry.npmjs.org` | Node toolchain (`biome`, project deps) |
| `cli.github.com` | `gh` install in `setup.sh` |

Add scanner hosts **only** if that repo's gate uses them, e.g.
`sonarcloud.io`, `*.sonarcloud.io`, `semgrep.dev`, `*.semgrep.dev`.

For **shared memory across separate cloud containers**, add the routable host you
bind the memory server to (see `network-policy` note in `../mcp.template.json` and
`web/README.md` §Shared memory). Loopback (`127.0.0.1`) never crosses containers.

## Which to pick

Start with **Full** to prove the environment end-to-end with no allowlist
friction, then tighten to **Custom** with the table above once the workflow is
known. Both are valid; Custom is the least-privilege posture for shared sandboxes.
