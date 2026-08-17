# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Session bills Anthropic | Launched bare `claude` | Use `scripts/claude-deepseek.sh` |
| 401 / invalid auth | `ANTHROPIC_API_KEY` still set, or key in wrong var | Unset `ANTHROPIC_API_KEY`; use `ANTHROPIC_AUTH_TOKEN` |
| 404 on model | Model string typo | Use `deepseek-v4-pro[1m]` / `deepseek-v4-flash` |
| Session dies on "let me look at the image" | Multimodal tool path unsupported | Avoid image tools; restart session |
| Works in terminal, not in plugin pane | Plugin pane spawned a shell without env | Launch from the same terminal, or set env in your shell profile |
| Verify script says "not ignored" | `.gitignore` missing entry | Add `.env.local` and `.env.*.local` |
