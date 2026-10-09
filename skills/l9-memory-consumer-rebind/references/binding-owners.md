<!-- L9_META
schema: 1
parent: l9-memory-consumer-rebind
layer: reference
role: binding-owners
status: active
-->

# Binding owners

Load this only while changing the pin.

| Owner | Change |
|---|---|
| `ops/config/memory-binding.json` | Expected version, source ref, tag, tag object, wheel filename, wheel sha256, release evidence. Do not set `installed_record_digest`. Do not change contract or schema semantics that the release did not change. |
| `ops/config/memory-canonical-epoch.json` | Same release identity the binding now claims. Epoch tests compare the two. |
| `pyproject.toml` | Version pin. Remove a path override only when the registry wheel is the admitted bytes. |
| `uv.lock` | Regeneration of that one distribution. Any other package change is a separate decision in the skill entrypoint. |
| `ops/vendor/wheels/` | Delete the previous wheel when the override is removed. Do not leave two active versions. |
| `CANONICAL_LAW.md` | Append the new pin. Do not rewrite the previous pin section. |
| `ops/scripts/ensure_uv_environment.sh` | The sync-and-seal owner. Run it. Do not add a second installer. |
| `ops/memory/seal_artifact_provenance.py` | Writes the PEP 610 archive hash the binder trusts. |

A `pyproject.toml` overwrite needs `ALLOW-ROOT-DELETION: pyproject.toml` in that commit message, naming the vendor-override removal.

The sealed interpreter must report `exact` and `artifact_sha256` equal to the admitted wheel. `compatible` means the version matched and the artifact was not proved. Heal installs the locked source. It must not restore the previous pin or an adjacent checkout.
