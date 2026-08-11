#!/usr/bin/env python3
import pathlib, sys, yaml, hashlib
root = pathlib.Path(__file__).resolve().parents[1]
errors = []
for path in root.rglob('*.yaml'):
    try:
        yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:
        errors.append(f'yaml_parse_failed: {path.relative_to(root)}: {exc}')
required = [
    '00_manifest/MANIFEST.yaml',
    '00_manifest/ARTIFACT_REGISTRY.yaml',
    '00_manifest/KERNEL_REFERENCE_REGISTRY.yaml',
    '00_manifest/REGISTRATION_LAW.yaml',
    '01_strategy/l9_alignment_matrix.v1.yaml',
    '02_runtime_contracts/context_slice_hydration_law.v1.yaml',
    '02_runtime_contracts/signal_propulsion_contract.v1.yaml',
    '08_validation/REGRESSION_GUARD.md',
    '08_validation/UNKNOWN_REGISTER.yaml',
]
for rel in required:
    if not (root/rel).exists():
        errors.append(f'missing_required_file: {rel}')
manifest = yaml.safe_load((root/'00_manifest/MANIFEST.yaml').read_text(encoding='utf-8')) if (root/'00_manifest/MANIFEST.yaml').exists() else {}
manifest_paths = {f.get('path') for f in manifest.get('files', []) if isinstance(f, dict)}
for path in root.rglob('*'):
    if path.is_file():
        rel = path.relative_to(root).as_posix()
        if rel != '00_manifest/MANIFEST.yaml' and rel not in manifest_paths:
            errors.append(f'unregistered_file_in_manifest: {rel}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('l9_hardening_validation_passed')
