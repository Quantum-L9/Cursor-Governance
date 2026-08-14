from __future__ import annotations

from collections.abc import Iterable

_PERMISSION_PROFILES = {
    "repo-local-bounded": {
        "deny": (
            "push",
            "pull_request",
            "merge",
            "publish_or_release",
            "deploy_or_migrate",
            "force_push",
            "destructive_change",
            "external_message",
        ),
    },
    "read-only": {
        "deny": (
            "local_write",
            "commit",
            "push",
            "pull_request",
            "merge",
            "publish_or_release",
            "deploy_or_migrate",
            "destructive_change",
            "external_message",
        ),
    },
}


def _capabilities(value: Iterable[str]) -> set[str]:
    output: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("requested capabilities must be non-empty strings")
        output.add(item)
    if not output:
        raise ValueError("requested capabilities must not be empty")
    return output


def resolve_permission_profile(
    profile_ref: str,
    requested_capabilities: Iterable[str],
) -> dict[str, object]:
    if not isinstance(profile_ref, str) or not profile_ref.strip():
        raise ValueError("permission profile reference must be a non-empty string")
    definition = _PERMISSION_PROFILES.get(profile_ref)
    if definition is None:
        raise ValueError(f"unknown permission profile: {profile_ref}")
    requested = _capabilities(requested_capabilities)
    denied = set(definition["deny"])
    allowed = requested - denied
    return {
        "schema": "l9.peer-execution.permission-profile.v1",
        "profile_ref": profile_ref,
        "requested_actions": sorted(requested),
        "allowed_actions": sorted(allowed),
        "denied_actions": sorted(denied),
    }
