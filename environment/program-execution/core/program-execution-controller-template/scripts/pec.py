#!/usr/bin/env python3
from pathlib import Path

from pec.cli import main

if __name__ == "__main__":
    raise SystemExit(main(template_root=Path(__file__).resolve().parents[1]))
