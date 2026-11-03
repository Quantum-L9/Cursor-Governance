<!-- L9_META
schema: 1
parent: l9-release-publication
layer: reference
role: tag-push-transport
version: 1.0.0
status: active
-->

# Publication plane: pushing one tag ref

Applies to TAG_TRIGGERED and NO_AUTOMATION, the two models where you push a tag.
In MAIN_TAGGER you never push a tag.

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
3. In a later command, push exactly one ref: `git push origin refs/tags/<tag>`.
4. Remove the receipt as soon as the push returns, success or failure:

   ```bash
   rm -f ~/.l9/autonomy/publish-path-override.json
   "$GOV_PY" "$GOV/ops/autonomy/breakglass_receipt.py" --status
   ```

Never write the receipt and push in one shell command: the hook inspects the push
before the command runs, so the receipt would not exist yet.

## Denied substitutes

- `--force`, `--tags`, deleting the tag, or pointing `refs/tags/<tag>` at another sha.
- Creating the tag object through the host API: a new object has a new sha even
  when the message matches.
- Leaving the receipt in place, or using it for anything but that one ref.
