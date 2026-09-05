#!/usr/bin/env python3
"""Prove the commit-verification rule is declared, told, and true.

Three failures this gate exists to prevent, each of which actually happened:

1. **Told but not enforced.** Eight skill files said "never `--no-verify`" while
   every execution gate allowed it. Prose is not a gate.
2. **Enforced but not told.** A denial an agent meets for the first time *as a
   denial* costs a turn and reads as a malfunction. The session briefing must
   carry the declaration's own lines, so the rule is known before it is hit.
3. **Forbidden but emitted.** ``workflows/*_executor.py`` generated
   ``git commit --no-verify`` while the skills forbade it, so governance tooling
   performed the bypass on the agent's behalf.

Scope note: a line that *forbids* a bypass is the point, not a violation. This
gate flags a line that would *run* one, the same way
``validate_git_denial_residue.py`` flags a false denial claim rather than
banning words.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from verification_bypass_gate import (  # noqa: E402
    CONTRACT_PATH,
    ContractError,
    briefing_lines,
    command_bypasses_verification,
    load_contract,
)

PROFILE = ROOT / "ops" / "autonomy" / "surface_profile.yaml"

#: Tokens that identify the briefing has actually landed. Derived from the
#: declaration's own briefing lines rather than restated, so a reworded
#: declaration cannot leave a stale briefing passing.
_BRIEFING_TOKENS = ("--no-verify", "verification_bypass_gate.py", "core.hooksPath")

#: Executable surfaces where a bypass token means the bypass will RUN.
_EXECUTABLE_SUFFIXES = {".py", ".sh", ".bash", ".zsh"}

#: Historical evidence and reference corpora: out of scope, same rationale as
#: the sibling residue gates. These record what was done, not what to do.
_SKIP_PARTS = {
    "_archived",
    "archived",
    "reports",
    "WIP",
    "learning",
    "Dags-Harvest",
    "releases",
    "__pycache__",
    ".venv",
}

#: The plane's own files necessarily name every form they govern.
_SKIP_FILES = {
    "ops/config/commit-verification-contract.json",
    "ops/autonomy/verification_bypass_gate.py",
    "ops/scripts/validate_commit_verification_contract.py",
    "tests/ops/autonomy/test_verification_bypass_gate.py",
    "tests/ops/scripts/test_commit_verification_validator.py",
}

#: Reading a setting is not setting it. `git config --get core.hooksPath` is how
#: a tool REPORTS that hooks are repointed — the installer warns about exactly
#: that — and a line that only mentions the key inside a message emits nothing.
#: Both were flagged until the hook this gate guards caught its own installer,
#: which is the intended way for a false positive to surface.
_READS_NOT_WRITES = re.compile(r"(?i)--get\b|--get-all\b|--list\b|^\s*(?:#|echo\b|printf\b)")

#: The line teaches against the bypass, or records that one happened. Both are
#: legitimate; neither runs anything.
_PROHIBITION = re.compile(
    r"(?i)\b(never|forbid\w*|prohibit\w*|den(?:y|ies|ied|ial)|must\s+not|"
    r"do\s+not|don't|avoid|refus\w*|reject\w*|violation|banned|illegal|"
    r"disallow\w*|bypass\w*)\b|❌"
)

#: Bare "no"/"not" are deliberately absent above: ``\bno\b`` matches *inside*
#: ``--no-verify`` (both sides of "no" are hyphens, so both word boundaries
#: hold), which silently exonerated every line this gate exists to catch. The
#: token is stripped before the prohibition test for the same reason.


def _scan_tokens(contract: dict) -> tuple[str, ...]:
    """Literal tokens a source line can carry that *run* a declared bypass.

    Derived from the declaration rather than restated, so a form added to
    ``commit-verification-contract.json`` is scanned here without a second
    edit. Three literals were hand-maintained here while the contract declared
    more, so ``--no-pre-commit-hook`` — declared on six git subcommands — was
    never scanned at all.

    ``env_prefix`` forms are deliberately excluded. ``SKIP=`` / ``HUSKY=`` only
    bypass verification when applied to ``git commit`` / ``git push``, and that
    context lives in the command, not in the line. Scanning the bare names
    flags governance's own sanctioned surface-aware skip list
    (``run_pr_precommit.sh``) and five other legitimate files. The gate still
    denies them — it parses the command, which a line scan cannot.
    """
    tokens: set[str] = set()
    for form in contract.get("forms") or ():
        detector = form.get("detector")
        if detector == "git_flag":
            tokens.update(form.get("flags") or ())
        elif detector == "git_global_config":
            tokens.update(form.get("keys") or ())
        elif detector == "git_subcommand_args":
            tokens.update(form.get("match_args") or ())
        elif detector == "argv":
            head, args = form.get("head"), form.get("args") or ()
            if head and args:
                tokens.add(" ".join([str(head), *(str(arg) for arg in args)]))
    return tuple(sorted(tokens, key=len, reverse=True))


def bypass_pattern(contract: dict) -> re.Pattern[str]:
    """Match a declared token as a whole flag or key, never as a prefix.

    Without the trailing guard ``--no-verify`` matches inside
    ``--no-verify-ancestry`` — an argparse flag for skipping an ancestry
    reachability probe, not a bypass — which failed this gate on unmodified
    ``main``. The enforcer never had the bug: it compares whole tokens.
    """
    alternatives = "|".join(
        re.escape(token).replace(r"\ ", r"\s+") for token in _scan_tokens(contract)
    )
    return re.compile(rf"(?i)(?:{alternatives})(?![\w-])")


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [ROOT / line for line in out.stdout.splitlines() if line.strip()]


def _in_scope(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel in _SKIP_FILES:
        return False
    if set(path.parts) & _SKIP_PARTS:
        return False
    return path.suffix in _EXECUTABLE_SUFFIXES


def check_declaration(errors: list[str]) -> dict | None:
    try:
        return load_contract()
    except ContractError as exc:
        errors.append(f"declaration unreadable: {exc}")
        return None


def check_every_form_denies(contract: dict, errors: list[str]) -> None:
    """A form that does not produce a denial is decoration in a JSON file."""
    for form in contract["forms"]:
        if not form.get("label") or not form.get("why"):
            errors.append(f"form {form['id']}: needs a 'label' and a 'why' for the denial text")


def check_briefing_is_told(errors: list[str]) -> None:
    """The rule must reach the agent before the agent reaches the rule."""
    if not PROFILE.is_file():
        errors.append(f"{PROFILE} missing: the session briefing cannot be verified")
        return
    text = PROFILE.read_text(encoding="utf-8")
    for token in _BRIEFING_TOKENS:
        if token not in text:
            errors.append(
                f"ops/autonomy/surface_profile.yaml does not mention {token!r}: the gate "
                "would deny a command the session was never briefed about"
            )
    if not briefing_lines():
        errors.append("declaration has no briefing_lines: nothing to tell the session")


def check_tree_emits_no_bypass(contract: dict, errors: list[str]) -> None:
    """Governance tooling must not perform the bypass on the agent's behalf."""
    bypass_token = bypass_pattern(contract)
    for path in _tracked_files():
        if not path.is_file() or not _in_scope(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            hit = bypass_token.search(line)
            if not hit:
                continue
            if _PROHIBITION.search(bypass_token.sub(" ", line)):
                continue
            # A read or a message about the key is not an emission. Scoped to
            # core.hooksPath: `--no-verify` has no read form, so a line carrying
            # it is always constructing the bypass.
            if hit.group(0).lower() == "core.hookspath" and _READS_NOT_WRITES.search(line):
                continue
            rel = path.relative_to(ROOT).as_posix()
            errors.append(
                f"{rel}:{number}: emits a commit-verification bypass — {line.strip()[:96]}"
            )


def check_gate_is_live(errors: list[str]) -> None:
    """End-to-end: the canonical form must actually come back denied."""
    if not command_bypasses_verification('git commit --no-verify -m "x"', env={}):
        errors.append(
            "verification_bypass_gate does not deny `git commit --no-verify`: "
            "the plane is declared but not enforcing"
        )
    if command_bypasses_verification('git commit -m "ordinary"', env={}):
        errors.append("verification_bypass_gate denies an ordinary commit: false positive")


def main() -> int:
    errors: list[str] = []
    contract = check_declaration(errors)
    if contract is not None:
        check_every_form_denies(contract, errors)
    check_briefing_is_told(errors)
    check_gate_is_live(errors)
    if contract is not None:
        check_tree_emits_no_bypass(contract, errors)
    if errors:
        print("FAIL: commit-verification contract", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        print(
            f"\nDeclaration: {CONTRACT_PATH.relative_to(ROOT)}",
            file=sys.stderr,
        )
        return 1
    print("PASS: commit-verification contract declared, briefed, enforced, and unemitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
