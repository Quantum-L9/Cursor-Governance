---
name: Dismiss env injection notice
overview: This is not a repo bug. Cursor’s Python Environments extension is warning that a workspace `.env` exists while terminal injection stays off (the default). You chose to keep injection disabled; dismiss the toast and leave the setting false.
todos:
  - id: dismiss-toast
    content: Click Don't Show Again on the Python Environments toast (update the extension first if the button is missing)
    status: completed
  - id: keep-disabled
    content: Leave python.terminal.useEnvFile false; do not change repo or IDE-profile settings
    status: completed
isProject: false
---

# Dismiss the Python `.env` terminal notice

This is an **info toast**, not a broken terminal or a failed env load. The Python Environments extension sees this workspace’s [`.env`](.env) (via the default `python.envFile` of `${workspaceFolder}/.env`) while [`python.terminal.useEnvFile`](https://code.visualstudio.com/docs/python/settings-reference) is `false`. Injection is **off by default on purpose**.

This repo does not need the setting. [`.env.example`](.env.example) states that no script auto-loads a root `.env`. Your current `.env` also holds live API keys; leaving injection disabled keeps those values out of every integrated terminal.

No files in Cursor-Governance need to change.

## What to do

1. On the toast, click **Don’t Show Again** if it is there. That writes a flag in the Python Environments extension’s global state (not `settings.json`), so saving `.env` later should not retrigger it.
2. If the button is missing, update **Python Environments** (`ms-python.vscode-python-envs`) in Extensions, then save `.env` again and click **Don’t Show Again**. Older builds had no dismiss control ([microsoft/vscode-python-environments#1373](https://github.com/microsoft/vscode-python-environments/issues/1373)).
3. Leave `python.terminal.useEnvFile` **unchecked / false**. Do not add `"python.terminal.useEnvFile": true` to user or workspace settings.
4. Close the toast with the **X** if you only want it gone for this session. It can return the next time `.env` is saved until Don’t Show Again is used.

Optional (clarity only, does not hide the toast): pin the current default in [~/Library/Application Support/Cursor/User/settings.json](/Users/macm2/Library/Application%20Support/Cursor/User/settings.json):

```json
"python.terminal.useEnvFile": false
```

## What not to do

- Do not enable injection for this workspace. This clone’s `.env` is secrets-heavy; new terminals would inherit those variables.
- Do not add this key to the governed IDE profile ([environment/ide/settings.python.json](environment/ide/settings.python.json)). The profile owns type-check mode, not env injection.
- Debugger / Run Python File can still read `python.envFile` even with terminal injection off. That is separate from this toast.

## If it still pops after Don’t Show Again

Confirm the extension is **Python Environments**, not only **Python**. Then Command Palette → **Developer: Reload Window**. There is no supported `settings.json` key to suppress this notice; dismiss is extension state.
