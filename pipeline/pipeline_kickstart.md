---
name: pipeline_kickstart
version: "1.0.0"
description: "Start pipeline from scratch"
auto_chain: null
---

# /pipeline_kickstart — Pipeline Startup

## WHAT IT DOES

Initialize CI/CD pipeline for new project/branch:

1. Create workflow files
2. Configure checks
3. Test locally
4. Push and verify

---

## SETUP

### 1. GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest tests/
```

### 2. Pre-commit Config

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
```

### 3. Install Hooks

```bash
pip install pre-commit
pre-commit install
```

---

## VERIFY

```bash
# Test locally
ruff check . && pytest tests/

# Push and check
git push origin {branch}
gh run list --limit 1
```

---

## OUTPUT

```markdown
## 🚀 PIPELINE KICKSTART

### Created
- [ ] .github/workflows/ci.yml
- [ ] .pre-commit-config.yaml
- [ ] Hooks installed

### Verified
- [ ] Local checks pass
- [ ] Remote run triggered
- [ ] All jobs green
```

--- End Command ---
