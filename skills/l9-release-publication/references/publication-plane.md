<!-- L9_META
schema: 1
parent: l9-release-publication
layer: reference
role: tag-push-transport
version: 1.0.0
status: active
-->

# Publication plane: pushing release tag refs

Applies to TAG_TRIGGERED and NO_AUTOMATION, where you push the exact tag, and to any
model where the completion loop (`complete_release.py`) plans an agent tag push
because the release job will not. In MAIN_TAGGER you push a tag only on that plan.

Advancing an existing major tag is not an agent push: the git guardrails deny a lease
push onto a shared tag ref without `L9_GIT_DESTRUCTIVE_AUTHORIZED`, which only the
operator sets. The loop hands that command to the operator.

Read `ops/autonomy/first_publication_gate.py` and `ops/autonomy/breakglass_receipt.py`
in the governance checkout (`$HOME/.cursor-governance`) before pushing. The rules
below are their observed behavior; if the files disagree, the files win and this
note is stale.

## Why `make pr` cannot do this

`make pr` publishes a branch (`git push -u origin HEAD`). A `git push` of
`refs/tags/<tag>` has no open pull request, so the gate treats it as a first
publication and denies it. Opening another pull request does not move a tag.

## Authorized push

The hook allows the push when `breakglass_reason()` is non-empty. It reads
`L9_LOCAL_PUSH_AUTHORIZED` from the hook's own process (a prefix on the pushed command
is invisible to it) or the receipt file `~/.l9/autonomy/publish-path-override.json`.

1. Only after the operator ordered publication of the verified tag, write the receipt
   in its own command:

   ```bash
   "$GOV_PY" "$GOV/ops/autonomy/breakglass_receipt.py" --write --issuer ops --hours 1 \
     --reason 'publish existing tag <tag> object <obj> peeled <commit>; no force, no recreate'
   ```

   Confirm the status line says the grant is in force.
2. `verify_release_tag.py ... --remote owner/name --bind-origin` must already have
   returned `REMOTE_ABSENT` or `MATCH` for that origin.
3. In a later command, push exactly the refs the plan names, one ref per command
   (for example `git push origin refs/tags/<tag>`).
4. Remove the receipt as soon as the push returns, success or failure:

   ```bash
   rm -f ~/.l9/autonomy/publish-path-override.json
   "$GOV_PY" "$GOV/ops/autonomy/breakglass_receipt.py" --status
   ```

Never write the receipt and push in one shell command: the hook inspects the push
before the command runs, so the receipt would not exist yet.

## Session transport refuses the tag push

A hosted session's git transport can push branches but refuse a tag ref: the push
fails with `RPC failed; HTTP 403` while the gate allowed it (observed 2026-11-03,
`Quantum-L9/l9-constellation-topology` v2.0.0). That is a transport policy, not a
gate decision. Remove the receipt, do not retry, and do not substitute the host API
(below). Hand the operator the tag commands to run from their own clone,
`git tag -s <tag> <commit> -m "<tag>"` then `git push origin refs/tags/<tag>`, and
continue from the Release step once `verify_release_tag.py --require-remote` returns
`MATCH` for the tag object they pushed.

## Denied substitutes

- `--force`, `--tags`, deleting the tag, or pointing `refs/tags/<tag>` at another sha.
- Creating the tag object through the host API: a new object has a new sha even
  when the message matches.
- Leaving the receipt in place, or using it for anything but the release refs the
  loop's plan names.
