"""Consumer override attempt: inline suppression of a central rule."""

import subprocess


def run(cmd: str) -> None:
    subprocess.run(cmd, shell=True, check=True)  # nosemgrep
