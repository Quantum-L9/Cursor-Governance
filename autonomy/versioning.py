from __future__ import annotations

import re
from dataclasses import dataclass

from autonomy.errors import CompatibilityError

_VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)$"
)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> Version:
        match = _VERSION_RE.match(value)
        if not match:
            raise CompatibilityError(f"Version must use strict MAJOR.MINOR.PATCH format: {value!r}")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def require_same_major(actual: str, expected: str, component: str) -> None:
    actual_version = Version.parse(actual)
    expected_version = Version.parse(expected)
    if actual_version.major != expected_version.major:
        raise CompatibilityError(
            f"{component} major-version mismatch: "
            f"actual={actual_version}, expected={expected_version}"
        )
    if actual_version < expected_version:
        raise CompatibilityError(
            f"{component} is older than the minimum supported version: "
            f"actual={actual_version}, minimum={expected_version}"
        )
