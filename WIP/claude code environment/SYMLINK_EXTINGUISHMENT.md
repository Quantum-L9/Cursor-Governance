# Transitional symlink extinguishment

`environment/claude-code` → `environment/agents/adapters/claude-code`

Remove only after CI greps show zero remaining hardcoded consumers of
`environment/claude-code/` outside the symlink itself and this note.
