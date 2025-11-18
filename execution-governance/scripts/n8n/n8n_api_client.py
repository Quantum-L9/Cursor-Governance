#!/usr/bin/env python3
"""
n8n REST API Client
Interacts with n8n instance using REST API endpoints
"""

import json
import sys
import os
import base64
from typing import Dict, List, Optional, Any
import requests
from urllib.parse import urljoin

# Load credentials from CSV or environment
def load_from_csv():
    """Load N8N credentials from CSV file"""
    # Try multiple possible paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(script_dir, 'env.variables.n8n.ssot.csv'),
        'env.variables.n8n.ssot.csv',
        os.path.join(os.getcwd(), 'env.variables.n8n.ssot.csv'),
    ]
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if csv_path:
        import csv
        try:
            # Read with utf-8-sig to handle BOM
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = row.get('Key', '').strip()
                    value = row.get('Value', '').strip()
                    if key == 'N8N_BASE_URL' and value:
                        os.environ['N8N_BASE_URL'] = value
                    elif key == 'N8N_API_KEY' and value:
                        os.environ['N8N_API_KEY'] = value
        except Exception as e:
            print(f"Warning: Could not load from CSV: {e}", file=sys.stderr)

# Try to load from CSV first
load_from_csv()

N8N_BASE_URL = os.getenv("N8N_BASE_URL", "https://ibeylin.app.n8n.cloud")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# Fallback: if no API key found, try reading directly from CSV
if not N8N_API_KEY:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(script_dir, 'env.variables.n8n.ssot.csv'),
        'env.variables.n8n.ssot.csv',
        os.path.join(os.getcwd(), 'env.variables.n8n.ssot.csv'),
    ]
    for csv_path in possible_paths:
        if os.path.exists(csv_path):
            import csv
            try:
                # Read with utf-8-sig to handle BOM
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Key', '').strip() == 'N8N_API_KEY':
                            N8N_API_KEY = row.get('Value', '').strip()
                            if N8N_API_KEY:
                                break
                if N8N_API_KEY:
                    break
            except Exception:
                continue


class N8nAPIClient:
    """Client for interacting with n8n REST API"""
    
    def __init__(self, base_url: str = N8N_BASE_URL, api_key: str = N8N_API_KEY):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # Note: n8n Cloud accepts JWT tokens with "public-api" audience for REST API
        # This is valid for API access
        
        # Try different auth methods
        # Method 1: X-N8N-API-KEY header
        self.session.headers.update({
            'X-N8N-API-KEY': api_key,
            'Content-Type': 'application/json'
        })
        
        # Also try Authorization Bearer as fallback
        self.bearer_auth = {'Authorization': f'Bearer {api_key}'}
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with error handling"""
        url = urljoin(self.base_url, endpoint)
        
        # Try multiple auth methods
        auth_methods = [
            {'X-N8N-API-KEY': self.api_key},
            {'Authorization': f'Bearer {self.api_key}'},
            {'X-N8N-API-KEY': self.api_key, 'Authorization': f'Bearer {self.api_key}'}
        ]
        
        last_error = None
        for auth_headers in auth_methods:
            try:
                headers = kwargs.get('headers', {}).copy()
                headers.update(auth_headers)
                kwargs['headers'] = headers
                
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        return {'raw': response.text, 'status': 200}
                elif response.status_code == 401:
                    last_error = {
                        'error': f'HTTP 401 Unauthorized',
                        'message': response.text[:500],
                        'auth_method_tried': list(auth_headers.keys())
                    }
                    continue
                else:
                    return {
                        'error': f'HTTP {response.status_code}',
                        'message': response.text[:500]
                    }
            except Exception as e:
                last_error = {'error': str(e)}
                continue
        
        # If all auth methods failed, return last error
        return last_error or {'error': 'All authentication methods failed'}
    
    def list_workflows(self) -> List[Dict]:
        """List all workflows"""
        result = self._request('GET', '/api/v1/workflows')
        if 'data' in result:
            return result['data']
        return result
    
    def get_workflow(self, workflow_id: str) -> Dict:
        """Get workflow by ID"""
        return self._request('GET', f'/api/v1/workflows/{workflow_id}')
    
    def create_workflow(self, workflow_data: Dict) -> Dict:
        """Create a new workflow"""
        return self._request('POST', '/api/v1/workflows', json=workflow_data)
    
    def update_workflow(self, workflow_id: str, workflow_data: Dict) -> Dict:
        """Update an existing workflow"""
        return self._request('PUT', f'/api/v1/workflows/{workflow_id}', json=workflow_data)
    
    def delete_workflow(self, workflow_id: str) -> Dict:
        """Delete a workflow"""
        return self._request('DELETE', f'/api/v1/workflows/{workflow_id}')
    
    def execute_workflow(self, workflow_id: str, input_data: Optional[Dict] = None) -> Dict:
        """Execute a workflow"""
        endpoint = f'/api/v1/workflows/{workflow_id}/execute'
        if input_data:
            return self._request('POST', endpoint, json=input_data)
        return self._request('POST', endpoint)
    
    def list_executions(self, workflow_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """List workflow executions"""
        endpoint = '/api/v1/executions'
        params = {'limit': limit}
        if workflow_id:
            params['workflowId'] = workflow_id
        result = self._request('GET', endpoint, params=params)
        if 'data' in result:
            return result['data']
        return result
    
    def get_execution(self, execution_id: str) -> Dict:
        """Get execution details"""
        return self._request('GET', f'/api/v1/executions/{execution_id}')
    
    def retry_execution(self, execution_id: str) -> Dict:
        """Retry a failed execution"""
        return self._request('POST', f'/api/v1/executions/{execution_id}/retry')
    
    def list_credentials(self) -> List[Dict]:
        """List all credentials"""
        result = self._request('GET', '/api/v1/credentials')
        if 'data' in result:
            return result['data']
        return result
    
    def get_credential(self, credential_id: str) -> Dict:
        """Get credential by ID"""
        return self._request('GET', f'/api/v1/credentials/{credential_id}')
    
    def test_connection(self) -> Dict:
        """Test API connection"""
        return self._request('GET', '/api/v1/workflows?limit=1')


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: n8n_api_client.py <command> [args...]")
        print("\nCommands:")
        print("  test              - Test API connection")
        print("  list-workflows    - List all workflows")
        print("  get-workflow <id> - Get workflow details")
        print("  list-executions   - List recent executions")
        print("  list-credentials - List all credentials")
        return
    
    client = N8nAPIClient()
    command = sys.argv[1]
    
    if command == 'test':
        result = client.test_connection()
        print(json.dumps(result, indent=2))
    
    elif command == 'list-workflows':
        workflows = client.list_workflows()
        print(json.dumps(workflows, indent=2))
    
    elif command == 'get-workflow' and len(sys.argv) > 2:
        workflow_id = sys.argv[2]
        workflow = client.get_workflow(workflow_id)
        print(json.dumps(workflow, indent=2))
    
    elif command == 'list-executions':
        executions = client.list_executions()
        print(json.dumps(executions, indent=2))
    
    elif command == 'list-credentials':
        credentials = client.list_credentials()
        print(json.dumps(credentials, indent=2))
    
    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()

