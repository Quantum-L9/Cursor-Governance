---
name: l9-memory-consumer-rebind
description: Rebind a governed consumer onto one immutable published l9-graphite-memory release. Verify the official wheel digest, replace the vendored pin with the registry lock, seal PEP 610 provenance, prove signed-agent grants and Cursor and Claude MCP on an isolated store, then publish once through make pr. Use when a tagged memory release must replace the consumer pin. Do not use for hydrate debugging, host deployment, retagging the release, or a live workstation MCP cutover.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, memory, release, consumer, wheel, mcp]
  owner: igor_beylin
  status: active
  version: "1.0.0"
  updated: "2026-10-08"
  license: Proprietary
---

# Memory consumer rebind

## Purpose

Replace the consumer's memory pin with one immutable published release and prove the bound runtime, then publish that consumer change once.

## Authority

1. The admitted release identity supplied for this rebind (version, tag, tag object, peeled source, wheel filename, wheel sha256).
2. The official published wheel bytes. A local rebuild is evidence only when its digest equals that sha256.
3. `ops/config/memory-binding.json` and the lockfile.
4. The bound package's grant schema and MCP configurator.
5. Inference. Never substitute a digest, retarget a tag, or treat a version string as provenance.

## Activation boundary

Run only for a consumer pin change onto an already-published memory release.

Do not run for hydrate or prefetch repair, a memory-host deploy, a tag move, a schema redesign, or a live workstation MCP cutover. Those stay on their own owners.

## Inputs

Required: distribution name, version, annotated tag, tag-object sha, peeled source sha, wheel filename, admitted wheel sha256, memory schema, control-plane contract.

Optional: release `SOURCE_DATE_EPOCH` and the publish receipt. Use them only for the rebuild comparison.

Unknown release identity or an unobtainable wheel stops the rebind. Do not guess another build.

## Sequence

1. Confirm the consumer publication path is `PR_REMEDIATE=0 make pr` against the integration base, with empty `PR_STACK`. Confirm the annotated tag still peels to the admitted source. Do not move the tag.
2. Obtain the official published wheel. Hash it with [scripts/verify_wheel_digest.py](scripts/verify_wheel_digest.py). Stop if the digest differs.
3. Confirm the wheel exports the required schema, CLI operations, and MCP tools named by the current binding manifest. A matching version string is not enough.
4. Update the binding manifest and the canonical epoch so version, source ref, tag, tag object, wheel name, and wheel sha256 match the admitted release. Leave control-plane semantics and the installed-RECORD pin untouched.
5. If the official wheel is the registry artifact, replace the vendored path override with that pin, delete the old vendored wheel, and lock only this distribution. If the registry artifact is not the admitted bytes, stop.
6. Sync the locked environment and seal PEP 610 provenance. The binding must report `exact` and `artifact_sha256` equal to the admitted digest.
7. Rebuild the wheel from the peeled source with the release epoch. If the digest matches, keep the existing cross-repo rebuild and point it at the admitted digest. If it does not match, change only that proof so it verifies the official artifact. Never replace the admitted digest with the local one.
8. Prove signed-agent grants against the bound package: registry grant in, verifier accepts the typed claims, and missing grant, bad signature, wrong actor, and unauthorized namespace are refused. The launcher's governance root is the checkout that contains the script when that checkout has `CANONICAL_LAW.md`.
9. Prove Cursor MCP by delegating install to the package configurator into a temporary config. The managed entry command is the signed-agent launcher, args are the stdio server, and there is no env block. Prove Claude from the canonical template, not a second MCP file. On an isolated store, one authorized `memory.write_agent` is readable by a second process after restart. Health, search, hydrate, phase lock, and governed write succeed; an unauthorized namespace is refused.
10. Run the existing memory acceptance tests with the cross-repo requirement flag set and the bound interpreter. Zero skips in that run.
11. Hold unrelated dirty files outside the release commit. Commit only the rebind pathspecs. A `pyproject.toml` overwrite carries `ALLOW-ROOT-DELETION` for that file. Authorize the clean tree, then `PR_REMEDIATE=0 make pr` once. Verify the PR base, head, file list, and required checks. Do not merge. Restore the held files.

Load [references/binding-owners.md](references/binding-owners.md) at step 4 and [references/proof-gates.md](references/proof-gates.md) at step 7.

## Decisions

Official wheel digest equals the admitted digest. True: continue. False: stop. Unknown: stop.

Registry bytes are that wheel. True: drop the vendored override and lock the registry pin. False: stop. Do not vendor a second copy of a wheel the registry already serves.

Rebuild digest equals the official digest. True: keep the rebuild proof. False: point the proof at the official artifact. Unknown: stop. Do not call unequal bytes identical.

Lockfile audit fails on a package this rebind did not pin, and the minimum fix stays inside that package's existing constraint as a one-package lock change. True: take that bump. False or a wider lock move: stop.

Live workstation MCP or the SSOT clone is in the request. True only when the user grants cutover. Otherwise leave both unchanged.

## Validation

- `python scripts/verify_wheel_digest.py <wheel> --expect <sha256>` exits 0.
- Bound interpreter: distribution, version, contract, schema, CLI, and `exact` provenance.
- Acceptance tests with the cross-repo flag: failures 0, skips 0.
- `make pr` local gate passes, then the PR head's required checks pass.
- `python skills/l9-skill-compiler/scripts/validate_skill_pack.py skills/l9-memory-consumer-rebind` is the pack gate for this skill, not a substitute for the rebind proofs. Run it from the repository root.

## Stop

Stop when the wheel cannot be obtained, the digest differs, the tag does not peel to the admitted source, the seal is not exact, a required proof skips, or publication was not asked for. Do not open a second publication ceremony to inspect a green tree. A confirmed defect on the open PR gets one fix, a new authorization, and one `make pr` that updates that PR.

## Outputs

A consumer branch whose lock resolves one active release, a sealed interpreter, passing isolated MCP and grant proofs, and one open PR URL with the head SHA and check conclusions. Merge is not an output.

## Compiler controls

This pack was produced by extract_expertise. Intelligence evidence is [skill_intelligence_report.yaml](skill_intelligence_report.yaml). Revalidate with `validate_exemplary_skill.py`. Structural enforcement is `enforcement-gates`.
