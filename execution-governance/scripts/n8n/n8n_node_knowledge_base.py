#!/usr/bin/env python3
"""
n8n Node Knowledge Base Builder
Fetches and indexes comprehensive information about all n8n nodes
for AI-assisted workflow creation.
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional
from pathlib import Path

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com/repos/n8n-io/n8n"
NODES_PATH = "packages/nodes-base/nodes"

class NodeKnowledgeBase:
    """Builds and maintains a knowledge base of all n8n nodes"""
    
    def __init__(self, cache_dir: str = ".n8n_kb_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.nodes_index = {}
        
    def fetch_all_node_names(self) -> List[str]:
        """Fetch list of all node directories from GitHub"""
        url = f"{GITHUB_API_BASE}/contents/{NODES_PATH}"
        try:
            response = requests.get(url, params={"per_page": 100})
            response.raise_for_status()
            nodes = response.json()
            return sorted([node['name'] for node in nodes if node['type'] == 'dir'])
        except Exception as e:
            print(f"Error fetching node list: {e}", file=sys.stderr)
            return []
    
    def fetch_node_description(self, node_name: str) -> Optional[Dict]:
        """Fetch node description file (contains all parameters and metadata)"""
        cache_file = self.cache_dir / f"{node_name}.json"
        
        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Try to find description file
        possible_files = [
            f"{NODES_PATH}/{node_name}/{node_name}.node.ts",
            f"{NODES_PATH}/{node_name}/{node_name}.node.js",
            f"{NODES_PATH}/{node_name}/index.ts",
            f"{NODES_PATH}/{node_name}/index.js",
        ]
        
        node_info = {
            'name': node_name,
            'path': f"{NODES_PATH}/{node_name}",
            'description': None,
            'parameters': [],
            'resources': [],
            'operations': [],
            'credentials': [],
            'categories': []
        }
        
        # Try to get README or description
        readme_url = f"{GITHUB_API_BASE}/contents/{NODES_PATH}/{node_name}/README.md"
        try:
            response = requests.get(readme_url)
            if response.status_code == 200:
                node_info['readme'] = response.json().get('content', '')
        except:
            pass
        
        # Cache the result
        with open(cache_file, 'w') as f:
            json.dump(node_info, f, indent=2)
        
        return node_info
    
    def fetch_node_source(self, node_name: str) -> Optional[str]:
        """Fetch node source code to extract parameter definitions"""
        # Try TypeScript first (most nodes are TS)
        ts_file = f"{NODES_PATH}/{node_name}/{node_name}.node.ts"
        url = f"{GITHUB_API_BASE}/contents/{ts_file}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                import base64
                content = base64.b64decode(response.json()['content']).decode('utf-8')
                return content
        except:
            pass
        
        return None
    
    def extract_node_info(self, node_name: str, source_code: str) -> Dict:
        """Extract structured information from node source code"""
        info = {
            'name': node_name,
            'displayName': None,
            'description': None,
            'categories': [],
            'parameters': [],
            'resources': [],
            'operations': [],
            'credentials': [],
            'inputs': [],
            'outputs': []
        }
        
        # Extract displayName
        import re
        display_match = re.search(r"displayName:\s*['\"]([^'\"]+)['\"]", source_code)
        if display_match:
            info['displayName'] = display_match.group(1)
        
        # Extract description
        desc_match = re.search(r"description:\s*['\"]([^'\"]+)['\"]", source_code)
        if desc_match:
            info['description'] = desc_match.group(1)
        
        # Extract categories
        cat_match = re.search(r"categories:\s*\[([^\]]+)\]", source_code)
        if cat_match:
            categories = re.findall(r"['\"]([^'\"]+)['\"]", cat_match.group(1))
            info['categories'] = categories
        
        # Extract resources (if present)
        resource_match = re.search(r"displayName:\s*['\"]Resource['\"].*?options:\s*\[(.*?)\]", source_code, re.DOTALL)
        if resource_match:
            resources = re.findall(r"name:\s*['\"]([^'\"]+)['\"]", resource_match.group(1))
            info['resources'] = resources
        
        # Extract operations (if present)
        op_match = re.search(r"displayName:\s*['\"]Operation['\"].*?options:\s*\[(.*?)\]", source_code, re.DOTALL)
        if op_match:
            operations = re.findall(r"name:\s*['\"]([^'\"]+)['\"]", op_match.group(1))
            info['operations'] = operations
        
        # Extract credentials
        cred_match = re.search(r"credentials:\s*\[(.*?)\]", source_code, re.DOTALL)
        if cred_match:
            creds = re.findall(r"name:\s*['\"]([^'\"]+)['\"]", cred_match.group(1))
            info['credentials'] = creds
        
        return info
    
    def build_knowledge_base(self, node_names: Optional[List[str]] = None) -> Dict:
        """Build comprehensive knowledge base of all nodes"""
        if node_names is None:
            node_names = self.fetch_all_node_names()
        
        print(f"Building knowledge base for {len(node_names)} nodes...")
        
        kb = {
            'nodes': {},
            'by_category': {},
            'by_integration': {},
            'total_nodes': len(node_names)
        }
        
        for i, node_name in enumerate(node_names, 1):
            print(f"[{i}/{len(node_names)}] Processing {node_name}...", end='\r')
            
            # Fetch source code
            source = self.fetch_node_source(node_name)
            if source:
                info = self.extract_node_info(node_name, source)
                kb['nodes'][node_name] = info
                
                # Index by category
                for cat in info.get('categories', []):
                    if cat not in kb['by_category']:
                        kb['by_category'][cat] = []
                    kb['by_category'][cat].append(node_name)
                
                # Index by integration name (if it's an integration node)
                if info.get('displayName'):
                    kb['by_integration'][info['displayName']] = node_name
        
        print(f"\n✅ Knowledge base built: {len(kb['nodes'])} nodes indexed")
        return kb
    
    def save_knowledge_base(self, kb: Dict, filename: str = "n8n_nodes_kb.json"):
        """Save knowledge base to JSON file"""
        output_file = Path(filename)
        with open(output_file, 'w') as f:
            json.dump(kb, f, indent=2)
        print(f"✅ Knowledge base saved to {output_file}")
        return output_file
    
    def generate_markdown_summary(self, kb: Dict, filename: str = "N8N_NODES_REFERENCE.md"):
        """Generate a markdown reference document"""
        md = ["# n8n Nodes Reference", "", f"Total Nodes: {kb['total_nodes']}", ""]
        
        # By category
        md.append("## Nodes by Category\n")
        for category, nodes in sorted(kb['by_category'].items()):
            md.append(f"### {category}")
            for node in sorted(nodes):
                node_info = kb['nodes'].get(node, {})
                display_name = node_info.get('displayName', node)
                desc = node_info.get('description', '')
                md.append(f"- **{display_name}** (`{node}`) - {desc}")
            md.append("")
        
        # All nodes list
        md.append("## All Nodes\n")
        for node_name in sorted(kb['nodes'].keys()):
            node_info = kb['nodes'][node_name]
            display_name = node_info.get('displayName', node_name)
            desc = node_info.get('description', '')
            cats = ', '.join(node_info.get('categories', []))
            md.append(f"- **{display_name}** (`{node_name}`)")
            if desc:
                md.append(f"  - {desc}")
            if cats:
                md.append(f"  - Categories: {cats}")
            md.append("")
        
        output_file = Path(filename)
        with open(output_file, 'w') as f:
            f.write('\n'.join(md))
        print(f"✅ Markdown reference saved to {output_file}")
        return output_file


def main():
    """CLI interface"""
    kb_builder = NodeKnowledgeBase()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'quick':
        # Quick mode: just fetch names
        nodes = kb_builder.fetch_all_node_names()
        print(f"\nFound {len(nodes)} nodes:")
        for node in nodes:
            print(f"  - {node}")
    else:
        # Full mode: build complete knowledge base
        kb = kb_builder.build_knowledge_base()
        kb_builder.save_knowledge_base(kb)
        kb_builder.generate_markdown_summary(kb)


if __name__ == '__main__':
    main()

