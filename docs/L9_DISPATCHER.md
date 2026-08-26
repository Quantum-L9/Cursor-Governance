# The `l9` dispatcher — one thin facade over the Governance Makefile

`l9` is the single cross-repo command facade. It contains **no build logic** and
**no second target registry**. It resolves the Governance runtime clone, asks
the canonical `Makefile` which targets are `CONSUMER_SAFE`, and delegates:

```bash
l9 <target> [make-args...]   →   make -C "$HOME/.cursor-governance" <target> WS="$PWD"
```

## Why one facade

- **One Governance Makefile** owns every build/validation/publish recipe. There
  are no consumer `Makefile` copies and no per-repo wrappers.
- **`CURDIR` vs `WS`.** Inside `make -C "$GOV"`, `CURDIR` is always the
  Governance implementation root; `WS` (default `$(CURDIR)`, overridden by the
  dispatcher to `$PWD`) is the consumer workspace the caller is in. A
  `CONSUMER_SAFE` target acts on `$(WS)`; Governance-internal work uses
  `$(CURDIR)`. The dispatcher can therefore never mutate Governance by path
  confusion — it only sets `WS`, never `-C`, from the caller's directory.

## Classification authority

The `Makefile` is the **single** classification authority. `CONSUMER_SAFE`
targets are listed once, in `L9_CONSUMER_SAFE_TARGETS`, and printed by:

```bash
make -C "$HOME/.cursor-governance" --no-print-directory l9-consumer-safe-list
```

The dispatcher queries that list and refuses anything not on it. A target is
`CONSUMER_SAFE` only when it is WS-aware — it reads/writes the consumer
workspace through `$(WS)` and does not assume the caller is inside Governance.

| Class | Meaning | Reached by |
|---|---|---|
| `CONSUMER_SAFE` | WS-aware; safe to run against any consumer workspace | `l9 <target>` |
| `GOVERNANCE_ONLY` | operates on the Governance clone itself (validators, PE/campaign internals, `venv`, `backup`, `sync`, `push`, `ff`, corpus lint/test) | `make -C "$HOME/.cursor-governance" <target>` |

`GOVERNANCE_ONLY` targets are intentionally **not** exposed through `l9`; run
them directly against the Governance clone. Diagnostics that ignore `WS` (e.g.
`graphiti-health`) are Governance-scoped and likewise not exposed.

## Install / verify

The repo-owned source is the only dispatcher:

```
environment/agents/adapters/claude-code/bin/l9
```

It is installed to the first-on-PATH user bin as a **real file** (so it survives
a runtime-clone refresh mid-session):

```bash
make l9-dispatcher-install     # install/reconcile → $HOME/.local/bin/l9
make l9-dispatcher-check       # report drift, write nothing
```

The adapter `install.sh` and SessionStart run the same reconcile, so a cached
environment self-heals without a manual step.

## Usage

```bash
cd /path/to/consumer-repo
l9 --list                      # print the CONSUMER_SAFE allowlist
l9 start                       # run the session-start pipeline against this repo
l9 pr PR_BASE=origin/main      # gate + open PR for this repo (make-vars forwarded)
l9 claude-env                  # structural + runtime readiness for this repo's wiring
```

Exit status is propagated from `make`. A missing Governance runtime clone, or a
Makefile that cannot report its allowlist, is fail-closed (exit 3): the
dispatcher never guesses a target list.
