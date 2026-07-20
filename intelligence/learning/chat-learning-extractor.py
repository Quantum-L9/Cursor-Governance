#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "INT-LE-001"
component_name: "Chat Learning Extractor"
layer: "intelligence"
domain: "learning"
type: "extractor"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["re", "json", "datetime", "pathlib"]
integrates_with: ["INT-ML-001", "FND-LG-001", "EXE-API-001"]
api_endpoints: ["/api/v1/learning/extract", "/api/v1/learning/patterns"]
data_sources: ["cursor_chat_logs", "conversation_transcripts"]
outputs: ["intelligence/meta-learning/meta-learning-log.md", "foundation/logic/rule-registry.json"]

# === OPERATIONAL METADATA ===
execution_mode: "autonomous"
monitoring_required: true
logging_level: "info"
performance_tier: "real-time"

# === BUSINESS METADATA ===
purpose: "Automatically extract learning patterns from chat conversations for governance improvement"
summary: "Real-time conversation analysis that detects patterns and generates governance rules"
business_value: "Enables true recursive learning without manual intervention"
success_metrics: ["pattern_detection_accuracy >= 95%", "extraction_latency < 500ms", "rule_generation_rate >= 80%"]

# === INTEGRATION METADATA ===
constellation_origin: "New component - addresses missing chat extraction capability"
migration_notes: "Created to bridge the gap between conversations and governance rule generation"

