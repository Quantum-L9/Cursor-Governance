---
name: l9-python-tdd-with-uv
description: test-driven development in Python using uv as the package manager. covers the red-green-refactor cycle, vertical slicing, and uv project setup. use when starting Python TDD with uv, setting up a uv project, or running a red-green-refactor loop.
disable-model-invocation: true
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, python, tdd, uv, testing]
owner: igor_beylin
status: active
version: 1.1.1
updated: 2026-06-06
---

# Python TDD with uv

## Purpose

Write Python code test-first using `uv` for dependency and environment management. Enforce red-green-refactor vertical slices — one failing test at a time.

## Core Contract

| Phase | Rule |
|-------|------|
| RED | One failing test for next behavior |
| GREEN | Minimum code to pass |
| REFACTOR | Clean without behavior change |
| RUN | `uv run pytest` after every change |

## Authority Order

1. Explicit user module/API under test.
2. Existing `pyproject.toml`, `uv.lock`, and test layout in repo.
3. pytest conventions in repo when present.
4. This skill's TDD workflow and uv commands below.
5. `Unknown` — initialize with `uv init` only when no Python project exists.

## Setting Up the Project

1. Check if `uv` is installed: `uv --version`
2. If the project doesn't have a `pyproject.toml`, initialize:
   ```bash
   uv init
   ```
3. Add pytest as a dev dependency:
   ```bash
   uv add --dev pytest pytest-cov
   ```
4. Confirm the test runner works:
   ```bash
   uv run pytest --co
   ```

## TDD Workflow — Vertical Slicing

Work in small cycles. Never write more than one failing test at a time.

### Planning Phase

Before writing code, answer:
1. What interface changes are needed? (functions, classes, APIs)
2. Which behaviors matter most? (prioritize critical paths)
3. Can we design for testability? (inject dependencies, avoid global state)

### The Cycle

```
RED   → Write ONE failing test for the next behavior
GREEN → Write the MINIMUM code to make it pass
REFACTOR → Clean up without changing behavior
REPEAT
```

**Rules:**
- Never write implementation before a failing test exists
- Never write more than one failing test at a time
- Run `uv run pytest` after every change
- Tests must assert observable behavior, not implementation details
- Mocks should only be used at system boundaries (I/O, network, clock)

### Test File Structure

```python
# tests/test_<module>.py

class TestFeatureName:
    """Group related behaviors."""

    def test_does_expected_thing_when_given_input(self):
        result = function_under_test(input_value)
        assert result == expected

    def test_raises_when_given_invalid_input(self):
        with pytest.raises(ValueError):
            function_under_test(bad_input)
```

### Running Tests

```bash
uv run pytest                      # all tests
uv run pytest tests/test_foo.py    # single file
uv run pytest -k "test_name"       # by name pattern
uv run pytest --cov=src            # with coverage
uv run pytest -x                   # stop on first failure
```

## uv Essentials

```bash
uv add <package>           # add dependency
uv add --dev <package>     # add dev dependency
uv remove <package>        # remove dependency
uv sync                    # sync environment from lockfile
uv run <command>           # run in managed environment
uv lock                    # regenerate lockfile
```

- Always use `uv run` to execute commands — never activate venvs manually
- Commit both `pyproject.toml` and `uv.lock`

## Dev container

- Never activate a venv manually — `uv run` resolves from `uv.lock`.
- Add `uv sync` to `postCreateCommand` in `devcontainer.json` so rebuilds restore the locked environment.
- Never regenerate `uv.lock` without `uv lock`.

## Resource Map

No `references/` folder — workflow lives in this file. External inspiration:

- [mattpocock/skills — TDD skill](https://github.com/mattpocock/skills) — vertical-slice TDD philosophy
- [nizos/tdd-guard](https://github.com/nizos/tdd-guard) — automated TDD enforcement via hooks
- [s2005/uv-skill](https://github.com/s2005/uv-skill) — uv workflow patterns

## Validation

Never write implementation before a failing test exists. Never more than one failing test at a time. Tests MUST assert observable behavior, not implementation details. Always use `uv run` — never manual venv activation. Commit `pyproject.toml` and `uv.lock` together.

## Failure Handling

- `uv` not installed → install uv or ask user; do not fall back to pip without approval.
- Existing non-uv project → ask before `uv init`; may need migration plan.
- Test passes on first write → test was not RED; rewrite test to fail first.
- Odoo/runtime tests needed → this skill covers pure Python TDD; route Odoo tests to repo test rules.
