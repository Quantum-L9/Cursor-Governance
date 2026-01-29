# scripts/test_imports.py
import importlib
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILED = []

def try_import(name):
    try:
        importlib.import_module(name)
    except Exception as e:
        FAILED.append((name, repr(e)))

def main():
    for module in pkgutil.walk_packages([str(ROOT)]):
        name = module.name
        if name.startswith(("tests.", "venv.", ".venv.", "__pycache__")):
            continue
        try_import(name)

    if FAILED:
        print("\n❌ Broken imports detected:\n")
        for name, err in FAILED:
            print(f"{name}: {err}")
        sys.exit(1)

    print("✅ All imports OK")

if __name__ == "__main__":
    main()
