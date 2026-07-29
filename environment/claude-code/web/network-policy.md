# Network access — Claude Code Web & Mobile

Set once in `claude.ai/code` → open your environment → edit → **Network access**.
The environment is **account-level**, so the same policy applies to **Claude Code
Mobile** — sessions started from the phone inherit it. Changes apply to **new
sessions only**; start a fresh session after saving.

Anthropic exposes **four** levels — pick one:

| Level | Egress | Use when |
|---|---|---|
| **None** | No outbound network. | Fully offline work; `setup.sh` cannot clone governance or install `gh` — not viable for L9 sessions. |
| **Trusted** | Curated allowlist of common dev hosts — GitHub + the major package registries (PyPI, npm) are already permitted. | **The no-friction default for a plain Python/TypeScript repo.** Everything `setup.sh` needs is already covered; nothing to maintain. |
| **Full** | Unrestricted outbound. | The sandbox is trusted and you want zero allowlist maintenance *and* reach for arbitrary hosts (e.g. self-hosted scanners on odd domains). |
| **Custom** | Only what you allowlist. | Least-privilege / shared sandboxes where you want to enumerate every reachable host. |

## Option A — Trusted (recommended default, no friction)

**Network access → Trusted.** Its curated allowlist already covers `github.com`,
`api.github.com`, PyPI, and npm — i.e. every host `setup.sh` reaches to clone
governance, install `gh`, and set up Python/Node toolchains. For an ordinary
Python or TypeScript repo this removes all egress friction with **zero allowlist
maintenance**. Step up to **Custom** only if a repo's gate calls a host Trusted
doesn't include (e.g. a private scanner), or down to **Custom** if your posture
requires enumerating every reachable host.

## Option B — Full (broadest, still zero maintenance)

**Network access → Full.** Removes every egress block a governance/remediation
session tends to hit (package registries, `github.com`, scanner APIs on any
domain). Choose this when the sandbox is trusted, you want zero allowlist
maintenance, and you may need to reach hosts outside the Trusted set.

## Option C — Custom (least privilege)

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

For a plain Python/TypeScript repo, start with **Trusted** — it already
allowlists GitHub + the common package registries, so `setup.sh` runs with no
friction and nothing to maintain. Use **Full** only if you need hosts outside the
Trusted set (e.g. scanners on arbitrary domains) and accept unrestricted egress.
Drop to **Custom** with the table above when a shared sandbox requires
enumerating every reachable host — the least-privilege posture. Avoid **None**:
governance can't clone and toolchains can't install.
