<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: adapter
role: platform-adapter
version: 1.1.0
status: active
-->

# Claude Code Adapter

Use the canonical skill directory without rewriting its doctrine. Install only to a path verified from the active Claude Code environment. Preserve relative references and run the bundled validators before installation.

Add a tool restriction only when the user requests a restricted tool surface:

- In a governed repository (the default), write it as `metadata.allowed-tools`. A top-level `allowed-tools` key is rejected by the install gate, as `references/meta-standard.md` states. Claude Code does not enforce the nested key: it records the requested restriction, and enforcement comes from the repository's own permission settings. Say so to the user rather than presenting it as a sandbox.
- For a pack published outside a governed repository, where Claude Code reads a top-level `allowed-tools`, opt in explicitly and validate with `python scripts/validate_skill_pack.py <pack> --frontmatter-profile agent-skills`. Never make that profile the default.
