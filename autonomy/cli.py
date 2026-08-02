from __future__ import annotations

import argparse
import sys

from autonomy.compiler.graph_compiler import main as compile_main
from autonomy.validation.graph_linter import main as lint_main


def main() -> int:
    parser = argparse.ArgumentParser(description="L9 autonomy control-plane CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "compile",
        help="Compile campaign, deployment, and action contracts.",
    )
    subparsers.add_parser(
        "lint",
        help="Validate a compiled graph against enforcement policies.",
    )
    args, remaining = parser.parse_known_args()
    original_argv = sys.argv
    try:
        sys.argv = [original_argv[0], *remaining]
        if args.command == "compile":
            return compile_main()
        if args.command == "lint":
            return lint_main()
    finally:
        sys.argv = original_argv
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
