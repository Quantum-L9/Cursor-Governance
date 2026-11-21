"""CI canary (DO NOT MERGE): consumer rulepack known-bad (SDK ADR 0021, canary B3).

l9.no-semgrep-app-token-in-child-env must fire on line 9 in the central
consumer execution (semgrep:consumer:quantum-l9.cursor-governance).
"""

import os

TOKEN = os.environ.get("SEMGREP_APP_TOKEN")
