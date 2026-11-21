"""CI canary (DO NOT MERGE): memory-boundary known-bad (SDK ADR 0021, canary B3).

In the central consumer execution:
- l9.memory-boundary-no-network-or-provider-transport fires on line 10;
- l9.memory-boundary-spawn-only-through-the-binding and
  l9.memory-boundary-no-shell-string-spawn fire on line 13.
No shell=True, so no central (SDK) rule is meant to fire here.
"""

import socket
import subprocess

subprocess.run("ls", check=False)
HOST = socket.gethostname