# === TAGS & CLASSIFICATION ===
tags: ["chat", "learning", "extraction", "patterns", "automation", "recursive"]
keywords: ["chat", "conversation", "learning", "patterns", "extraction", "automation"]
related_components: ["INT-ML-001", "FND-LG-001", "EXE-MON-001"]
"""

import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class LearningPattern:
    """Detected learning pattern from conversation"""
    pattern_id: str
    timestamp: str
    context: str
    learning_summary: str
    implications: List[str]
    confidence_score: float
    rule_candidates: List[str]
    source_conversation: str

class ChatLearningExtractor:
    """
    Autonomous chat conversation analyzer that extracts learning patterns
    and generates governance rules without manual intervention.
    """
    
    def __init__(self, suite_root: Path = None):
        self.suite_root = suite_root or Path(__file__).parent.parent.parent
        self.meta_learning_log = self.suite_root / "intelligence/meta-learning/meta-learning-log.md"
        self.rule_registry = self.suite_root / "foundation/logic/rule-registry.json"
        self.patterns_cache = {}
        self.learning_patterns = [
            # Pattern definitions for automatic detection
            {
                "name": "validation_error_pattern",
                "regex": r"(\d+)\+?\s*(linting|validation|error)s?\s*(due to|caused by|from)\s*(.+)",
                "category": "error_prevention",
                "confidence": 0.9
            },
            {
                "name": "formatting_rule_pattern", 
                "regex": r"(missing|need|require|add)\s*(blank lines?|spacing|format|header)s?\s*(around|before|after)\s*(.+)",
                "category": "formatting_rules",
                "confidence": 0.85
            },
            {
                "name": "governance_failure_pattern",
                "regex": r"governance\s*(system|model)?\s*(not|isn't|doesn't)\s*(working|functional|operational|extracting)",
                "category": "system_improvement",
                "confidence": 0.95
            },
            {
                "name": "automation_request_pattern",
                "regex": r"(should|shouldn't|need to|automatically|auto)\s*(extract|detect|generate|update|learn)",
                "category": "automation_enhancement", 
                "confidence": 0.8
            },
            {
                "name": "user_correction_pattern",
                "regex": r"(you're wrong|that's not right|actually|correction|fix that|debug)",
                "category": "error_correction",
                "confidence": 0.9
            }
        ]
    
    def extract_from_conversation(self, conversation_text: str, conversation_id: str = None) -> List[LearningPattern]:
        """
        Extract learning patterns from a conversation transcript
        """
        patterns = []
        conversation_id = conversation_id or f"conv_{int(time.time())}"
        
        # Split into messages for context analysis
        messages = self._parse_conversation(conversation_text)
        
        for i, message in enumerate(messages):
            # Detect patterns in each message
            detected = self._detect_patterns_in_message(message, i, messages)
            patterns.extend(detected)
        
        # Generate learning patterns from detections
        learning_patterns = []
        for detection in patterns:
            learning_pattern = self._generate_learning_pattern(detection, conversation_id)
            if learning_pattern:
                learning_patterns.append(learning_pattern)
        
        return learning_patterns
    
    def _parse_conversation(self, conversation_text: str) -> List[Dict]:
        """Parse conversation into structured messages"""
        # Simple parsing - can be enhanced for specific chat formats
        messages = []
        lines = conversation_text.split('\n')
        current_message = {"role": "unknown", "content": "", "timestamp": datetime.now().isoformat()}
        
        for line in lines:
            # Detect role changes (User:, Assistant:, etc.)
            if re.match(r'^(User|Assistant|Human|AI):', line):
                if current_message["content"].strip():
                    messages.append(current_message.copy())
                current_message = {
                    "role": line.split(':')[0].lower(),
                    "content": line.split(':', 1)[1].strip() if ':' in line else "",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                current_message["content"] += " " + line.strip()
        
        if current_message["content"].strip():
            messages.append(current_message)
        
        return messages
    
    def _detect_patterns_in_message(self, message: Dict, index: int, all_messages: List[Dict]) -> List[Dict]:
        """Detect learning patterns in a single message"""
        detections = []
        content = message["content"]
        
        for pattern_def in self.learning_patterns:
            matches = re.finditer(pattern_def["regex"], content, re.IGNORECASE)
            for match in matches:
                detection = {
                    "pattern_name": pattern_def["name"],
                    "category": pattern_def["category"],
                    "confidence": pattern_def["confidence"],
                    "match_text": match.group(0),
                    "groups": match.groups(),
                    "message_index": index,
                    "message_role": message["role"],
                    "context_before": all_messages[max(0, index-1)]["content"][:200] if index > 0 else "",
                    "context_after": all_messages[min(len(all_messages)-1, index+1)]["content"][:200] if index < len(all_messages)-1 else ""
                }
                detections.append(detection)
        
        return detections
    
    def _generate_learning_pattern(self, detection: Dict, conversation_id: str) -> Optional[LearningPattern]:
        """Generate a structured learning pattern from a detection"""
        pattern_id = f"LP_{int(time.time())}_{detection['pattern_name']}"
        
        # Generate context summary
        context = f"Detected in conversation {conversation_id} from {detection['message_role']} message: '{detection['match_text']}'"
        
        # Generate learning summary based on pattern type
        learning_summary = self._generate_learning_summary(detection)
        
        # Generate implications
        implications = self._generate_implications(detection)
        
        # Generate rule candidates
        rule_candidates = self._generate_rule_candidates(detection)
        
        if learning_summary and implications:
            return LearningPattern(
                pattern_id=pattern_id,
                timestamp=datetime.now().isoformat(),
                context=context,
                learning_summary=learning_summary,
                implications=implications,
                confidence_score=detection["confidence"],
                rule_candidates=rule_candidates,
                source_conversation=conversation_id
            )
        
        return None
    
    def _generate_learning_summary(self, detection: Dict) -> str:
        """Generate learning summary based on detection type"""
        category = detection["category"]
        match_text = detection["match_text"]
        
        summaries = {
            "error_prevention": f"System should prevent errors like: {match_text}",
            "formatting_rules": f"Formatting requirement identified: {match_text}",
            "system_improvement": f"System capability gap detected: {match_text}",
            "automation_enhancement": f"Automation opportunity: {match_text}",
            "error_correction": f"User correction indicates system error: {match_text}"
        }
        
        return summaries.get(category, f"Learning pattern detected: {match_text}")
    
    def _generate_implications(self, detection: Dict) -> List[str]:
        """Generate implications based on detection"""
        category = detection["category"]
        
        implications_map = {
            "error_prevention": [
                "Update validation rules to catch this error type",
                "Add preventive checks to pre-commit validation",
                "Generate formal logic rule for enforcement"
            ],
            "formatting_rules": [
                "Update file generation templates",
                "Add formatting validation to governance validator",
                "Create automatic formatting correction rules"
            ],
            "system_improvement": [
                "Identify missing system components",
                "Implement required functionality",
                "Update system architecture to support capability"
            ],
            "automation_enhancement": [
                "Implement automatic processing for this task",
                "Remove manual intervention requirements",
                "Add real-time monitoring and response"
            ],
            "error_correction": [
                "Update system knowledge base",
                "Correct erroneous behavior patterns",
                "Implement validation to prevent recurrence"
            ]
        }
        
        return implications_map.get(category, ["General system improvement needed"])
    
    def _generate_rule_candidates(self, detection: Dict) -> List[str]:
        """Generate formal logic rule candidates"""
        category = detection["category"]
        
        rule_templates = {
            "error_prevention": "∀f. File(f) ∧ GovernanceFile(f) → ValidFormat(f)",
            "formatting_rules": "∀f. MarkdownFile(f) → ProperFormatting(f)",
            "system_improvement": "∀s. System(s) → HasRequiredCapabilities(s)",
            "automation_enhancement": "∀t. Task(t) ∧ Repetitive(t) → Automated(t)",
            "error_correction": "∀e. Error(e) ∧ Detected(e) → Prevented(e)"
        }
        
        return [rule_templates.get(category, "∀x. LearningPattern(x) → AppliedCorrectly(x)")]
    
    def update_meta_learning_log(self, patterns: List[LearningPattern]) -> bool:
        """Update the meta-learning log with new patterns"""
        try:
            # Read existing log
            if self.meta_learning_log.exists():
                with open(self.meta_learning_log, 'r') as f:
                    content = f.read()
            else:
                content = ""
            
            # Generate new entries
            new_entries = []
            for pattern in patterns:
                entry = self._format_meta_learning_entry(pattern)
                new_entries.append(entry)
            
            # Append to log
            if new_entries:
                timestamp = datetime.now().strftime("%Y-%m-%d")
                new_content = content + f"\n\n### {timestamp} – Automatic Learning Extraction\n\n"
                new_content += "\n\n".join(new_entries)
                
                with open(self.meta_learning_log, 'w') as f:
                    f.write(new_content)
                
                return True
                
        except Exception as e:
            print(f"Error updating meta-learning log: {e}")
            return False
        
        return False
    
    def _format_meta_learning_entry(self, pattern: LearningPattern) -> str:
        """Format a learning pattern as a meta-learning log entry"""
        entry = f"""#### {pattern.pattern_id} – {pattern.learning_summary}

