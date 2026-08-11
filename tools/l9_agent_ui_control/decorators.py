"""Standalone stub for must_stay_async (no core.decorators monorepo dep)."""


def must_stay_async(reason: str = ""):
    """No-op decorator — documents that the callable must remain async."""

    def decorator(fn):
        return fn

    return decorator
