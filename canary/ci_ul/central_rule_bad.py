"""Known-bad: shell=True with a variable command (central rule witness)."""

import subprocess


def run(cmd: str) -> None:
    subprocess.run(cmd, shell=True, check=True)
