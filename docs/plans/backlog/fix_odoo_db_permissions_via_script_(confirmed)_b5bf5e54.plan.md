---
name: Fix Odoo DB Permissions via Script (Confirmed)
overview: "We will create a script `scripts/fix_db_permissions.py` that connects to the PostgreSQL database at `192.168.1.1` using the **superuser** credentials (user: `postgres`) to grant the necessary permissions to the **Odoo user** (user: `p_cryptoxdog`). This will allow Odoo to see and create databases."
todos:
  - id: create-fix-script
    content: Create scripts/fix_db_permissions.py
    status: pending
  - id: run-fix-script
    content: Run the script and fix permissions
    status: pending
isProject: false
---

### 1. Create Script: `scripts/fix_db_permissions.py`

- This script will prompt you for the **superuser password** (for user `postgres`).
- It will connect to `192.168.1.1` port `5432`.
- It will execute: `GRANT SELECT ON pg_database TO "p_cryptoxdog";` (or whatever your Odoo user is named in `odoo.conf`).
- It will also check if the database `cryptoxdog-ib-odoo-19-staging-29047277` exists, and create it if missing.

### 2. Run the Script

- You will run: `python3 scripts/fix_db_permissions.py`
- You will enter the password for the `postgres` user on `192.168.1.1`.

### 3. Verify

- Restart Odoo. The "permission denied" error should be gone.
