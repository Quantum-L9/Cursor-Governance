---
name: Fix Odoo Database Permissions via Script
overview: We will create a Python script (`scripts/fix_db_permissions.py`) to programmatically fix the permission issue. This script will require the **Admin** credentials for the database server (192.168.1.1) to run. It will grant the necessary `pg_database` read permission to the Odoo user and ensure the target database exists.
todos: []
isProject: false
---

### 1. Create Fix Script
- **File**: `scripts/fix_db_permissions.py`
- **Purpose**: Connects to the database as an Admin to grant privileges that the Odoo user cannot grant itself.
- **Logic**:
  1.  Connect to `postgres` database on `192.168.1.1` using **Admin** credentials.
  2.  Execute SQL: `GRANT SELECT ON pg_database TO [target_odoo_user];`
  3.  Check if the target database (`cryptoxdog-ib-odoo-19-staging-29047277`) exists.
  4.  If not, create it: `CREATE DATABASE [target_db] OWNER [target_odoo_user];`

### 2. Execution
- You will run this script locally: `python3 scripts/fix_db_permissions.py`
- You will be prompted to enter the **Admin Password** and the **Target Odoo User** (from your config).

### 3. Verification
- After the script runs successfully, restart Odoo.
- The "permission denied" error should disappear, and Odoo should find (or create) the database.