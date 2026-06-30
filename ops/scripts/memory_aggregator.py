#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-AGG-001"
component_name: "Memory Aggregator"
layer: "operations"
domain: "learning"
type: "aggregator"
status: "active"
created: "2025-10-06T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3", "json", "sqlite3", "re", "pathlib"]
integrates_with: ["OPS-EXP-001", "OPS-LEA-001", "INT-LE-001"]
data_sources: ["ops/logs/chat_exports", "cursor_leveldb"]
outputs: ["ops/logs/memory_index.json", "ops/logs/memory_aggregator.log"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Parse chat exports and extract learnings using pattern detection"
summary: "Analyzes Cursor chat exports to identify mistakes, solutions, and patterns"
business_value: "Enables automated learning extraction without manual intervention"
success_metrics: ["detection_accuracy >= 95%", "processing_time < 5s", "false_positive_rate < 5%"]

# === TAGS & CLASSIFICATION ===
tags: ["memory", "aggregation", "pattern-detection", "learning", "automation"]
keywords: ["chat", "export", "parsing", "learning", "pattern", "detection"]
related_components: ["OPS-EXP-001", "OPS-LEA-001", "INT-LE-001", "INT-ML-001"]
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib

# LevelDB support for new export format
try:
    import plyvel
    LEVELDB_AVAILABLE = True
except ImportError:
    LEVELDB_AVAILABLE = False

# Configuration - Use Dropbox as single source of truth
def get_global_commands_path():
    """Get GlobalCommands path, preferring Dropbox location"""
    import logging
    
    fallback_log = Path.home() / ".cursor-globalcommands-fallback.log"
    disable_fallback = os.environ.get("DISABLE_FALLBACK", "0") == "1"
    
    dropbox_paths = [
        Path.home() / ".cursor-governance"
    ]
    library_path = Path(os.path.expanduser("~/.cursor-governance"))
    
    # Try Dropbox paths first
    for path in dropbox_paths:
        if path.exists():
            return path
    
    # Fallback to Library
    if library_path.exists():
        if disable_fallback:
            raise FileNotFoundError(
                "Dropbox GlobalCommands not found and DISABLE_FALLBACK=1. "
                "Set DISABLE_FALLBACK=0 to allow fallback, or fix Dropbox path."
            )
        
        # Log fallback usage
        from datetime import datetime
        log_entry = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FALLBACK USED: Library path instead of Dropbox
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: memory_aggregator.py
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Path: {library_path}
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   User: {os.getenv('USER', 'unknown')}
---
"""
        with open(fallback_log, 'a') as f:
            f.write(log_entry)
        
        print("\n⚠️  WARNING: Using Library fallback (logged to ~/.cursor-globalcommands-fallback.log)")
        return library_path
    
    raise FileNotFoundError("GlobalCommands directory not found in Dropbox or Library")

GLOBAL_COMMANDS = get_global_commands_path()
CHAT_EXPORTS_DIR = GLOBAL_COMMANDS / "ops/logs/chat_exports"
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"
LEARNING_DIR = GLOBAL_COMMANDS / "learning"

# Learning file paths
REPEATED_MISTAKES = LEARNING_DIR / "failures/repeated-mistakes.md"
QUICK_FIXES = LEARNING_DIR / "patterns/quick-fixes.md"
AUTH_FIXES = LEARNING_DIR / "solutions/authentication-fixes.md"
JSON_ISSUES = LEARNING_DIR / "solutions/json-issues.md"

class LearningPattern:
    """Represents a learning pattern extracted from conversations"""
    def __init__(self, pattern_type: str, content: str, context: Any, timestamp: str, 
                 enhanced_context: Optional[Dict[str, Any]] = None):
        self.pattern_type = pattern_type  # mistake, solution, pattern, insight
        self.content = content
        self.context = context  # Can be string or dict
        self.timestamp = timestamp
        self.enhanced_context = enhanced_context or {}
        self.hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate unique hash for deduplication"""
        unique_str = f"{self.pattern_type}:{self.content}:{str(self.context)}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "hash": self.hash,
            "type": self.pattern_type,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp
        }
        
        # Add enhanced context if available
        if self.enhanced_context:
            result["enhanced_context"] = self.enhanced_context
        
        return result


