---
name: Add local config files to gitignore
overview: Add `.cursor/`, `.cursor-commands/`, and `scripts/setup-new-workspace.yaml` to `.gitignore` to prevent local config from being tracked.
todos:
  - id: add-gitignore
    content: Add .cursor/, .cursor-commands/, and scripts/setup-new-workspace.yaml to .gitignore
    status: pending
isProject: false
---

# Add local config files to .gitignore

## Change

Add the following to `[.gitignore](.gitignore)`:

- `.cursor/` - Cursor IDE local config
- `.cursor-commands/` - Cursor governance commands (symlinked from Dropbox)
- `scripts/setup-new-workspace.yaml` - workspace setup config

## Implementation

Append the following lines to the end of `.gitignore` (after line 44, after `generated/`):

```
# Cursor IDE (local config)
.cursor/
.cursor-commands/

# Workspace setup
scripts/setup-new-workspace.yaml
```

