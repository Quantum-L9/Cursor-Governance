#!/usr/bin/env bash
# Parse pre-commit's per-hook markers out of a captured run log.
# shellcheck shell=bash
#
# pre-commit 4.5.1 prints, per hook (pre_commit/commands/run.py _run_single_hook):
#   - hook id: <id>
#   - duration: <s>s
#   - exit code: <n>                    only when the hook itself failed
#   - files were modified by this hook   whenever the tracked tree changed in
#                                        that hook's window, whoever wrote it
#
# The distinction is the whole point: an exit code is a validator verdict, a
# modified tree is dirtiness that may have come from anywhere.

# Hook ids that returned non-zero, one "<id> <code>" pair per line.
precommit_failed_hooks() {
  awk '
    /^- hook id: /   { id = substr($0, 12); next }
    /^- exit code: / { if (id != "") print id, substr($0, 14) }
  ' "$1"
}

# Hook ids pre-commit blamed for a modified tree — a window, not an author.
precommit_blamed_hooks() {
  awk '
    /^- hook id: /                        { id = substr($0, 12); next }
    /^- files were modified by this hook/ { if (id != "") print id }
  ' "$1" | sort -u
}
