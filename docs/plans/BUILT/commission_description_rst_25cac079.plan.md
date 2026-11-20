---
name: Commission description RST
overview: Stop the plasticos_commission docutils warnings by giving the module a short
  reStructuredText manifest description, so Odoo never feeds README.md to the RST
  parser. Bump the module so a running database picks that description up.
todos:
- id: manifest-description
  content: Add the RST description key and bump plasticos_commission to 19.0.1.4.8
  status: completed
- id: verify-update
  content: Format the manifest and upgrade only plasticos_commission
  status: completed
isProject: false
built: true
status: built
---

# Stop commission README RST warnings

Odoo stores `ir.module.module.description` from [`Manifest.description`](file:///Users/ib-mac/dev/odoo-19/odoo/modules/module.py) and later runs that string through docutils in `_get_desc`. A non-empty manifest `description` wins over `README.md`. [`plasticos_commission/__manifest__.py`](plasticos_commission/__manifest__.py) has no such key (version `19.0.1.4.7`), so the Markdown readme is parsed as RST.

## Change

In [`plasticos_commission/__manifest__.py`](plasticos_commission/__manifest__.py), after `summary`, add the same kind of plain RST description already used by [`plasticos_product/__manifest__.py`](plasticos_product/__manifest__.py):

```python
"description": """
PlasticOS Commission Engine
===========================
Commission rules, payout management, and the sales rep deal dashboard.
""",
```

Leave [`plasticos_commission/README.md`](plasticos_commission/README.md) unchanged. It stays the developer note and is no longer the Apps description.

Bump `"version"` from `19.0.1.4.7` to `19.0.1.4.8`. No migration folder: this is manifest metadata, rewritten on a normal module update. Odoo.sh only reloads a module when that version advances, so without the bump the stored Markdown description and the warnings remain.

## Verify

`ruff format plasticos_commission/__manifest__.py`, then `make update m=plasticos_commission`. The upgrade log for this module should no longer print the docutils `---|` / backtick messages. Do not upgrade any other module.

## Build evidence (auto)

- detected_at: `2026-11-09T22:30:16Z`
- conversation_id: `9e1f7482-58bc-4136-8d6f-c92d0f614af5`
- generation_id: `fdbdd29b-9644-4c8a-babc-b757d6a13d7e`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/9e1f7482-58bc-4136-8d6f-c92d0f614af5/9e1f7482-58bc-4136-8d6f-c92d0f614af5.jsonl`
- todos at build time:
- `manifest-description`: completed
- `verify-update`: completed
