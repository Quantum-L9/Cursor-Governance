#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "OPS-TPE-001"
component_name: "Tool Pattern Extractor"
layer: "operations"
domain: "learning"
type: "extractor"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3", "json", "re", "pathlib", "hashlib"]
integrates_with: ["OPS-AGG-001", "OPS-LEA-001", "INT-TSE-001"]
data_sources: ["ops/logs/chat_exports", "ops/logs/memory_index.json"]
outputs: ["ops/logs/tool_patterns.json"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Extract tool call sequences from chat history and build pattern database"
summary: "Analyzes conversations to identify successful tool sequences for different request types"
business_value: "Enables intelligent tool selection based on historical success patterns"
success_metrics: ["patterns_extracted >= 100", "success_rate_calculated", "tool_patterns.json_generated"]
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import hashlib

# Import memory aggregator to reuse conversation extraction
import sys
sys.path.insert(0, str(Path(__file__).parent))
from memory_aggregator import MemoryAggregator, get_global_commands_path

GLOBAL_COMMANDS = get_global_commands_path()
CHAT_EXPORTS_DIR = GLOBAL_COMMANDS / "ops/logs/chat_exports"
TOOL_PATTERNS_FILE = GLOBAL_COMMANDS / "ops/logs/tool_patterns.json"
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"

# Known tool names (from Cursor AI assistant)
KNOWN_TOOLS = [
    "read_file", "write", "search_replace", "grep", "codebase_search",
    "list_dir", "glob_file_search", "run_terminal_cmd", "read_lints",
    "delete_file", "todo_write", "update_memory", "web_search",
    "mcp_firecrawl_firecrawl_scrape", "mcp_firecrawl_firecrawl_search",
    "mcp_GitHub_get_file_contents", "mcp_postgres_query"
]

class ToolPatternExtractor:
    """Extract tool call patterns from chat conversations"""
    
    def __init__(self):
        self.tool_patterns = defaultdict(lambda: defaultdict(lambda: {
            "tools": [],
            "success_count": 0,
            "failure_count": 0,
            "total_corrections": 0,
            "count": 0,
            "examples": []
        }))
        self.request_examples = defaultdict(list)
        
    def extract_all_patterns(self):
        """Extract tool patterns from all chat exports"""
        print("🔍 Extracting tool patterns from chat history...")
        
        # Load existing patterns if available
        if TOOL_PATTERNS_FILE.exists():
            try:
                with open(TOOL_PATTERNS_FILE, 'r') as f:
                    existing = json.load(f)
                    self.tool_patterns = defaultdict(lambda: defaultdict(dict), existing.get("request_types", {}))
            except Exception as e:
                print(f"⚠️  Error loading existing patterns: {e}")
        
        # Use memory aggregator to get conversations
        aggregator = MemoryAggregator()
        
        # Process all exports
        if CHAT_EXPORTS_DIR.exists():
            export_dirs = sorted([d for d in CHAT_EXPORTS_DIR.iterdir() if d.is_dir()])
            print(f"📂 Found {len(export_dirs)} chat export directories")
            
            for export_dir in export_dirs:
                self._process_export(export_dir)
        
        # Calculate success rates
        self._calculate_success_rates()
        
        # Save patterns
        self._save_patterns()
        
        print(f"✅ Tool pattern extraction complete!")
        print(f"   Request types: {len(self.tool_patterns)}")
        total_sequences = sum(len(seqs) for seqs in self.tool_patterns.values())
        print(f"   Tool sequences: {total_sequences}")
    
    def _process_export(self, export_dir: Path):
        """Process a single export directory"""
        # Try LevelDB format first
        chat_data_dir = export_dir / "chat_data"
        if chat_data_dir.exists():
            conversations = self._extract_leveldb_conversations(chat_data_dir)
            if conversations:
                for conv in conversations:
                    self._extract_tool_patterns(conv)
                return
        
        # Fallback to SQLite format
        workspace_storage = export_dir / "User/workspaceStorage"
        if workspace_storage.exists():
            workspaces = [d for d in workspace_storage.iterdir() if d.is_dir()]
            for workspace in workspaces:
                state_db = workspace / "state.vscdb"
                if state_db.exists():
                    conversations = self._extract_sqlite_conversations(state_db)
                    for conv in conversations:
                        self._extract_tool_patterns(conv)
    
    def _extract_leveldb_conversations(self, chat_data_dir: Path) -> List[Dict]:
        """Extract conversations from LevelDB (reuse memory aggregator logic)"""
        conversations = []
        live_db_path = Path.home() / "Library/Application Support/Cursor/Local Storage/leveldb"
        
        if not live_db_path.exists():
            return conversations
        
        try:
            import plyvel
            db = plyvel.DB(str(live_db_path), create_if_missing=False)
            
            for key, value in db:
                try:
                    key_str = key.decode('utf-8', errors='ignore')
                    value_str = value.decode('utf-8', errors='ignore')
                    
                    if any(pattern in key_str.lower() for pattern in ['composer', 'chat', 'conversation']):
                        try:
                            data = json.loads(value_str)
                            if isinstance(data, dict):
                                conversations.append(data)
                            elif isinstance(data, list):
                                conversations.extend([item for item in data if isinstance(item, dict)])
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    continue
            
            db.close()
        except Exception as e:
            print(f"    ⚠️  LevelDB error: {e}")
        
        return conversations
    
    def _extract_sqlite_conversations(self, state_db: Path) -> List[Dict]:
        """Extract conversations from SQLite database"""
        conversations = []
        try:
            import sqlite3
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    composer_data = json.loads(result[0])
                    if 'allComposers' in composer_data:
                        conversations.extend(composer_data['allComposers'])
                except json.JSONDecodeError:
                    pass
            
            conn.close()
        except Exception as e:
            print(f"    ⚠️  SQLite error: {e}")
        
        return conversations
    
    def _extract_tool_patterns(self, conversation: Dict[str, Any]):
        """Extract tool call patterns from a single conversation"""
        if not isinstance(conversation, dict):
            return
        
        # Extract messages from conversation
        messages = self._extract_messages(conversation)
        if not messages:
            return
        
        # Find user request (first user message)
        user_request = None
        for msg in messages:
            if msg.get("role") == "user" or "user" in str(msg.get("role", "")).lower():
                user_request = self._extract_text(msg)
                break
        
        if not user_request:
            return
        
        # Classify request type
        request_type = self._classify_request(user_request)
        
        # Extract tool calls from assistant messages
        tool_sequence = []
        for msg in messages:
            if msg.get("role") == "assistant" or "assistant" in str(msg.get("role", "")).lower():
                tools = self._extract_tool_calls(msg)
                if tools:
                    tool_sequence.extend(tools)
        
        if not tool_sequence:
            return
        
        # Determine outcome
        outcome = self._determine_outcome(messages, user_request)
        corrections = self._count_corrections(messages)
        
        # Store pattern
        sequence_key = self._hash_sequence(tool_sequence)
        pattern = self.tool_patterns[request_type][sequence_key]
        
        if not pattern["tools"]:
            pattern["tools"] = tool_sequence
            pattern["examples"] = []
        
        pattern["count"] += 1
        if outcome == "success":
            pattern["success_count"] += 1
        else:
            pattern["failure_count"] += 1
        
        pattern["total_corrections"] += corrections
        
        # Store example (limit to 5 per sequence)
        if len(pattern["examples"]) < 5:
            pattern["examples"].append({
                "request": user_request[:100],
                "outcome": outcome,
                "corrections": corrections
            })
    
    def _extract_messages(self, conversation: Dict) -> List[Dict]:
        """Extract messages from conversation structure"""
        messages = []
        
        # Try various conversation formats
        if "messages" in conversation:
            messages = conversation["messages"]
        elif "allComposers" in conversation:
            # Flatten composers
            for composer in conversation["allComposers"]:
                if "messages" in composer:
                    messages.extend(composer["messages"])
        elif isinstance(conversation, dict):
            # Try to find message-like structures
            conv_str = json.dumps(conversation)
            # Look for tool call patterns in text
            if any(tool in conv_str for tool in KNOWN_TOOLS):
                messages.append(conversation)
        
        return messages
    
    def _extract_text(self, message: Dict) -> str:
        """Extract text content from message"""
        if isinstance(message, str):
            return message
        
        if "content" in message:
            content = message["content"]
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Extract text from content array
                texts = [item.get("text", "") for item in content if isinstance(item, dict)]
                return " ".join(texts)
        
        # Fallback: convert to string
        return json.dumps(message)
    
    def _extract_tool_calls(self, message: Dict) -> List[str]:
        """Extract tool calls from assistant message"""
        tools = []
        message_str = json.dumps(message).lower()
        
        # Look for tool call patterns
        # Pattern 1: Function calls in JSON
        for tool in KNOWN_TOOLS:
            if tool.lower() in message_str:
                # Check if it's actually a tool call (not just mentioned)
                patterns = [
                    f'"{tool}"',
                    f"'{tool}'",
                    f"function.*{tool}",
                    f"tool.*{tool}",
                ]
                if any(re.search(p, message_str, re.IGNORECASE) for p in patterns):
                    if tool not in tools:
                        tools.append(tool)
        
        # Pattern 2: Look for tool_calls array in message
        if "tool_calls" in message:
            for call in message["tool_calls"]:
                if "function" in call and "name" in call["function"]:
                    tool_name = call["function"]["name"]
                    if tool_name in KNOWN_TOOLS and tool_name not in tools:
                        tools.append(tool_name)
        
        # Pattern 3: Look for function_call in content
        if "content" in message and isinstance(message["content"], list):
            for item in message["content"]:
                if isinstance(item, dict) and "function_call" in item:
                    func = item["function_call"]
                    if "name" in func:
                        tool_name = func["name"]
                        if tool_name in KNOWN_TOOLS and tool_name not in tools:
                            tools.append(tool_name)
        
        return tools
    
    def _classify_request(self, request: str) -> str:
        """Classify request into type"""
        request_lower = request.lower()
        
        # Request type patterns
        patterns = {
            "code_analysis": ["analyze", "review", "check code", "security", "audit", "examine"],
            "file_operation": ["read", "edit", "create", "delete", "update", "write", "modify"],
            "search": ["find", "search", "locate", "where is", "show me"],
            "debug": ["fix", "error", "bug", "issue", "broken", "not working"],
            "setup": ["setup", "install", "configure", "initialize", "deploy"],
            "documentation": ["document", "explain", "guide", "how", "what is"],
            "governance": ["governance", "compliance", "suite 6", "canonical header"],
            "learning": ["learning", "chat export", "memory", "lessons", "extract"],
            "n8n": ["n8n", "workflow", "node", "webhook"],
            "mack": ["mack", "plastics", "brokerage", "odoo"],
        }
        
        for req_type, keywords in patterns.items():
            if any(keyword in request_lower for keyword in keywords):
                return req_type
        
        return "general"
    
    def _determine_outcome(self, messages: List[Dict], user_request: str) -> str:
        """Determine if conversation was successful"""
        # Look for success indicators in subsequent user messages
        success_patterns = [
            r"(?i)(perfect|exactly|yes|correct|right|thanks|thank you|great|good)",
            r"(?i)(that'?s (it|what i wanted|correct))",
        ]
        
        failure_patterns = [
            r"(?i)(no|wrong|incorrect|that'?s not|you'?re wrong|try again)",
            r"(?i)(actually|instead|should be|meant to|misunderstood)",
        ]
        
        # Check user messages after first assistant response
        found_assistant = False
        for msg in messages:
            if found_assistant:
                role = str(msg.get("role", "")).lower()
                if "user" in role:
                    text = self._extract_text(msg).lower()
                    
                    # Check for failure first (more specific)
                    for pattern in failure_patterns:
                        if re.search(pattern, text):
                            return "failure"
                    
                    # Check for success
                    for pattern in success_patterns:
                        if re.search(pattern, text):
                            return "success"
            
            if "assistant" in str(msg.get("role", "")).lower():
                found_assistant = True
        
        # Default: assume success if no corrections detected
        return "success"
    
    def _count_corrections(self, messages: List[Dict]) -> int:
        """Count number of corrections in conversation"""
        corrections = 0
        correction_patterns = [
            r"(?i)(no|wrong|incorrect|that'?s not right)",
            r"(?i)(actually|instead|should be)",
        ]
        
        for msg in messages:
            role = str(msg.get("role", "")).lower()
            if "user" in role:
                text = self._extract_text(msg).lower()
                for pattern in correction_patterns:
                    if re.search(pattern, text):
                        corrections += 1
                        break
        
        return corrections
    
    def _hash_sequence(self, tools: List[str]) -> str:
        """Create hash for tool sequence"""
        sequence_str = "→".join(tools)
        return hashlib.md5(sequence_str.encode()).hexdigest()[:12]
    
    def _calculate_success_rates(self):
        """Calculate success rates for all patterns"""
        for request_type in self.tool_patterns:
            for sequence_key in self.tool_patterns[request_type]:
                pattern = self.tool_patterns[request_type][sequence_key]
                total = pattern["count"]
                if total > 0:
                    pattern["success_rate"] = pattern["success_count"] / total
                    pattern["avg_corrections"] = pattern["total_corrections"] / total
                else:
                    pattern["success_rate"] = 0.0
                    pattern["avg_corrections"] = 0.0
    
    def _save_patterns(self):
        """Save tool patterns to JSON file"""
        output = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "request_types": {}
        }
        
        # Convert defaultdict to regular dict
        for request_type, sequences in self.tool_patterns.items():
            output["request_types"][request_type] = {}
            for seq_key, pattern in sequences.items():
                output["request_types"][request_type][seq_key] = {
                    "tools": pattern["tools"],
                    "success_rate": pattern.get("success_rate", 0.0),
                    "count": pattern["count"],
                    "success_count": pattern["success_count"],
                    "failure_count": pattern["failure_count"],
                    "avg_corrections": pattern.get("avg_corrections", 0.0),
                    "examples": pattern["examples"][:3]  # Limit examples
                }
        
        TOOL_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOOL_PATTERNS_FILE, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✅ Tool patterns saved to: {TOOL_PATTERNS_FILE}")


def main():
    extractor = ToolPatternExtractor()
    extractor.extract_all_patterns()


if __name__ == "__main__":
    main()


