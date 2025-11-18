#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-N8N-007"
component_name: "n8n API Helper"
layer: "intelligence"
domain: "n8n_automation"
type: "utility"
status: "active"
created: "2025-01-27T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "medium"
compliance_required: true
audit_trail: false
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["requests"]
integrates_with: ["INT-N8N-001"]
api_endpoints: ["n8n REST API"]
data_sources: ["n8n instance"]
outputs: ["workflow_json", "execution_data"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Python utility functions for n8n workflow management via REST API"
summary: "Helper functions for creating, updating, and managing n8n workflows programmatically"
business_value: "Enables programmatic n8n workflow management and automation"
success_metrics: ["api_call_success_rate >= 0.95"]

# === TAGS & CLASSIFICATION ===
tags: ["n8n", "api", "utility", "python"]
keywords: ["n8n", "api", "helper", "workflow", "management"]
related_components: ["INT-N8N-001"]
startup_required: false
mode_type: "utility"
---

n8n API Helper - Direct HTTP access to n8n cloud instance
No MCP required - just works with requests library
"""

import requests
import json
from typing import Dict, List, Optional, Any

class N8nAPI:
    """Simple n8n API client for direct HTTP access"""

    def __init__(self, base_url: str = "https://ibeylin.app.n8n.cloud", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGRkNDc4OC1hYTU4LTRhZDctYTljYS05YmQxOTY4MDUzYTEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYyNzM2NDI1fQ.NiaifCzXT81lgh71pGvuzaVEvICaRyJb8vvfwCT_iL4"
        self.headers = {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make authenticated request to n8n API"""
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        result = response.json()
        # n8n API sometimes returns data wrapped in 'data' key
        if isinstance(result, dict) and 'data' in result:
            return result['data']
        return result

    # ==================== WORKFLOWS ====================

    def list_workflows(self) -> List[Dict]:
        """Get all workflows"""
        return self._request("GET", "workflows")

    def get_workflow(self, workflow_id: str) -> Dict:
        """Get specific workflow by ID"""
        return self._request("GET", f"workflows/{workflow_id}")

    def create_workflow(self, workflow_data: Dict) -> Dict:
        """Create new workflow"""
        return self._request("POST", "workflows", json=workflow_data)

    def update_workflow(self, workflow_id: str, workflow_data: Dict) -> Dict:
        """Update existing workflow"""
        return self._request("PATCH", f"workflows/{workflow_id}", json=workflow_data)

    def activate_workflow(self, workflow_id: str) -> Dict:
        """Activate a workflow"""
        return self._request("PATCH", f"workflows/{workflow_id}", json={"active": True})

    def deactivate_workflow(self, workflow_id: str) -> Dict:
        """Deactivate a workflow"""
        return self._request("PATCH", f"workflows/{workflow_id}", json={"active": False})

    def delete_workflow(self, workflow_id: str) -> Dict:
        """Delete a workflow"""
        return self._request("DELETE", f"workflows/{workflow_id}")

    # ==================== EXECUTIONS ====================

    def execute_workflow(self, workflow_id: str, data: Optional[Dict] = None) -> Dict:
        """Execute a workflow manually"""
        payload = {"workflowId": workflow_id}
        if data:
            payload["data"] = data
        return self._request("POST", f"workflows/{workflow_id}/execute", json=payload)

    def list_executions(self, workflow_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get workflow executions"""
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        return self._request("GET", "executions", params=params)

    def get_execution(self, execution_id: str) -> Dict:
        """Get specific execution details"""
        return self._request("GET", f"executions/{execution_id}")

    def delete_execution(self, execution_id: str) -> Dict:
        """Delete an execution"""
        return self._request("DELETE", f"executions/{execution_id}")

    # ==================== CREDENTIALS ====================

    def list_credentials(self) -> List[Dict]:
        """Get all credentials"""
        return self._request("GET", "credentials")

    def get_credential(self, credential_id: str) -> Dict:
        """Get specific credential"""
        return self._request("GET", f"credentials/{credential_id}")

    # ==================== HELPER METHODS ====================

    def find_workflow_by_name(self, name: str) -> Optional[Dict]:
        """Find workflow by name (case-insensitive)"""
        workflows = self.list_workflows()
        for wf in workflows:
            if wf.get("name", "").lower() == name.lower():
                return wf
        return None

    def trigger_webhook(self, webhook_path: str, data: Dict) -> Dict:
        """Trigger a webhook workflow"""
        url = f"{self.base_url}/{webhook_path.lstrip('/')}"
        response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return response.json()

    def upload_workflow_from_file(self, file_path: str) -> Dict:
        """Upload workflow from JSON file"""
        with open(file_path, 'r') as f:
            workflow_data = json.load(f)
        return self.create_workflow(workflow_data)

    def download_workflow_to_file(self, workflow_id: str, file_path: str):
        """Download workflow to JSON file"""
        workflow = self.get_workflow(workflow_id)
        with open(file_path, 'w') as f:
            json.dump(workflow, f, indent=2)
        print(f"Workflow saved to {file_path}")

    def health_check(self) -> bool:
        """Check if API connection is working"""
        try:
            self.list_workflows()
            return True
        except Exception as e:
            print(f"Health check failed: {e}")
            return False


# ==================== QUICK USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Initialize API client
    n8n = N8nAPI()

    # Test connection
    print("Testing n8n API connection...")
    if n8n.health_check():
        print("✅ Connected to n8n successfully!")

        # List all workflows
        print("\n📋 Your workflows:")
        workflows = n8n.list_workflows()
        for wf in workflows:
            status = "🟢 Active" if wf.get("active") else "⚪ Inactive"
            print(f"  {status} - {wf['name']} (ID: {wf['id']})")

        # Show recent executions
        print("\n⚡ Recent executions:")
        executions = n8n.list_executions(limit=5)
        for exe in executions:
            status = "✅" if exe.get("finished") else "⏳"
            workflow_name = exe.get("workflowData", {}).get("name", "Unknown")
            print(f"  {status} {workflow_name} - {exe.get('startedAt', 'N/A')}")
    else:
        print("❌ Failed to connect to n8n")


# ==================== USAGE IN CURSOR ====================
"""
You can now use this in Cursor directly:

from GlobalCommands.n8n_startup.n8n_api_helper import N8nAPI

# Initialize
n8n = N8nAPI()

# List workflows
workflows = n8n.list_workflows()

# Execute a workflow
result = n8n.execute_workflow("workflow_id_here", {"input": "data"})

# Find and execute by name
wf = n8n.find_workflow_by_name("BCP Pipeline Prod v6")
if wf:
    result = n8n.execute_workflow(wf['id'], {"supplier_name": "Acme Corp"})

# Upload workflow from file
n8n.upload_workflow_from_file("path/to/workflow.json")
"""
