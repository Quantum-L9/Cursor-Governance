# Versioning — Headers, Archiving, and Version Map

## Mission
Guarantee traceability and consistency across all files (code, JSON, YAML, Markdown, n8n exports). Every artifact must carry a complete header and follow semantic versioning with auditable history.

---

## Standard Header (Insert at Top of Every File)
```
/*
====================================================================
 Workflow: <Workflow Name>
 Agent: <Primary Agent>
 Sub-Agent: <Sub-Agent or Node>

 File: <filename_with_version.ext>
 Created: <YYYY-MM-DD HH:MM:SS UTC>
 Last Modified: <YYYY-MM-DD HH:MM:SS UTC>
 Version: v<major.minor.patch>
 Author: <Assistant/Tool Name>
 Description: <one-liner purpose>
 Dependencies: <key libs/other files/APIs>
====================================================================
*/
```
- Always UTC timestamps (ISO-like: `YYYY-MM-DD HH:MM:SS UTC`).
- Update **Last Modified** and **Version** on every change.
- If filetype forbids comments, add a sibling `<filename>.meta.json` with the same fields.

---

## Semantic Versioning Rules
- **Major**: breaking changes, schema/structure shift
- **Minor**: new features or nodes, non-breaking
- **Patch**: fixes, refactors, docs-only changes

### Auto-Increment Logic
- If newer version exists, bump logically (major/minor/patch) based on change type.
- Never overwrite silently; archive previous version and update the version map.

---

## File Naming
- Prefer: `<Workflow>_<Agent>_<SubAgent>_vX.Y[.Z].ext`
- For n8n collections: `<Workflow>_collection_vX.Y.json`

---

## Version Map
Maintain `version_index.json` at repo root with entries like:
```json
{
  "PlasticBroker_LeadGenPipeline": {
    "lead_parser_v3.2.js": {
      "version": "v3.2",
      "created": "2025-10-06 15:42:00 UTC",
      "last_modified": "2025-10-06 16:12:00 UTC",
      "agent": "DataExtractionBot",
      "sub_agent": "ArticleParser_Node",
      "archived_from": "v3.1"
    }
  }
}
```
- Update map on every create/modify/archive.
- If mismatch between header and map, **repair automatically** (header is the source of truth).

---

## Archiving Policy
- Move superseded versions to `/archive/<workflow>/<filename_version>/`
- Keep latest **5** per file unless otherwise requested.
- Log moves to `/logs/version_history.txt` (timestamp + reason).

---

## Enforcement
- If header missing/invalid → add/fix silently.
- If older version in active dir → **promote** or **merge** into the latest, then archive older.
- Output a **Versioning Summary** in the Delivery Log.
