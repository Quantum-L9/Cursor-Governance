# QUICKSTART.md

## Purpose

Validate the L9 mobile chat session hydration strategy pack from one command.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run Validation

```bash
python run_all.py
```

## Expected Output

```text
required_file_check_passed
disallowed_marker_scan_passed
validation_passed
l9_hardening_validation_passed
yaml_parse_passed
manifest_present
polish_validation_passed
```

## Boundary

This pack validates structure, manifest registration, YAML parseability, and L9 hydration-pack boundaries. It does not simulate ChatGPT mobile runtime behavior and does not perform network calls.