class MemoryAggregator:
    """Main class for aggregating and processing chat memories"""
    
    def __init__(self):
        self.memory_index = self._load_memory_index()
        self.processed_exports = set(self.memory_index.get("processed_exports", []))
        self.learnings = self.memory_index.get("learnings", [])
        self.stats = self.memory_index.get("stats", {
            "total_exports_processed": 0,
            "total_conversations": 0,
            "total_learnings_extracted": 0,
            "last_run": None
        })
    
    def _load_memory_index(self) -> Dict[str, Any]:
        """Load existing memory index or create new one"""
        if MEMORY_INDEX.exists():
            try:
                with open(MEMORY_INDEX, 'r') as f:
                    content = f.read().strip()
                    if content and content != "{}":
                        return json.loads(content)
            except json.JSONDecodeError:
                print(f"⚠️  Memory index corrupted, creating new one")
        
        return {
            "version": "2.0.0",
            "last_updated": None,
            "processed_exports": [],
            "learnings": [],
            "stats": {
                "total_exports_processed": 0,
                "total_conversations": 0,
                "total_learnings_extracted": 0,
                "last_run": None
            }
        }
    
    def _save_memory_index(self):
        """Save memory index to disk"""
        self.memory_index["last_updated"] = datetime.now().isoformat()
        self.memory_index["processed_exports"] = list(self.processed_exports)
        self.memory_index["learnings"] = self.learnings
        self.memory_index["stats"] = self.stats
        
        MEMORY_INDEX.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_INDEX, 'w') as f:
            json.dump(self.memory_index, f, indent=2)
        print(f"✅ Memory index saved: {len(self.learnings)} learnings tracked")
    
    def process_all_exports(self):
        """Process all chat exports"""
        if not CHAT_EXPORTS_DIR.exists():
            print(f"❌ No chat exports found at: {CHAT_EXPORTS_DIR}")
            return
        
        export_dirs = sorted([d for d in CHAT_EXPORTS_DIR.iterdir() if d.is_dir()])
        print(f"📂 Found {len(export_dirs)} chat export directories")
        
        new_exports = [d for d in export_dirs if d.name not in self.processed_exports]
        
        if not new_exports:
            print("✅ No new exports to process")
            return
        
        print(f"🔍 Processing {len(new_exports)} new exports...")
        
        for export_dir in new_exports:
            print(f"\n📊 Processing: {export_dir.name}")
            self._process_export(export_dir)
            self.processed_exports.add(export_dir.name)
            self.stats["total_exports_processed"] += 1
        
        self.stats["last_run"] = datetime.now().isoformat()
        self._save_memory_index()
        print(f"\n✅ Processing complete! Total learnings: {len(self.learnings)}")
    
    def _process_export(self, export_dir: Path):
        """Process a single export directory"""
        conversations_found = 0
        
        # Try new LevelDB format first (chat_data directory)
        chat_data_dir = export_dir / "chat_data"
        if chat_data_dir.exists():
            try:
                conversations = self._extract_leveldb_conversations(chat_data_dir)
                if conversations:
                    conversations_found += len(conversations)
                    self.stats["total_conversations"] += len(conversations)
                    self._analyze_conversations(conversations)
                print(f"  ✅ Found {conversations_found} conversations (LevelDB)")
                return
            except Exception as e:
                print(f"  ⚠️  Error processing LevelDB: {e}")
        
        # Fallback to old SQLite format (User/workspaceStorage)
        workspace_storage = export_dir / "User/workspaceStorage"
        if workspace_storage.exists():
            workspaces = [d for d in workspace_storage.iterdir() if d.is_dir()]
            
            for workspace in workspaces:
                state_db = workspace / "state.vscdb"
                if not state_db.exists():
                    continue
                
                try:
                    conversations = self._extract_conversations(state_db)
                    if conversations:
                        conversations_found += len(conversations)
                        self.stats["total_conversations"] += len(conversations)
                        self._analyze_conversations(conversations)
                except Exception as e:
                    print(f"  ⚠️  Error processing {workspace.name}: {e}")
            
            print(f"  ✅ Found {conversations_found} conversations (SQLite)")
            return
        
        print(f"  ⚠️  No chat data found (tried LevelDB and SQLite formats)")
    
    def _extract_leveldb_conversations(self, chat_data_dir: Path) -> List[Dict[str, Any]]:
        """Extract conversations from LevelDB chat data"""
        conversations = []
        
        # PRAGMATIC APPROACH: Read LIVE Cursor data instead of export
        # This bypasses the plyvel linking issues
        live_db_path = Path.home() / "Library/Application Support/Cursor/Local Storage/leveldb"
        
        if not live_db_path.exists():
            print(f"    ⚠️  Live Cursor database not found at {live_db_path}")
            return conversations
        
        # Try using plyvel if available and working
        if LEVELDB_AVAILABLE:
            try:
                import plyvel
                db = plyvel.DB(str(live_db_path), create_if_missing=False)
                
                # Iterate through all keys in the database
                for key, value in db:
                    try:
                        # Keys and values in Cursor's LevelDB are typically strings
                        key_str = key.decode('utf-8', errors='ignore')
                        value_str = value.decode('utf-8', errors='ignore')
                        
                        # Look for chat/composer data
                        # Cursor stores chat data with keys like "composer" or "chat"
                        if any(pattern in key_str.lower() for pattern in ['composer', 'chat', 'conversation']):
                            try:
                                # Try to parse as JSON
                                data = json.loads(value_str)
                                if isinstance(data, dict):
                                    conversations.append(data)
                                elif isinstance(data, list):
                                    conversations.extend([item for item in data if isinstance(item, dict)])
                            except json.JSONDecodeError:
                                # Value is not JSON, skip
                                pass
                    except Exception as e:
                        # Skip problematic entries
                        continue
                
                db.close()
                return conversations
            except Exception as e:
                print(f"    ⚠️  LevelDB plyvel error: {e}")
        
        # Fallback: Simple text-based pattern detection from export
        # This doesn't extract full conversations but can still detect patterns
        print(f"    ℹ️  Using fallback text-based analysis (plyvel unavailable)")
        
        # Check if there are any .log files in the export
        log_files = list(chat_data_dir.glob("*.log"))
        if log_files:
            for log_file in log_files:
                try:
                    # Read as binary and look for text patterns
                    content = log_file.read_bytes().decode('utf-8', errors='ignore')
                    
                    # Look for JSON-like structures
                    # This is a rough heuristic
                    json_patterns = re.findall(r'\{[^{}]*"[^"]*"[^{}]*\}', content)
                    for pattern in json_patterns[:100]:  # Limit to prevent overload
                        try:
                            data = json.loads(pattern)
                            if isinstance(data, dict):
                                conversations.append(data)
                        except:
                            pass
                except Exception as e:
                    continue
        
        return conversations
    
    def _extract_conversations(self, state_db: Path) -> List[Dict[str, Any]]:
        """Extract conversations from state database (SQLite format)"""
        conversations = []
        
        try:
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()
            
            # Extract composer data (contains chat history)
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
            print(f"    ⚠️  Database error: {e}")
        
        return conversations
    
    def _analyze_conversations(self, conversations: List[Dict[str, Any]]):
        """Analyze conversations for learning patterns"""
        # Process conversations with message windows for context
        for i, conv in enumerate(conversations):
            # Skip if no meaningful data
            if not isinstance(conv, dict):
                continue
            
            # Extract message window for context (3 messages before/after)
            message_window = self._extract_message_window(conversations, i)
            
            # Check for "LESSON" trigger first (highest priority)
            if self._detect_lesson_trigger(conv, conversations, i):
                continue  # Already processed
            
            # Look for correction patterns
            self._detect_corrections(conv, message_window)
            
            # Look for mistakes
            self._detect_mistakes(conv, message_window)
            
            # Look for solutions
            self._detect_solutions(conv, message_window)
    
    def _extract_message_window(self, conversations: List[Dict[str, Any]], index: int, window_size: int = 3) -> List[Dict[str, Any]]:
        """Extract message window around current conversation"""
        start = max(0, index - window_size)
        end = min(len(conversations), index + window_size + 1)
        return conversations[start:end]
    
    def _extract_structured_snippets(self, message_window: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structured snippets from message window"""
        snippets = {
            'conversation_id': message_window[0].get('composerId', 'unknown') if message_window else 'unknown',
            'message_count': len(message_window),
            'messages': []
        }
        
        for msg in message_window[:5]:  # Limit to 5 messages
            msg_text = json.dumps(msg)
            snippets['messages'].append({
                'content': msg_text[:200],  # Truncate for storage
                'timestamp': msg.get('timestamp', '')
            })
        
        return snippets
    
    def _detect_lesson_trigger(self, conv: Dict[str, Any], conversations: List[Dict[str, Any]], index: int) -> bool:
        """Detect 'LESSON' trigger and extract 10 previous messages"""
        conv_text = json.dumps(conv).lower()
        
        # Check for "LESSON" keyword (case-insensitive)
        if re.search(r'\blesson\b', conv_text, re.IGNORECASE):
            # Extract 10 previous messages from full conversations list
            prev_start = max(0, index - 10)
            prev_messages = conversations[prev_start:index]
            
            # Extract structured context
            enhanced_context = {
                'trigger_type': 'LESSON',
                'trigger_message': json.dumps(conv)[:500],
                'message_window': [json.dumps(m)[:200] for m in prev_messages],
                'window_size': len(prev_messages),
                'priority': 'HIGH'
            }
            
            learning = LearningPattern(
                pattern_type="lesson",
                content="User-initiated lesson request detected",
                context=json.dumps(enhanced_context),
                timestamp=datetime.now().isoformat(),
                enhanced_context=enhanced_context
            )
            
            self._add_learning(learning)
            return True
        
        return False
    
    def _detect_corrections(self, conv: Dict[str, Any], message_window: List[Dict[str, Any]]):
        """L9-Enhanced: Multi-modal correction detection with confidence scoring"""
        conv_text = json.dumps(conv).lower()
        full_context = ' '.join([json.dumps(m) for m in message_window]).lower()
        
        # L9 Correction Patterns with confidence levels
        correction_patterns = {
            "explicit_rejection": {
                "patterns": [r"(?i)\b(no|wrong|incorrect|that'?s not right|you'?re wrong|stop|don'?t)\b"],
                "confidence_base": 0.95,
                "severity": "HIGH"
            },
            "clarification": {
                "patterns": [r"(?i)\b(actually|instead|should be|meant to|i meant|i want)\b"],
                "confidence_base": 0.85,
                "severity": "MEDIUM"
            },
            "repetition_indicator": {
                "patterns": [r"(?i)\b(i (told|said|asked|reminded) you|again|still|still.*happening|wtf|fuck|dick|can'?t believe you)\b"],
                "confidence_base": 0.90,
                "severity": "HIGH",
                "pattern_type": "behavioral"  # Indicates repeated mistake or frustration
            },
            "understanding_gap": {
                "patterns": [r"(?i)\b(misunderstood|didn'?t understand|not what i meant|confused)\b"],
                "confidence_base": 0.80,
                "severity": "MEDIUM"
            },
            "critical_reminder": {
                "patterns": [r"(?i)\b(critical|must|never|always|10/10|important)\b.*\b(remind|issue|problem)\b"],
                "confidence_base": 0.98,
                "severity": "CRITICAL",
                "pattern_type": "logical"  # Indicates critical rule violation
            }
        }
        
        detected_corrections = []
        
        for correction_type, config in correction_patterns.items():
            patterns = config["patterns"]
            confidence_base = config["confidence_base"]
            severity = config.get("severity", "MEDIUM")
            
            for pattern in patterns:
                matches = re.findall(pattern, full_context)
                if matches:
                    # Abductive: Calculate discovery confidence
                    match_count = len(matches)
                    frequency_bonus = min(0.15, match_count * 0.05)  # Repeated corrections = higher confidence
                    
                    # Deductive: Validate correction context
                    has_previous_error = any('error' in json.dumps(m).lower() for m in message_window[:-1])
                    has_explanation = len([m for m in message_window if len(json.dumps(m)) > 100]) > 2
                    context_score = (0.3 if has_previous_error else 0.0) + (0.2 if has_explanation else 0.0)
                    
                    # Inductive: Assess correction value (how generalizable)
                    correction_value = 0.5  # Base
                    if severity == "CRITICAL":
                        correction_value += 0.3
                    if correction_type == "repetition_indicator":
                        correction_value += 0.2  # Repeated mistakes are high-value lessons
                    
                    # Calculate final confidence
                    confidence = min(1.0, confidence_base + frequency_bonus + context_score)
                    
                    # Extract enhanced context with L9 metadata
                    enhanced_context = self._extract_structured_snippets(message_window)
                    enhanced_context['trigger_type'] = 'correction'
                    enhanced_context['correction_type'] = correction_type
                    enhanced_context['confidence'] = confidence
                    enhanced_context['severity'] = severity
                    enhanced_context['detection_method'] = 'l9_multi_modal'
                    enhanced_context['match_count'] = match_count
                    enhanced_context['correction_value'] = correction_value
                    enhanced_context['pattern_type'] = config.get('pattern_type', 'behavioral')
                    
                    detected_corrections.append({
                        'type': correction_type,
                        'confidence': confidence,
                        'enhanced_context': enhanced_context
                    })
                    break  # One pattern per correction type
        
        # Create learning patterns for detected corrections
        for detection in detected_corrections:
            learning = LearningPattern(
                pattern_type="mistake",
                content=f"L9-detected user correction: {detection['type']} (confidence: {detection['confidence']:.2f}, severity: {detection['enhanced_context'].get('severity', 'MEDIUM')})",
                context=f"Correction pattern: {detection['type']}",
                timestamp=datetime.now().isoformat(),
                enhanced_context=detection['enhanced_context']
            )
            self._add_learning(learning)
    
    def _detect_mistakes(self, conv: Dict[str, Any], message_window: List[Dict[str, Any]]):
        """L9-Enhanced: Multi-modal mistake detection with pattern classification"""
        conv_text = json.dumps(conv).lower()
        full_context = ' '.join([json.dumps(m) for m in message_window]).lower()
        
        # L9 Pattern Type 1: Structural Patterns (code/workflow structure issues)
        structural_patterns = {
            "path_hardcode": {
                "patterns": [r"/users/[^/]+/", r"hardcoded.*path", r"\$home.*not.*used", r"absolute.*path"],
                "confidence_base": 0.85,
                "pattern_type": "structural"
            },
            "symlink_misunderstanding": {
                "patterns": [r"display.*folder", r"show.*sidebar", r"left margin", r"symlink.*display"],
                "confidence_base": 0.80,
                "pattern_type": "structural"
            },
            "workflow_structure": {
                "patterns": [r"workflow.*import.*fail", r"missing.*node.*id", r"workflow.*structure"],
                "confidence_base": 0.75,
                "pattern_type": "structural"
            }
        }
        
        # L9 Pattern Type 2: Logical Patterns (reasoning/decision errors)
        logical_patterns = {
            "tool_selection": {
                "patterns": [r"first.*tool.*without.*compar", r"didn'?t.*compare.*options", r"should.*have.*compared"],
                "confidence_base": 0.90,
                "pattern_type": "logical"
            },
            "assumption_error": {
                "patterns": [r"assumed.*without.*check", r"didn'?t.*verify", r"took.*for.*granted"],
                "confidence_base": 0.85,
                "pattern_type": "logical"
            },
            "intent_misunderstanding": {
                "patterns": [r"misunderstood.*intent", r"not.*what.*i.*meant", r"wrong.*deliverable"],
                "confidence_base": 0.88,
                "pattern_type": "logical"
            }
        }
        
        # L9 Pattern Type 3: Behavioral Patterns (error handling/process issues)
        behavioral_patterns = {
            "auth": {
                "patterns": [r"authentication.*fail", r"credential.*error", r"401", r"403", r"auth.*header.*invalid"],
                "confidence_base": 0.85,
                "pattern_type": "behavioral",
                "quick_fix": "Use predefinedCredentialType instead of manual headers"
            },
            "json": {
                "patterns": [r"json.*error", r"parsing.*failed", r"invalid json", r"jsondecodeerror", r"string.*wrapped.*json"],
                "confidence_base": 0.90,
                "pattern_type": "behavioral",
                "quick_fix": "Double json.loads() for string-wrapped JSON"
            },
            "n8n": {
                "patterns": [r"n8n.*error", r"workflow.*failed", r"node.*error", r"expression.*error", r"spaces.*in.*expression"],
                "confidence_base": 0.80,
                "pattern_type": "behavioral",
                "quick_fix": "Remove ALL spaces from n8n expressions"
            },
            "supabase": {
                "patterns": [r"supabase.*auth", r"supabase.*error", r"supabase.*connection"],
                "confidence_base": 0.75,
                "pattern_type": "behavioral"
            },
            "fabrication": {
                "patterns": [r"fabricat.*data", r"made.*up", r"invent.*value", r"guessed.*without.*confirm"],
                "confidence_base": 0.95,
                "pattern_type": "behavioral",
                "severity": "CRITICAL"
            },
            "claim_without_proof": {
                "patterns": [r"claim.*fix.*without.*proof", r"should.*work.*now", r"try.*it.*let.*me.*know"],
                "confidence_base": 0.90,
                "pattern_type": "behavioral",
                "severity": "HIGH"
            }
        }
        
        # L9 Pattern Type 4: Relationship Patterns (dependency/cascade issues)
        relationship_patterns = {
            "dependency_error": {
                "patterns": [r"missing.*dependenc", r"import.*error", r"module.*not.*found", r"circular.*dependenc"],
                "confidence_base": 0.80,
                "pattern_type": "relationship"
            },
            "cascade_failure": {
                "patterns": [r"cascade.*fail", r"chain.*reaction", r"one.*error.*led.*to", r"domino.*effect"],
                "confidence_base": 0.75,
                "pattern_type": "relationship"
            }
        }
        
        # Combine all pattern categories
        all_patterns = {
            **structural_patterns,
            **logical_patterns,
            **behavioral_patterns,
            **relationship_patterns
        }
        
        # Multi-modal detection: Abductive (discover) + Deductive (validate) + Inductive (generalize)
        detected_patterns = []
        
        for mistake_type, config in all_patterns.items():
            patterns = config["patterns"]
            confidence_base = config["confidence_base"]
            pattern_type = config.get("pattern_type", "unknown")
            
            for pattern in patterns:
                if re.search(pattern, conv_text) or re.search(pattern, full_context):
                    # Abductive: Calculate discovery confidence
                    match_count = len(re.findall(pattern, full_context))
                    frequency_bonus = min(0.1, match_count * 0.02)  # Up to +0.1 for multiple matches
                    
                    # Deductive: Validate pattern consistency
                    context_quality = self._assess_context_quality(message_window)
                    validation_score = context_quality * 0.2  # Up to +0.2 for good context
                    
                    # Inductive: Generalize pattern applicability
                    pattern_specificity = self._assess_pattern_specificity(pattern, mistake_type)
                    generalization_score = pattern_specificity * 0.1  # Up to +0.1 for specific patterns
                    
                    # Calculate final confidence (L9 multi-modal synthesis)
                    confidence = min(1.0, confidence_base + frequency_bonus + validation_score + generalization_score)
                    
                    # Extract enhanced context with L9 metadata
                    enhanced_context = self._extract_structured_snippets(message_window)
                    enhanced_context['trigger_type'] = 'mistake'
                    enhanced_context['error_pattern'] = pattern
                    enhanced_context['pattern_type'] = pattern_type
                    enhanced_context['confidence'] = confidence
                    enhanced_context['detection_method'] = 'l9_multi_modal'
                    enhanced_context['abductive_score'] = confidence_base + frequency_bonus
                    enhanced_context['deductive_score'] = validation_score
                    enhanced_context['inductive_score'] = generalization_score
                    
                    if 'quick_fix' in config:
                        enhanced_context['quick_fix'] = config['quick_fix']
                    if 'severity' in config:
                        enhanced_context['severity'] = config['severity']
                    
                    detected_patterns.append({
                        'type': mistake_type,
                        'pattern': pattern,
                        'confidence': confidence,
                        'enhanced_context': enhanced_context
                    })
                    break  # One pattern per mistake type
        
        # Create learning patterns for detected mistakes
        for detection in detected_patterns:
            learning = LearningPattern(
                pattern_type="mistake",
                content=f"L9-detected {detection['type']} issue (confidence: {detection['confidence']:.2f})",
                context=detection['pattern'],
                timestamp=datetime.now().isoformat(),
                enhanced_context=detection['enhanced_context']
            )
            self._add_learning(learning)
    
    def _assess_context_quality(self, message_window: List[Dict[str, Any]]) -> float:
        """Assess quality of context for pattern validation (Deductive reasoning)"""
        if not message_window:
            return 0.0
        
        # Quality factors
        has_error_message = any('error' in json.dumps(m).lower() for m in message_window)
        has_user_correction = any('wrong' in json.dumps(m).lower() or 'incorrect' in json.dumps(m).lower() for m in message_window)
        has_solution = any('fix' in json.dumps(m).lower() or 'work' in json.dumps(m).lower() for m in message_window)
        context_length = len(message_window)
        
        score = 0.0
        if has_error_message:
            score += 0.3
        if has_user_correction:
            score += 0.4
        if has_solution:
            score += 0.2
        if context_length >= 5:
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_pattern_specificity(self, pattern: str, mistake_type: str) -> float:
        """Assess pattern specificity for generalization (Inductive reasoning)"""
        # More specific patterns (with context words) score higher
        specific_indicators = ['error', 'failed', 'invalid', 'missing', 'wrong', 'incorrect']
        generic_patterns = [r'\b\w+\b', r'.*', r'\w+']
        
        specificity = 0.5  # Base score
        
        # Check if pattern contains specific error indicators
        if any(indicator in pattern.lower() for indicator in specific_indicators):
            specificity += 0.3
        
        # Check if pattern is too generic
        if any(gp in pattern for gp in generic_patterns):
            specificity -= 0.2
        
        # Mistake type specificity bonus
        if mistake_type in ['fabrication', 'claim_without_proof', 'tool_selection']:
            specificity += 0.2  # High-value patterns
        
        return max(0.0, min(1.0, specificity))
    
    def _detect_solutions(self, conv: Dict[str, Any], message_window: List[Dict[str, Any]]):
        """L9-Enhanced: Solution detection with pattern extraction for reuse"""
        conv_text = json.dumps(conv).lower()
        full_context = ' '.join([json.dumps(m) for m in message_window]).lower()
        
        # L9 Solution Patterns with validation requirements
        solution_patterns = {
            "explicit_success": {
                "patterns": [r"(?i)\b(fixed|solved|working now|success|resolved|it works)\b"],
                "confidence_base": 0.85,
                "requires_proof": True
            },
            "user_confirmation": {
                "patterns": [r"(?i)\b(that worked|perfect|exactly|great|thanks|appreciate)\b"],
                "confidence_base": 0.90,
                "requires_proof": False  # User confirmation is proof
            },
            "completion_indicator": {
                "patterns": [r"(?i)(✅|done|complete|finished|all set)"],
                "confidence_base": 0.80,
                "requires_proof": False
            },
            "proof_provided": {
                "patterns": [r"(?i)\b(exit code.*0|test.*pass|verified|confirmed.*working)\b"],
                "confidence_base": 0.95,
                "requires_proof": False,
                "pattern_type": "behavioral"  # Indicates good practice
            }
        }
        
        detected_solutions = []
        
        for solution_type, config in solution_patterns.items():
            patterns = config["patterns"]
            confidence_base = config["confidence_base"]
            requires_proof = config.get("requires_proof", False)
            
            for pattern in patterns:
                if re.search(pattern, conv_text) or re.search(pattern, full_context):
                    # Abductive: Calculate discovery confidence
                    match_count = len(re.findall(pattern, full_context))
                    frequency_bonus = min(0.1, match_count * 0.03)
                    
                    # Deductive: Validate solution (check for proof if required)
                    has_proof = self._check_solution_proof(message_window)
                    proof_score = 0.0
                    if requires_proof:
                        proof_score = 0.2 if has_proof else -0.1  # Penalty if proof required but missing
                    else:
                        proof_score = 0.1 if has_proof else 0.0  # Bonus if proof present
                    
                    # Inductive: Extract reusable solution pattern
                    solution_pattern = self._extract_solution_pattern(message_window)
                    pattern_value = 0.3 if solution_pattern else 0.0
                    
                    # Calculate final confidence
                    confidence = min(1.0, max(0.0, confidence_base + frequency_bonus + proof_score + pattern_value))
                    
                    # Extract enhanced context with L9 metadata
                    enhanced_context = self._extract_structured_snippets(message_window)
                    enhanced_context['trigger_type'] = 'solution'
                    enhanced_context['solution_type'] = solution_type
                    enhanced_context['confidence'] = confidence
                    enhanced_context['has_proof'] = has_proof
                    enhanced_context['detection_method'] = 'l9_multi_modal'
                    if solution_pattern:
                        enhanced_context['reusable_pattern'] = solution_pattern
                        enhanced_context['pattern_type'] = config.get('pattern_type', 'behavioral')
                    
                    detected_solutions.append({
                        'type': solution_type,
                        'confidence': confidence,
                        'enhanced_context': enhanced_context
                    })
                    break  # One pattern per solution type
        
        # Create learning patterns for detected solutions
        for detection in detected_solutions:
            learning = LearningPattern(
                pattern_type="solution",
                content=f"L9-detected successful solution: {detection['type']} (confidence: {detection['confidence']:.2f})",
                context=f"Solution pattern: {detection['type']}",
                timestamp=datetime.now().isoformat(),
                enhanced_context=detection['enhanced_context']
            )
            self._add_learning(learning)
    
    def _check_solution_proof(self, message_window: List[Dict[str, Any]]) -> bool:
        """Check if solution has proof (command output, test results, etc.)"""
        proof_indicators = [
            r'exit code.*0',
            r'test.*pass',
            r'verified',
            r'confirmed',
            r'output.*success',
            r'✅',
            r'working',
            r'no.*error'
        ]
        
        full_text = ' '.join([json.dumps(m) for m in message_window]).lower()
        return any(re.search(pattern, full_text) for pattern in proof_indicators)
    
    def _extract_solution_pattern(self, message_window: List[Dict[str, Any]]) -> str:
        """Extract reusable solution pattern from context (Inductive reasoning)"""
        # Look for code blocks, command sequences, or structured fixes
        solution_keywords = ['fix', 'solution', 'change', 'update', 'replace', 'use', 'instead']
        
        for msg in message_window:
            msg_text = json.dumps(msg).lower()
            if any(keyword in msg_text for keyword in solution_keywords):
                # Try to extract the actual fix (simplified - could be enhanced)
                if 'code' in msg_text or 'command' in msg_text or 'script' in msg_text:
                    return msg_text[:200]  # Return snippet as pattern
        
        return ""
    
    def _add_learning(self, learning: LearningPattern):
        """Add learning to index (with deduplication)"""
        learning_dict = learning.to_dict()
        
        # Check if already exists
        existing_hashes = [l['hash'] for l in self.learnings]
        if learning.hash not in existing_hashes:
            self.learnings.append(learning_dict)
            self.stats["total_learnings_extracted"] += 1
    
    def generate_report(self) -> str:
        """Generate summary report"""
        report = f"""
╔════════════════════════════════════════════════════════════╗
║          MEMORY AGGREGATOR - LEARNING REPORT              ║
╠════════════════════════════════════════════════════════════╣
║  Exports Processed:     {self.stats['total_exports_processed']:>4}                              ║
║  Conversations Found:   {self.stats['total_conversations']:>4}                              ║
║  Learnings Extracted:   {self.stats['total_learnings_extracted']:>4}                              ║
║  Last Run:              {self.stats.get('last_run', 'Never')[:19]:>19}           ║
╠════════════════════════════════════════════════════════════╣
║  LEARNING BREAKDOWN                                        ║
╠════════════════════════════════════════════════════════════╣
"""
        
        # Count by type
        types = {}
        for l in self.learnings:
            types[l['type']] = types.get(l['type'], 0) + 1
        
        for ltype, count in types.items():
            report += f"║  {ltype.capitalize():<20} {count:>4}                          ║\n"
        
        report += "╚════════════════════════════════════════════════════════════╝\n"
        
        return report


def main():
    """Main execution"""
    print("🚀 Memory Aggregator v2.0.0 - Starting...\n")
    
    aggregator = MemoryAggregator()
    aggregator.process_all_exports()
    
    # Generate and display report
    report = aggregator.generate_report()
    print(report)
    
    # Save report to log
    log_file = GLOBAL_COMMANDS / "ops/logs/memory_aggregator.log"
    with open(log_file, 'a') as f:
        f.write(f"\n{datetime.now().isoformat()}\n{report}\n")
    
    print(f"📝 Full log: {log_file}")


if __name__ == "__main__":
    main()

