from pathlib import Path

from adapters.common.imports import load_module

_module = load_module(Path(__file__).with_name("driver.py"), "pes_generic_shell_driver")
GenericShellVerifier = _module.GenericShellVerifier
