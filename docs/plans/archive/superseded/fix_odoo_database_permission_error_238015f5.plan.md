---
name: Fix Odoo Database Permission Error
overview: The error indicates a permissions issue (Authorization), not an incorrect password (Authentication). The database user connects successfully but lacks privileges to check if the database exists. This causes Odoo to skip auto-creation, which breaks the setup if the database doesn't already exist.
todos: []
isProject: false
---

### Diagnosis
- **Not "Wrong Password"**: If credentials were wrong, you would see `FATAL: password authentication failed`.
- **The Issue**: The user logged in successfully but lacks permission to read the system table `pg_database`.
- **Consequence**: Odoo skips creating the database. If this is a new setup, the database is missing, hence "it's not working."

### Plan to Fix

1. **Option A: If you have Admin access to the Database (192.168.1.1)**
   - Grant the required permission to the database user.
   - Run SQL: `GRANT SELECT ON pg_database TO [your_db_user];`
   - OR, create the database manually using a superuser account.

2. **Option B: If you are using a Managed Database (Cloud/Shared)**
   - You likely cannot grant this permission.
   - **Fix**: Manually create the empty database `cryptoxdog-ib-odoo-19-staging-29047277` using your hosting provider's dashboard or admin tool (pgAdmin/psql).
   - Once the database exists, Odoo will connect to it even without the `pg_database` permission.

3. **Verify Configuration**
   - Confirm the `db_name` in your `odoo.conf` or environment variables matches the manually created database exactly.

### Next Steps
- Please confirm if you can manually create the database on the server `192.168.1.1`.
- Once created, restart the Odoo service.