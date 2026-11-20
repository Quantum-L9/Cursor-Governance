"""Known-bad: shell=True with a variable command (consumer .semgrepignore override attempt)."""

import subprocess


def run(cmd: str) -> None:
    subprocess.run(cmd, shell=True, check=True)
