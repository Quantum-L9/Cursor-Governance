"""Non-routable target-deployment factory marker.

The generator remains directly invokable through its existing factory tooling. It is
intentionally not an execution adapter and must never be loaded by provider_loader.
"""

NON_ROUTABLE_FACTORY = True
