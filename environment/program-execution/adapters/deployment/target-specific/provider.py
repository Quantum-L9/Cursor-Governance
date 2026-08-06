from __future__ import annotations

from adapters.common.base import BaseExecutionAdapter


class TargetDeploymentFactoryAdapter(BaseExecutionAdapter):
    adapter_id = "target-deployment-factory"
    capabilities = ("generate_adapter", "validate_adapter")
    cancellation = "unsupported"

    def _probe_status(self, context):
        return "PASS", None, [{"type": "factory_integrity", "routable": False}]

    def _dispatch_record(self, record):
        raise ValueError("target-deployment-factory is non-routable; invoke its generator directly")