**Context:**
{pattern.context}

**Summary of Learning:**
{pattern.learning_summary}

**Implications:**
{chr(10).join(f"- {imp}" for imp in pattern.implications)}

**Generated Rules:**
- Rule ID: {pattern.pattern_id}
- FOL: {pattern.rule_candidates[0] if pattern.rule_candidates else "TBD"}
- Integration: Automatic extraction from conversation
- Confidence: {pattern.confidence_score:.2f}

**Success Metrics:**
- Pattern detection accuracy >= 95%
- Rule application success >= 90%
- Error reduction measurable

**Related Components:**
- INT-LE-001 (Chat Learning Extractor)
- INT-ML-001 (Meta Learning Log)
- FND-LG-001 (DSL Compiler)"""

        return entry
    
    def process_current_conversation(self, conversation_text: str = None) -> List[LearningPattern]:
        """
        Process the current conversation for learning patterns
        This would be called automatically by the governance system
        """
        if not conversation_text:
            # In a real implementation, this would get the current chat context
            # For now, we'll use a placeholder
            conversation_text = "Placeholder for current conversation context"
        
        patterns = self.extract_from_conversation(conversation_text, "current_session")
        
        if patterns:
            success = self.update_meta_learning_log(patterns)
            if success:
                print(f"✅ Extracted {len(patterns)} learning patterns from conversation")
                for pattern in patterns:
                    print(f"   - {pattern.learning_summary} (confidence: {pattern.confidence_score:.2f})")
            else:
                print("❌ Failed to update meta-learning log")
        else:
            print("ℹ️ No learning patterns detected in current conversation")
        
        return patterns

def main():
    """Test the chat learning extractor"""
    extractor = ChatLearningExtractor()
    
    # Test with sample conversation
    sample_conversation = """
    User: you shouldn't need to update it manually it should get extracted from chat automatically
    
    Assistant: You're absolutely right! The governance system should be extracting these patterns automatically from our chat, not requiring manual memory updates. The fact that I had to manually create that memory entry means the automatic learning extraction isn't working as designed.
    
    User: debug the current governance - figure out why it's not working
    
    Assistant: The issue is that there's no chat extraction component in L9 Governance! The system has meta-learning log, reasoning snapshot generator, governance monitor, DSL compiler, but is missing the chat conversation analyzer/extractor.
    """
    
    patterns = extractor.extract_from_conversation(sample_conversation, "test_conversation")
    
    print(f"Detected {len(patterns)} learning patterns:")
    for pattern in patterns:
        print(f"- {pattern.learning_summary}")
        print(f"  Confidence: {pattern.confidence_score:.2f}")
        print(f"  Implications: {len(pattern.implications)} items")
        print()

if __name__ == "__main__":
    main()
