import json
import sys

mode_map = {
    "architect": "architectMode",
    "think": "thinkTankMode",
    "strategy": "strategistMode"
}

import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(script_dir, "snippets.json")) as f:
    snippets = json.load(f)

mode = sys.argv[1] if len(sys.argv) > 1 else "architect"
prompt = snippets[mode_map.get(mode)]

config = { "ai.prompt": prompt["body"] }

with open(os.path.join(script_dir, "config.json"), "w") as f:
    json.dump(config, f, indent=2)

print(f"✅ Mode switched to {mode.upper()} successfully.")
