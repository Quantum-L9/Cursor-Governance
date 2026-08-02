from __future__ import annotations


class AutonomyError(Exception):
    """Base class for autonomy control-plane failures."""


class ContractError(AutonomyError):
    """Raised when a machine-readable contract is malformed."""


class GraphCompilationError(AutonomyError):
    """Raised when an action graph cannot be compiled safely."""


class GraphValidationError(AutonomyError):
    """Raised when a compiled action graph violates invariants."""


class PolicyViolation(AutonomyError):
    """Raised when an action violates a declared governance policy."""


class CompatibilityError(AutonomyError):
    """Raised when contract or adapter versions are incompatible."""
