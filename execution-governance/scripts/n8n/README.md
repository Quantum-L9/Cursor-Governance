---
title: n8n Scripts
version: 1.0.0
created: 2025-11-07
type: execution-scripts
category: n8n
---

# n8n Execution Scripts

Shared utilities for working with n8n workflows, nodes, and API.

## Scripts

### `n8n_api_client.py`
REST API client for interacting with n8n instances.

**Usage:**
```bash
python3 .cursor-commands/execution/scripts/n8n/n8n_api_client.py <command> [args...]
```

**Commands:**
- `test` - Test API connection
- `list-workflows` - List all workflows
- `get-workflow <id>` - Get workflow details
- `list-executions` - List recent executions
- `list-credentials` - List all credentials

**Configuration:**
- Loads credentials from `env.variables.n8n.ssot.csv` in project root
- Or from environment variables: `N8N_BASE_URL`, `N8N_API_KEY`

### `n8n_node_knowledge_base.py`
Builds comprehensive knowledge base of all n8n nodes from GitHub.

**Usage:**
```bash
# Quick mode: just fetch node names
python3 .cursor-commands/execution/scripts/n8n/n8n_node_knowledge_base.py quick

# Full mode: build complete knowledge base
python3 .cursor-commands/execution/scripts/n8n/n8n_node_knowledge_base.py
```

**Output:**
- `n8n_nodes_kb.json` - Complete node database
- `N8N_NODES_REFERENCE.md` - Markdown reference document

### `csv_env_loader.py`
Loads environment variables from CSV file.

**Usage:**
```bash
python3 .cursor-commands/execution/scripts/n8n/csv_env_loader.py <command> [args...]
```

**Commands:**
- `list` - List all environment variable keys
- `get <key>` - Get value for a specific key
- `show <key>` - Show key, value, and usage syntax
- `load` - Load all variables and show summary

**CSV Format:**
Expected file: `env.variables.n8n.ssot.csv` in project root
- Columns: `Key`, `Value`, `Usage Syntax`

## Access from Any Workspace

These scripts are accessible from any workspace via the `.cursor-commands` symlink:

```bash
# From any workspace with Suite 6 governance enabled
python3 .cursor-commands/execution/scripts/n8n/n8n_api_client.py test
```

## Dependencies

- Python 3.8+
- `requests` library
- `pyyaml` (for node knowledge base)

Install dependencies:
```bash
pip3 install requests pyyaml
```

## Notes

- Scripts search for `env.variables.n8n.ssot.csv` in multiple locations:
  1. Script directory
  2. Current working directory
  3. Project root
- All scripts are executable (`chmod +x`)

