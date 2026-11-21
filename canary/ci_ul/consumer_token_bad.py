"""CI canary (DO NOT MERGE): consumer rulepack known-bad (SDK ADR 0021, canary B3).

l9.no-semgrep-app-token-in-child-env must fire here in the central consumer
execution (semgrep:consumer:quantum-l9.cursor-governance) and locally.
"""

import os

TOKEN = os.environ.get("SEMGREP_APP_TOKEN")
