# Copy-paste prompt for Cursor Agent

Paste into Cursor Agent (Agent mode), repo open, fresh branch.

---

```
Read ./skills-normalization-pack/STANDARD.md and NORMALIZE_TASK.md.

Execute STAGE 1, STAGE 2, and STAGE 3. Stop before STAGE 4.

Stage 1 nests non-native frontmatter under `metadata:` - it MOVES fields, it
does not delete them. Nothing may be lost.
Stage 2 locks down archived skills.
Stage 3 is the audit report only - measure, do not change.

Hard constraints:
- Do NOT add `paths` to any skill in this run. Scoping is Stage 4 and needs
  my per-skill approval, because a wrong glob hides a skill silently.
- Do NOT rewrite any description in Stage 1-3. Report candidates only.
- Verify `name` matches its parent folder for every skill; report mismatches,
  fix none without telling me.
- Do not touch CANONICAL_LAW.md, ORG_INVARIANTS.yaml, CODEOWNERS,
  .claude/settings.json, or .claude/hooks/**.
- skills/AUTONOMY_MANIFEST.yaml is not a skill. Do not modify it, but do check
  whether it references frontmatter fields you are about to move.
- Branch: chore/skills-normalization. Do not commit or push.

Report: fields nested per skill with counts, name/folder mismatches, archived
skills missing disable-model-invocation, the total discovery footprint in
bytes and tokens, and descriptions outside the 150-500 char band.
```

---

Stage 4 is `PATHS-PROPOSAL.md`, one skill per commit.
