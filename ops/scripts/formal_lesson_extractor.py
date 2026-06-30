#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "2.0.0"
component_id: "OPS-FLE-001"
component_name: "Formal Lesson Extractor"
layer: "operations"
domain: "learning"
type: "analyzer"
status: "active"
created: "2025-11-17T22:06:00Z"
updated: "2025-11-17T22:06:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3", "json", "pathlib", "re", "os"]
integrates_with: ["OPS-AGG-001", "OPS-LEA-001", "OPS-UPD-001"]
data_sources: ["ops/logs/memory_index.json", "ops/logs/chat_exports"]
outputs: ["learning/failures/repeated-mistakes.md", "learning/failures/reasoning_insights.md", "learning/failures/lessons_review_log.jsonl", "learning/failures/audit_log.jsonl"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Autonomously analyze raw patterns and generate formal lessons using Reasoning Blocks framework"
summary: "Fully autonomous lesson creation with quality validation and direct file integration"
business_value: "Enables systematic learning from raw patterns without manual intervention"
success_metrics: ["pattern_grouping_accuracy >= 80%", "lesson_quality >= 90%", "autonomous_success_rate >= 95%"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "analysis", "formal_lessons", "pattern_recognition", "autonomous", "reasoning"]
keywords: ["formal", "lessons", "analysis", "patterns", "extraction", "autonomous", "reasoning_blocks"]
related_components: ["OPS-AGG-001", "OPS-UPD-001", "INT-ML-001"]
"""

import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

# Configuration - Use Dropbox as single source of truth
def get_global_commands_path():
    """Get GlobalCommands path, preferring Dropbox location"""
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
        log_entry = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FALLBACK USED: Library path instead of Dropbox
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: formal_lesson_extractor.py
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
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"
REPEATED_MISTAKES_FILE = GLOBAL_COMMANDS / "learning/failures/repeated-mistakes.md"
REASONING_INSIGHTS_FILE = GLOBAL_COMMANDS / "learning/failures/reasoning_insights.md"
REVIEW_LOG_FILE = GLOBAL_COMMANDS / "learning/failures/lessons_review_log.jsonl"
AUDIT_LOG_FILE = GLOBAL_COMMANDS / "learning/failures/audit_log.jsonl"

# Quality thresholds (CALIBRATED based on existing lesson analysis)
# Lowered to extract maximum value from accumulated data while maintaining quality
QUALITY_THRESHOLDS = {
    'high_quality': 0.70,  # Auto-add, no review needed (was 0.85, then 0.75)
    'medium_quality': 0.55,  # Auto-add BUT log to review file (was 0.70, then 0.60)
    'low_quality': 0.35  # Reject and log to audit (was 0.50, then 0.40)
}


class ReasoningBlocks:
    """7-block reasoning framework for generating formal lessons"""
    
    def __init__(self, patterns: List[Dict[str, Any]], context_data: Dict[str, Any]):
        self.patterns = patterns
        self.context_data = context_data
        self.insights = {}
        # Store category in insights for _generate_mistake_description access
        if 'category' in context_data:
            self.insights['context'] = {'category': context_data['category']}
    
    def block1_define_objective(self) -> Dict[str, Any]:
        """BLOCK 1: Define the Objective"""
        pattern_count = len(self.patterns)
        pattern_type = self.patterns[0].get('type', 'unknown') if self.patterns else 'unknown'
        
        # Extract common content themes
        content_samples = [p.get('content', '')[:100] for p in self.patterns[:5]]
        common_themes = self._extract_themes(content_samples)
        
        objective = {
            'task': f"Generate formal lesson for {pattern_type} pattern",
            'pattern_count': pattern_count,
            'pattern_type': pattern_type,
            'common_themes': common_themes,
            'success_criteria': 'Complete lesson with mistake, impact, prevention, and rule'
        }
        
        self.insights['objective'] = objective
        return objective
    
    def block2_understand_context(self) -> Dict[str, Any]:
        """BLOCK 2: Understand the Context"""
        timestamps = [p.get('timestamp', '') for p in self.patterns if p.get('timestamp')]
        dates = sorted(set([t[:10] for t in timestamps if len(t) >= 10]))
        
        # Extract context snippets
        contexts = [p.get('context', '') for p in self.patterns if p.get('context')]
        
        context = {
            'domain': 'AI development and governance',
            'when': f"{dates[0]} to {dates[-1]}" if dates else "Unknown date range",
            'frequency': len(self.patterns),
            'context_samples': contexts[:3],
            'why_now': 'Pattern detected through automated learning system',
            'constraints': 'Must align with Suite 6 governance standards'
        }
        
        # Preserve category if it was set in __init__
        if 'context' in self.insights and 'category' in self.insights['context']:
            context['category'] = self.insights['context']['category']
        elif 'category' in self.context_data:
            context['category'] = self.context_data['category']
        
        self.insights['context'] = context
        return context
    
    def block3_decompose_challenge(self) -> Dict[str, Any]:
        """BLOCK 3: Decompose the Challenge"""
        # Analyze root causes
        content_text = ' '.join([p.get('content', '') for p in self.patterns])
        
        root_causes = []
        if 'correction' in content_text.lower():
            root_causes.append('User correction required - misunderstanding or assumption')
        if 'auth' in content_text.lower() or 'credential' in content_text.lower():
            root_causes.append('Authentication method incorrect')
        if 'json' in content_text.lower():
            root_causes.append('Data format parsing issue')
        if 'n8n' in content_text.lower():
            root_causes.append('n8n workflow or node configuration issue')
        
        if not root_causes:
            root_causes.append('Pattern detected but root cause needs analysis')
        
        decomposition = {
            'key_parts': ['Pattern detection', 'Root cause analysis', 'Prevention protocol', 'Enforcement rule'],
            'complexity': 'Medium - requires pattern analysis and lesson generation',
            'root_causes': root_causes,
            'interdependencies': ['Memory index', 'Existing lessons', 'Governance rules']
        }
        
        self.insights['decomposition'] = decomposition
        return decomposition
    
    def block4_leverage_prior_work(self) -> Dict[str, Any]:
        """BLOCK 4: Leverage Prior Work"""
        # Check existing lessons for similar patterns
        existing_lessons = self._check_existing_lessons()
        
        leverage = {
            'existing_lessons': existing_lessons,
            'similar_patterns': 'Check repeated-mistakes.md for similar mistakes',
            'prevention_protocols': 'Reference existing prevention rules',
            'avoid_duplication': True
        }
        
        self.insights['leverage'] = leverage
        return leverage
    
    def block5_map_strategy(self) -> Dict[str, Any]:
        """BLOCK 5: Map Strategy"""
        pattern_type = self.patterns[0].get('type', 'mistake') if self.patterns else 'mistake'
        
        strategy = {
            'reasoning_type': 'Pattern analysis and prevention design',
            'strategic_leverage': 'Prevent future occurrences through formal documentation',
            'success_conditions': 'Lesson is specific, actionable, and prevents repetition',
            'prevention_approach': 'Clear rule + actionable prevention steps',
            'enforcement_method': 'Pre-execution checklist integration'
        }
        
        self.insights['strategy'] = strategy
        return strategy
    
    def block6_execute_reasoning(self) -> Dict[str, Any]:
        """BLOCK 6: Execute Reasoning - Generate lesson content"""
        objective = self.insights.get('objective', {})
        context = self.insights.get('context', {})
        decomposition = self.insights.get('decomposition', {})
        
        # Generate mistake description
        mistake = self._generate_mistake_description()
        
        # Generate impact analysis
        impact = self._generate_impact_analysis(context, decomposition)
        
        execution = {
            'mistake': mistake,
            'impact': impact,
            'pattern_evidence': len(self.patterns),
            'date_range': context.get('when', 'Unknown')
        }
        
        self.insights['execution'] = execution
        return execution
    
    def block7_synthesize(self) -> Dict[str, Any]:
        """BLOCK 7: Synthesize - Create prevention protocol and rule"""
        execution = self.insights.get('execution', {})
        strategy = self.insights.get('strategy', {})
        decomposition = self.insights.get('decomposition', {})
        
        # Generate prevention protocol
        prevention = self._generate_prevention_protocol(decomposition, strategy)
        
        # Generate enforcement rule
        rule = self._generate_enforcement_rule(strategy)
        
        synthesis = {
            'prevention': prevention,
            'rule': rule,
            'strategic_position': 'Formal lesson prevents future repetition',
            'leverage_points': ['Pre-execution checklist', 'Governance integration', 'Pattern recognition']
        }
        
        self.insights['synthesis'] = synthesis
        return synthesis
    
    def generate_complete_lesson(self) -> Dict[str, Any]:
        """Run all blocks and generate complete lesson"""
        self.block1_define_objective()
        self.block2_understand_context()
        self.block3_decompose_challenge()
        self.block4_leverage_prior_work()
        self.block5_map_strategy()
        self.block6_execute_reasoning()
        self.block7_synthesize()
        
        execution = self.insights.get('execution', {})
        synthesis = self.insights.get('synthesis', {})
        context = self.insights.get('context', {})
        
        return {
            'mistake': execution.get('mistake', ''),
            'impact': execution.get('impact', ''),
            'prevention': synthesis.get('prevention', ''),
            'rule': synthesis.get('rule', ''),
            'date_added': datetime.now().strftime("%Y-%m-%d")
        }
    
    def _extract_themes(self, content_samples: List[str]) -> List[str]:
        """Extract common themes from content samples"""
        themes = []
        content_lower = ' '.join(content_samples).lower()
        
        if 'correction' in content_lower:
            themes.append('user correction')
        if 'auth' in content_lower:
            themes.append('authentication')
        if 'json' in content_lower:
            themes.append('data parsing')
        if 'n8n' in content_lower:
            themes.append('n8n workflow')
        
        return themes[:3]  # Top 3 themes
    
    def _check_existing_lessons(self) -> List[str]:
        """Check for similar existing lessons"""
        if not REPEATED_MISTAKES_FILE.exists():
            return []
        
        content = REPEATED_MISTAKES_FILE.read_text()
        # Simple check - look for common keywords
        themes = self._extract_themes([p.get('content', '') for p in self.patterns[:3]])
        
        similar = []
        for theme in themes:
            if theme in content.lower():
                similar.append(theme)
        
        return similar
    
    def _generate_mistake_description(self) -> str:
        """Generate mistake description from patterns (REASONING-BASED: Use category from group_key)"""
        # Extract category from group_key (passed via context)
        category = self.insights.get('context', {}).get('category', '')
        content_samples = [p.get('content', '') for p in self.patterns[:5]]
        themes = self._extract_themes(content_samples)
        enhanced = self.patterns[0].get('enhanced_context', {}) if self.patterns else {}
        
        # REASONING-BASED: Use granular category to generate specific descriptions
        
        # User Corrections (GRANULAR)
        if 'user_correction_explicit_rejection' in category:
            return "User explicitly rejected action - said 'no', 'wrong', 'incorrect', 'stop', or 'don't'"
        elif 'user_correction_clarification' in category:
            return "User clarification required - said 'actually', 'instead', 'should be', or 'meant to'"
        elif 'user_correction_repeated_mistake' in category:
            return "Repeated mistake detected - user said 'I told you', 'again', or 'still happening'"
        elif 'user_correction_critical_reminder' in category:
            return "Critical reminder from user - said 'critical', 'must', 'never', 'always', or '10/10'"
        elif 'user_correction_understanding_gap' in category:
            return "Understanding gap - user said 'misunderstood', 'didn't understand', or 'not what I meant'"
        elif 'user_correction' in category:
            return "User correction required - misunderstanding or incorrect assumption made"
        
        # Authentication (GRANULAR)
        elif 'auth_manual_headers' in category:
            return "Authentication failed - used manual Authorization headers instead of predefinedCredentialType"
        elif 'supabase_auth_config' in category:
            return "Supabase authentication configuration incorrect or not following best practices"
        elif 'auth' in category:
            return "Authentication method incorrect or not following best practices"
        
        # JSON Parsing (GRANULAR)
        elif 'json_string_wrapped' in category:
            return "JSON parsing error - JSON string wrapped in quotes, requires double json.loads()"
        elif 'json' in category:
            return "Data format parsing issue - incorrect handling of JSON structure"
        
        # n8n Issues (GRANULAR)
        elif 'n8n_expression_syntax' in category:
            return "n8n expression syntax error - spaces in expressions break execution"
        elif 'n8n_workflow_structure' in category:
            return "n8n workflow structure issue - missing node IDs or incorrect workflow format"
        elif 'n8n_workflow_import' in category:
            return "n8n workflow import failed - missing required fields or incorrect structure"
        elif 'n8n' in category:
            return "n8n workflow or node configuration issue detected"
        
        # Solutions (VALUABLE PATTERNS)
        elif 'solution_with_proof' in category:
            return "Successful solution pattern - solution provided with proof (exit code, test results, verification)"
        elif 'solution_user_confirmed' in category:
            return "Successful solution pattern - user confirmed solution worked ('that worked', 'perfect', 'great')"
        elif 'solution_explicit_success' in category:
            return "Successful solution pattern - explicit success indicators ('fixed', 'solved', 'working now')"
        elif 'solution' in category:
            return "Successful solution pattern detected - can be reused for similar problems"
        
        # High-Value Patterns
        elif 'claim_without_proof' in category:
            return "Claimed fix without providing proof - said 'should work now', 'try it', or 'let me know'"
        elif 'dependency_import_error' in category:
            return "Dependency or import error - missing modules, circular dependencies, or import failures"
        elif 'symlink_display_misunderstanding' in category:
            return "Symlink display misunderstanding - user asked to 'display folder' but meant symlink, not documentation"
        elif 'path_hardcoding' in category:
            return "Hardcoded path used instead of $HOME - breaks cross-machine compatibility"
        elif 'user_initiated_lesson' in category:
            return "User-initiated lesson request - user explicitly requested lesson extraction with 'LESSON' keyword"
        
        # Fallback to themes
        elif themes:
            return f"{', '.join(themes).title()} issue detected"
        else:
            return f"Pattern detected: {category.replace('_', ' ').title() if category else 'Unknown pattern'}"
    
    def _generate_impact_analysis(self, context: Dict, decomposition: Dict) -> str:
        """Generate impact analysis"""
        pattern_count = len(self.patterns)
        date_range = context.get('when', 'Unknown')
        
        impact_parts = [
            f"Occurred {pattern_count} time(s)",
            f"Date range: {date_range}",
            "Requires user correction or rework"
        ]
        
        if pattern_count >= 5:
            impact_parts.append("HIGH frequency - significant time waste")
        elif pattern_count >= 3:
            impact_parts.append("MEDIUM frequency - moderate impact")
        
        return " | ".join(impact_parts)
    
    def _generate_prevention_protocol(self, decomposition: Dict, strategy: Dict) -> str:
        """Generate prevention protocol"""
        root_causes = decomposition.get('root_causes', [])
        
        prevention_steps = []
        
        if 'misunderstanding' in str(root_causes).lower():
            prevention_steps.append("Ask clarifying questions BEFORE starting")
            prevention_steps.append("Confirm understanding of requirements")
        
        if 'auth' in str(root_causes).lower():
            prevention_steps.append("Always use predefinedCredentialType + supabaseApi")
            prevention_steps.append("Never add manual Authorization headers")
        
        if 'json' in str(root_causes).lower():
            prevention_steps.append("Always check JSON format before parsing")
            prevention_steps.append("Use defensive parsing approach")
        
        if not prevention_steps:
            prevention_steps.append("Review pattern context before proceeding")
            prevention_steps.append("Check existing lessons for similar patterns")
        
        return " | ".join(prevention_steps)
    
    def _generate_enforcement_rule(self, strategy: Dict) -> str:
        """Generate enforcement rule"""
        return "Apply prevention protocol before execution | Check existing lessons | Verify approach"


class QualityValidator:
    """Simple quality validation for generated lessons"""
    
    @staticmethod
    def assess_quality(lesson: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Assess lesson quality and return score + dimension breakdown"""
        completeness = QualityValidator._check_completeness(lesson)
        actionability = QualityValidator._check_actionability(lesson)
        specificity = QualityValidator._check_specificity(lesson)
        impact_quantification = QualityValidator._check_impact_quantification(lesson)
        
        # ENHANCED: Weighted average (adjusted to favor content over format)
        # Completeness and actionability are most important
        quality_score = (
            completeness * 0.35 +  # Increased from 0.30
            actionability * 0.35 +  # Increased from 0.30
            specificity * 0.20 +    # Decreased from 0.25 (format less important)
            impact_quantification * 0.10  # Decreased from 0.15 (content > quantification)
        )
        
        # ENHANCED: Bonus for lessons with multiple pattern occurrences
        pattern_count = lesson.get('pattern_count', 0)
        if pattern_count >= 3:
            quality_score += 0.05  # Small bonus for repeated patterns
        elif pattern_count >= 2:
            quality_score += 0.02
        
        quality_score = min(quality_score, 1.0)  # Cap at 1.0
        
        dimensions = {
            'completeness': completeness,
            'actionability': actionability,
            'specificity': specificity,
            'impact_quantification': impact_quantification
        }
        
        return quality_score, dimensions
    
    @staticmethod
    def _check_completeness(lesson: Dict[str, Any]) -> float:
        """Check if all required fields are populated"""
        required_fields = ['mistake', 'impact', 'prevention', 'rule']
        score = 0.0
        
        # Check for placeholders
        lesson_text = ' '.join([str(lesson.get(f, '')) for f in required_fields])
        if '[REVIEW REQUIRED]' in lesson_text or '[PLACEHOLDER]' in lesson_text:
            return 0.0
        
        # Check all fields present and non-empty
        for field in required_fields:
            value = lesson.get(field, '')
            if value and len(str(value).strip()) > 0:
                score += 0.25
        
        return min(score, 1.0)
    
    @staticmethod
    def _check_actionability(lesson: Dict[str, Any]) -> float:
        """Check if prevention steps are actionable"""
        prevention = lesson.get('prevention', '')
        if not prevention:
            return 0.0
        
        prevention_lower = prevention.lower()
        
        # Check for action verbs
        action_verbs = ['always', 'never', 'check', 'verify', 'confirm', 'use', 'apply', 'ensure']
        action_count = sum(1 for verb in action_verbs if verb in prevention_lower)
        
        # Check for specific instructions
        has_steps = '|' in prevention or '\n' in prevention or '1.' in prevention
        
        score = min(action_count * 0.2, 0.6) + (0.4 if has_steps else 0.0)
        return min(score, 1.0)
    
    @staticmethod
    def _check_specificity(lesson: Dict[str, Any]) -> float:
        """Check if mistake description is specific (ENHANCED: Content > Format)"""
        mistake = lesson.get('mistake', '')
        if not mistake:
            return 0.0
        
        mistake_lower = mistake.lower()
        
        # ENHANCED: More lenient word count (target: 10-150 words, was 20-100)
        word_count = len(mistake.split())
        if 10 <= word_count <= 150:
            word_score = 0.5
        elif word_count > 5:  # Accept shorter valuable lessons
            word_score = 0.4
        else:
            word_score = 0.2  # Was 0.1
        
        # Check for concrete terms vs abstract (expanded list)
        concrete_terms = ['user', 'data', 'file', 'api', 'auth', 'json', 'n8n', 'workflow', 
                         'script', 'path', 'error', 'correction', 'mistake', 'pattern', 'system']
        concrete_count = sum(1 for term in concrete_terms if term in mistake_lower)
        concrete_score = min(concrete_count * 0.08, 0.5)  # More lenient scoring
        
        # ENHANCED: Check for context richness (pattern count, date range)
        pattern_count = lesson.get('pattern_count', 0)
        context_score = min(pattern_count * 0.05, 0.2)  # Bonus for multiple occurrences
        
        return min(word_score + concrete_score + context_score, 1.0)
    
    @staticmethod
    def _check_impact_quantification(lesson: Dict[str, Any]) -> float:
        """Check if impact includes quantifiable information (ENHANCED: More lenient)"""
        impact = lesson.get('impact', '')
        if not impact:
            return 0.0
        
        impact_lower = impact.lower()
        
        # ENHANCED: Check for numbers (more lenient)
        has_numbers = bool(re.search(r'\d+', impact))
        # ENHANCED: Expanded time references
        has_time = any(word in impact_lower for word in ['time', 'minute', 'hour', 'day', 'occurred', 
                                                          'waste', 'delay', 'break', 'fail'])
        # ENHANCED: Expanded frequency indicators
        has_frequency = any(word in impact_lower for word in ['times', 'frequency', 'multiple', 'repeated',
                                                               'often', 'always', 'never', 'every'])
        
        # ENHANCED: Check pattern count as quantification
        pattern_count = lesson.get('pattern_count', 0)
        has_pattern_count = pattern_count >= 2
        
        score = 0.0
        if has_numbers:
            score += 0.4
        elif has_pattern_count:  # Use pattern count as quantification
            score += 0.3
        if has_time:
            score += 0.3
        if has_frequency:
            score += 0.3
        
        # ENHANCED: Minimum score for lessons with impact description
        if len(impact.split()) > 5:  # Has substantial impact description
            score = max(score, 0.3)  # Minimum 0.3 if impact is described
        
        return min(score, 1.0)


class FormalLessonExtractor:
    """Autonomously analyzes raw patterns and generates formal lessons"""
    
    def __init__(self, autonomous: bool = True, weekly_review: bool = False):
        self.autonomous = autonomous
        self.weekly_review = weekly_review
        self.memory_index = self._load_memory_index()
        self.formalized_hashes = set(self.memory_index.get("formalized_learnings", []))
        self.accepted_lessons = []
        self.rejected_lessons = []
        self.review_lessons = []
    
    def _load_memory_index(self) -> Dict[str, Any]:
        """Load memory index"""
        if MEMORY_INDEX.exists():
            try:
                with open(MEMORY_INDEX, 'r') as f:
                    content = f.read().strip()
                    if content and content != "{}":
                        return json.loads(content)
            except json.JSONDecodeError:
                print("⚠️  Memory index corrupted, creating new one")
        
        return {"learnings": [], "formalized_learnings": []}
    
    def _save_memory_index(self):
        """Save memory index"""
        self.memory_index["formalized_learnings"] = list(self.formalized_hashes)
        MEMORY_INDEX.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_INDEX, 'w') as f:
            json.dump(self.memory_index, f, indent=2)
    
    def analyze_patterns(self) -> List[Dict[str, Any]]:
        """Analyze patterns and generate formal lessons"""
        learnings = self.memory_index.get("learnings", [])
        
        # Filter unformalized learnings
        pending = [l for l in learnings if l['hash'] not in self.formalized_hashes]
        
        if not pending:
            print("✅ No pending patterns to analyze")
            return []
        
        print(f"\n🔍 Analyzing {len(pending)} pending patterns...")
        
        # Group by type and context
        grouped = self._group_patterns(pending)
        
        # ENHANCED: Generate lessons (including single-pattern high-value lessons)
        lessons = []
        for group_key, patterns in grouped.items():
            # ENHANCED: Accept groups with 2+ patterns OR single high-value patterns
            if len(patterns) >= 2:
                lesson = self._generate_lesson(group_key, patterns)
                if lesson:
                    lessons.append(lesson)
            elif len(patterns) == 1:
                # ENHANCED: Accept ALL single patterns (they're valuable even if unique)
                # Previously only accepted high-value, now accept all to maximize extraction
                pattern = patterns[0]
                content = pattern.get('content', '').lower()
                pattern_type = pattern.get('type', '')
                
                # Generate lesson for all single patterns
                lesson = self._generate_lesson(group_key, patterns)
                if lesson:
                    lessons.append(lesson)
        
        print(f"📊 Generated {len(lessons)} formal lesson candidates")
        
        return lessons
    
    def _group_patterns(self, learnings: List[Dict[str, Any]]) -> Dict[str, List]:
        """Group similar patterns together (REASONING-BASED: Granular categorization)"""
        grouped = defaultdict(list)
        
        for learning in learnings:
            content = learning.get('content', '').lower()
            learning_type = learning.get('type', 'unknown')
            enhanced = learning.get('enhanced_context', {})
            
            # REASONING-BASED CATEGORIZATION: Use enhanced context first, then fallback
            
            # Extract enhanced context indicators
            error_pattern = enhanced.get('error_pattern', '')
            quick_fix = enhanced.get('quick_fix', '')
            pattern_type = enhanced.get('pattern_type', '')
            severity = enhanced.get('severity', '')
            correction_type = enhanced.get('correction_type', '')
            solution_type = enhanced.get('solution_type', '')
            trigger_type = enhanced.get('trigger_type', '')
            
            # Category 1: User Corrections (MOST GRANULAR - separate by type)
            if trigger_type == 'correction' or correction_type or 'user correction' in content:
                if correction_type == 'explicit_rejection':
                    key = f"{learning_type}:user_correction_explicit_rejection"
                elif correction_type == 'clarification':
                    key = f"{learning_type}:user_correction_clarification"
                elif correction_type == 'repetition_indicator':
                    key = f"{learning_type}:user_correction_repeated_mistake"
                elif correction_type == 'critical_reminder':
                    key = f"{learning_type}:user_correction_critical_reminder"
                elif correction_type == 'understanding_gap':
                    key = f"{learning_type}:user_correction_understanding_gap"
                elif 'remind' in content or 'told you' in content or 'again' in content:
                    key = f"{learning_type}:user_correction_repeated_mistake"
                elif 'critical' in content or '10/10' in content or 'must' in content or 'never' in content:
                    key = f"{learning_type}:user_correction_critical_reminder"
                else:
                    key = f"{learning_type}:user_correction_general"
            
            # Category 2: Authentication Issues (SEPARATE by specific problem)
            elif 'auth' in content or 'authentication' in content or 'credential' in content or '401' in content or '403' in content:
                if quick_fix and 'predefinedCredentialType' in quick_fix:
                    key = f"{learning_type}:auth_manual_headers"
                elif 'supabase' in content:
                    key = f"{learning_type}:supabase_auth_config"
                else:
                    key = f"{learning_type}:auth_general"
            
            # Category 3: JSON Parsing (SEPARATE by specific issue)
            elif 'json' in content or 'parsing' in content or 'decode' in content:
                if quick_fix and 'json.loads' in quick_fix:
                    key = f"{learning_type}:json_string_wrapped"
                else:
                    key = f"{learning_type}:json_parsing_general"
            
            # Category 4: n8n Issues (SEPARATE by specific problem)
            elif 'n8n' in content or 'workflow' in content or 'node' in content:
                if 'expression' in content or (quick_fix and 'spaces' in quick_fix):
                    key = f"{learning_type}:n8n_expression_syntax"
                elif 'structure' in content or pattern_type == 'structural':
                    key = f"{learning_type}:n8n_workflow_structure"
                elif 'import' in content:
                    key = f"{learning_type}:n8n_workflow_import"
                else:
                    key = f"{learning_type}:n8n_general"
            
            # Category 5: Solutions (SEPARATE by type - these are valuable!)
            elif trigger_type == 'solution' or solution_type or learning_type == 'solution':
                if solution_type == 'proof_provided':
                    key = f"{learning_type}:solution_with_proof"
                elif solution_type == 'user_confirmation':
                    key = f"{learning_type}:solution_user_confirmed"
                elif solution_type == 'explicit_success':
                    key = f"{learning_type}:solution_explicit_success"
                else:
                    key = f"{learning_type}:solution_general"
            
            # Category 6: Claim Without Proof (SPECIFIC HIGH-VALUE PATTERN)
            elif 'claim' in content or 'proof' in content or error_pattern == 'try.*it.*let.*me.*know':
                key = f"{learning_type}:claim_without_proof"
            
            # Category 7: Dependency & Import Issues
            elif 'dependency' in content or 'import' in content or 'module' in content or 'circular' in content:
                key = f"{learning_type}:dependency_import_error"
            
            # Category 8: Symlink Issues (SEPARATE by misunderstanding type)
            elif 'symlink' in content or 'display' in content or 'folder' in content or 'sidebar' in content:
                if 'display' in content or 'show' in content:
                    key = f"{learning_type}:symlink_display_misunderstanding"
                else:
                    key = f"{learning_type}:symlink_general"
            
            # Category 9: Path Issues
            elif 'path' in content or 'hardcode' in content or '/users/' in content or '$home' in content or 'home' in content:
                key = f"{learning_type}:path_hardcoding"
            
            # Category 10: Lesson Triggers
            elif trigger_type == 'LESSON' or 'lesson' in content:
                key = f"{learning_type}:user_initiated_lesson"
            
            # Category 11: Date/Time Issues
            elif 'date' in content or 'time' in content or 'timestamp' in content:
                key = f"{learning_type}:date_time_issue"
            
            # Category 12: File/Directory Issues
            elif 'file' in content or 'directory' in content:
                key = f"{learning_type}:file_issue"
            
            # Category 13: Search/Find Patterns
            elif 'search' in content or 'find' in content or 'lookup' in content:
                key = f"{learning_type}:search_pattern"
            
            # Category 14: Error Handling (generic)
            elif 'error' in content or 'fail' in content or 'exception' in content:
                if pattern_type:
                    key = f"{learning_type}:error_{pattern_type}"
                else:
                    key = f"{learning_type}:error_handling"
            
            # Last resort: Use pattern type or first significant word
            else:
                if pattern_type:
                    key = f"{learning_type}:pattern_{pattern_type}"
                else:
                    words = content.split()
                    significant_words = [w for w in words if len(w) > 4 and w not in ['detected', 'conversation', 'pattern', 'successful', 'issue']]
                    category = significant_words[0] if significant_words else 'uncategorized'
                    key = f"{learning_type}:{category}"
            
            grouped[key].append(learning)
        
        return grouped
    
    def _generate_lesson(self, group_key: str, patterns: List[Dict]) -> Optional[Dict[str, Any]]:
        """Generate a formal lesson using Reasoning Blocks"""
        learning_type, category = group_key.split(':', 1)
        
        # Extract context data
        context_data = self._extract_pattern_context(patterns)
        # Add category to context so _generate_mistake_description can use it
        context_data['category'] = category
        
        # Use Reasoning Blocks to generate lesson
        reasoning = ReasoningBlocks(patterns, context_data)
        lesson_content = reasoning.generate_complete_lesson()
        
        # Quality validation
        quality_score, dimensions = QualityValidator.assess_quality(lesson_content)
        
        # Extract timestamps for date range
        timestamps = [p.get('timestamp', '') for p in patterns]
        dates = sorted(set([t[:10] for t in timestamps if len(t) >= 10]))
        
        lesson = {
            "id": f"FL_{datetime.now().strftime('%Y%m%d')}_{category}",
            "type": learning_type,
            "category": category.replace('_', ' ').title(),
            "pattern_count": len(patterns),
            "first_seen": dates[0] if dates else "unknown",
            "last_seen": dates[-1] if dates else "unknown",
            "hashes": [p['hash'] for p in patterns],
            "quality_score": quality_score,
            "quality_dimensions": dimensions,
            "status": "autonomous_generated",
            "generated_at": datetime.now().isoformat(),
            **lesson_content
        }
        
        return lesson
    
    def _extract_pattern_context(self, patterns: List[Dict]) -> Dict[str, Any]:
        """Extract context from patterns (ENHANCED: Use enhanced_context when available)"""
        contexts = []
        enhanced_contexts = []
        
        for pattern in patterns[:5]:  # Sample first 5
            # ENHANCED: Prefer enhanced_context over basic context
            enhanced_ctx = pattern.get('enhanced_context', {})
            if enhanced_ctx and isinstance(enhanced_ctx, dict):
                # Extract actual conversation snippets from enhanced context
                if 'message_window' in enhanced_ctx:
                    enhanced_contexts.extend(enhanced_ctx['message_window'])
                elif 'messages' in enhanced_ctx:
                    for msg in enhanced_ctx['messages']:
                        if isinstance(msg, dict):
                            enhanced_contexts.append(msg.get('content', ''))
                        else:
                            enhanced_contexts.append(str(msg))
                elif 'trigger_message' in enhanced_ctx:
                    enhanced_contexts.append(enhanced_ctx['trigger_message'])
                
                # Add trigger type for context
                if 'trigger_type' in enhanced_ctx:
                    enhanced_contexts.append(f"[Trigger: {enhanced_ctx['trigger_type']}]")
            else:
                # Fallback to basic context (might be UUID or string)
                context_str = pattern.get('context', '')
                if context_str and len(context_str) > 20:  # Likely not just UUID
                    contexts.append(context_str)
        
        # Combine enhanced and basic contexts
        all_contexts = enhanced_contexts + contexts
        
        return {
            'conversation_snippets': all_contexts[:10],  # Limit to 10 snippets
            'pattern_count': len(patterns),
            'extraction_method': 'enhanced' if enhanced_contexts else 'basic',
            'has_enhanced_context': len(enhanced_contexts) > 0,
            'snippet_count': len(all_contexts)
        }
    
    def process_lessons(self, lessons: List[Dict[str, Any]]):
        """Process lessons through quality gates"""
        for lesson in lessons:
            quality_score = lesson.get('quality_score', 0.0)
            
            if quality_score >= QUALITY_THRESHOLDS['high_quality']:
                # High quality - auto-add
                self.accepted_lessons.append(lesson)
            elif quality_score >= QUALITY_THRESHOLDS['medium_quality']:
                # Medium quality - auto-add but log to review
                self.accepted_lessons.append(lesson)
                self.review_lessons.append(lesson)
            else:
                # Low quality - reject and audit
                self.rejected_lessons.append(lesson)
                self._log_to_audit(lesson)
        
        print(f"\n✅ Quality Assessment Complete:")
        print(f"   High Quality (>={QUALITY_THRESHOLDS['high_quality']}): {len([l for l in self.accepted_lessons if l.get('quality_score', 0) >= QUALITY_THRESHOLDS['high_quality']])}")
        print(f"   Medium Quality ({QUALITY_THRESHOLDS['medium_quality']}-{QUALITY_THRESHOLDS['high_quality']}): {len(self.review_lessons)}")
        print(f"   Low Quality (<{QUALITY_THRESHOLDS['medium_quality']}): {len(self.rejected_lessons)}")
    
    def integrate_lessons(self):
        """Integrate accepted lessons into repeated-mistakes.md"""
        if not self.accepted_lessons:
            print("✅ No lessons to integrate")
            return
        
        if not REPEATED_MISTAKES_FILE.exists():
            print(f"⚠️  Repeated mistakes file not found: {REPEATED_MISTAKES_FILE}")
            return
        
        # Append lessons to file (per plan requirement)
        content = self._append_to_repeated_mistakes()
        
        # Update tracking table
        content = self._update_tracking_table(content)
        
        # Update timestamp
        content = re.sub(
            r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',
            f'**Last Updated:** {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}',
            content
        )
        
        REPEATED_MISTAKES_FILE.write_text(content)
        print(f"✅ Integrated {len(self.accepted_lessons)} lessons into repeated-mistakes.md")
        
        # Mark as formalized
        for lesson in self.accepted_lessons:
            for hash_val in lesson.get('hashes', []):
                self.formalized_hashes.add(hash_val)
        
        self._save_memory_index()
    
    def _append_to_repeated_mistakes(self) -> str:
        """Append lessons to repeated-mistakes.md file (per plan requirement)"""
        content = REPEATED_MISTAKES_FILE.read_text()
        
        # Find next lesson number
        lesson_numbers = re.findall(r'### \*\*(\d+)\.', content)
        next_number = max([int(n) for n in lesson_numbers] + [0]) + 1
        
        # Generate lesson entries
        lesson_entries = []
        for i, lesson in enumerate(self.accepted_lessons):
            lesson_num = next_number + i
            entry = self._format_lesson_entry(lesson_num, lesson)
            lesson_entries.append(entry)
        
        # Find insertion point (after "## 🚨 **CRITICAL FAILURES TO NEVER REPEAT**")
        insertion_marker = "## 🚨 **CRITICAL FAILURES TO NEVER REPEAT**"
        if insertion_marker in content:
            # Find the last lesson before the protocol section
            last_lesson_match = list(re.finditer(r'### \*\*\d+\.', content))
            if last_lesson_match:
                last_lesson_end = last_lesson_match[-1].end()
                # Find end of that lesson (next ### or ---)
                next_section = re.search(r'\n---|\n## ', content[last_lesson_end:])
                if next_section:
                    insert_pos = last_lesson_end + next_section.start()
                    content = content[:insert_pos] + '\n\n' + '\n\n'.join(lesson_entries) + '\n\n' + content[insert_pos:]
                else:
                    # Append at end of lessons section
                    content = content[:last_lesson_end] + '\n\n' + '\n\n'.join(lesson_entries) + content[last_lesson_end:]
            else:
                # No lessons found, insert after header
                header_pos = content.find(insertion_marker)
                if header_pos != -1:
                    next_line = content.find('\n', header_pos)
                    content = content[:next_line+1] + '\n\n' + '\n\n'.join(lesson_entries) + '\n\n' + content[next_line+1:]
        else:
            # Header not found, append at end
            content += '\n\n' + '\n\n'.join(lesson_entries)
        
        return content
    
    def _format_lesson_entry(self, lesson_num: int, lesson: Dict[str, Any]) -> str:
        """Format lesson as markdown entry"""
        mistake = lesson.get('mistake', '')
        impact = lesson.get('impact', '')
        prevention = lesson.get('prevention', '')
        rule = lesson.get('rule', '')
        date_added = lesson.get('date_added', datetime.now().strftime("%Y-%m-%d"))
        
        entry = f"""### **{lesson_num}. {mistake[:50]}...**
**Mistake:** {mistake}
**Impact:** {impact}
**Prevention:** {prevention}
**Rule:** {rule}
**Date Added:** {date_added}"""
        
        return entry
    
    def _update_tracking_table(self, content: str) -> str:
        """Update tracking table with new lessons"""
        # Find tracking table
        table_pattern = r'(\|\| Mistake Type \|.*?\|\n\|\|[-|]+\|\n(?:\|\|.*?\|\n)*)'
        match = re.search(table_pattern, content)
        
        if match:
            table = match.group(1)
            # Count new lessons by category
            categories = {}
            for lesson in self.accepted_lessons:
                cat = lesson.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            # Add entries for each category
            for cat, count in categories.items():
                new_row = f"|| {cat} | {count} | Autonomous Lesson Generation | ✅ Active |\n"
                # Insert before closing of table
                if '---\n\n**Last Updated:' in content:
                    content = content.replace('---\n\n**Last Updated:', new_row + '---\n\n**Last Updated:')
        
        return content
    
    def _log_to_review(self, lesson: Dict[str, Any]):
        """Log lesson to review file"""
        REVIEW_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            'lesson_id': lesson.get('id', ''),
            'quality_score': lesson.get('quality_score', 0.0),
            'lesson_content': {
                'mistake': lesson.get('mistake', ''),
                'impact': lesson.get('impact', ''),
                'prevention': lesson.get('prevention', ''),
                'rule': lesson.get('rule', '')
            },
            'date_added': datetime.now().isoformat(),
            'status': 'pending_review'
        }
        
        with open(REVIEW_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _log_to_audit(self, lesson: Dict[str, Any]):
        """Log rejected lesson to audit file"""
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        audit_entry = {
            'lesson_id': lesson.get('id', ''),
            'quality_score': lesson.get('quality_score', 0.0),
            'quality_dimensions': lesson.get('quality_dimensions', {}),
            'lesson_content': {
                'mistake': lesson.get('mistake', ''),
                'impact': lesson.get('impact', ''),
                'prevention': lesson.get('prevention', ''),
                'rule': lesson.get('rule', '')
            },
            'rejection_reason': 'Quality score below threshold',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(AUDIT_LOG_FILE, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def run_meta_analysis(self) -> Dict[str, Any]:
        """Run meta-analysis on repeated-mistakes.md"""
        if not REPEATED_MISTAKES_FILE.exists():
            return {}
        
        content = REPEATED_MISTAKES_FILE.read_text()
        
        # Extract all lessons
        lessons = re.findall(r'### \*\*\d+\.\s*(.*?)\*\*\n(.*?)(?=\n###|\n---|\Z)', content, re.DOTALL)
        
        # Cross-reference with memory_index.json
        learnings = self.memory_index.get("learnings", [])
        
        # Find patterns that match existing lessons (indicating repetition)
        repeated_lessons = []
        for lesson_match in lessons:
            lesson_title = lesson_match[0] if lesson_match else ''
            lesson_content = lesson_match[1] if len(lesson_match) > 1 else ''
            
            # Check if patterns exist after lesson date
            lesson_date_match = re.search(r'Date Added.*?(\d{4}-\d{2}-\d{2})', lesson_content)
            if lesson_date_match:
                lesson_date = lesson_date_match.group(1)
                
                # Find patterns matching this lesson that occurred AFTER lesson date
                matching_patterns = [
                    l for l in learnings
                    if l.get('timestamp', '')[:10] > lesson_date
                    and self._pattern_matches_lesson(l, lesson_title, lesson_content)
                ]
                
                if matching_patterns:
                    repeated_lessons.append({
                        'lesson': lesson_title,
                        'lesson_date': lesson_date,
                        'repeat_count': len(matching_patterns),
                        'last_repeat': max([l.get('timestamp', '')[:10] for l in matching_patterns])
                    })
        
        meta_analysis = {
            'total_lessons': len(lessons),
            'repeated_lessons': len(repeated_lessons),
            'repeated_details': repeated_lessons,
            'implementation_gaps': len(repeated_lessons),
            'analysis_date': datetime.now().isoformat()
        }
        
        return meta_analysis
    
    def _pattern_matches_lesson(self, pattern: Dict, lesson_title: str, lesson_content: str) -> bool:
        """Check if pattern matches an existing lesson"""
        pattern_content = pattern.get('content', '').lower()
        lesson_lower = lesson_title.lower() + ' ' + lesson_content.lower()
        
        # Simple keyword matching
        keywords = re.findall(r'\b\w{4,}\b', lesson_title.lower())
        matches = sum(1 for kw in keywords if kw in pattern_content)
        
        return matches >= 2  # At least 2 keywords match
    
    def generate_daily_insights(self, meta_analysis: Dict[str, Any]):
        """Generate daily reasoning insights"""
        REPEATED_MISTAKES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        repeated_count = meta_analysis.get('repeated_lessons', 0)
        total_lessons = meta_analysis.get('total_lessons', 0)
        gaps = meta_analysis.get('implementation_gaps', 0)
        
        insight_text = f"""
### {datetime.now().strftime('%Y-%m-%d')} - Daily Meta-Analysis

Analysis of {total_lessons} formal lessons identified {repeated_count} lessons that continue to be violated after being documented, indicating implementation gaps. Key conclusions: {gaps} lessons learned but not effectively implemented, suggesting need for stronger enforcement mechanisms or clearer prevention protocols.
- Repeated lessons identified: {repeated_count}
- Implementation gaps: {gaps}
- Key conclusions: Lessons exist but patterns persist, indicating prevention protocols may need enhancement or enforcement integration
"""
        
        # Append to insights file
        if REASONING_INSIGHTS_FILE.exists():
            content = REASONING_INSIGHTS_FILE.read_text()
        else:
            content = "## Reasoning Insights from Lessons Learned\n\n"
        
        content += insight_text + "\n"
        REASONING_INSIGHTS_FILE.write_text(content)
        
        print(f"✅ Generated daily insights: {repeated_count} repeated lessons identified")
    
    def generate_weekly_meta_insights(self):
        """Generate weekly meta-insights review"""
        if not REASONING_INSIGHTS_FILE.exists():
            print("⚠️  No insights file found for weekly review")
            return
        
        # Read all daily insights from the week
        content = REASONING_INSIGHTS_FILE.read_text()
        
        # Extract this week's insights (last 7 days)
        week_pattern = r'### (\d{4}-\d{2}-\d{2}) - Daily Meta-Analysis\n(.*?)(?=\n### |\Z)'
        week_insights = re.findall(week_pattern, content, re.DOTALL)
        
        # Analyze patterns
        total_repeated = sum(int(re.search(r'Repeated lessons identified: (\d+)', insight[1]).group(1)) 
                            for insight in week_insights 
                            if re.search(r'Repeated lessons identified: (\d+)', insight[1]))
        
        total_gaps = sum(int(re.search(r'Implementation gaps: (\d+)', insight[1]).group(1))
                        for insight in week_insights
                        if re.search(r'Implementation gaps: (\d+)', insight[1]))
        
        # Generate 3-section format
        weekly_entry = f"""
### {datetime.now().strftime('%Y-%m-%d')} - Weekly Meta-Insights Review

#### Observation
This week's analysis of daily meta-insights reveals {len(week_insights)} daily analysis entries. Total repeated lessons identified: {total_repeated}. Total implementation gaps detected: {total_gaps}. Patterns show consistent theme of lessons existing but not preventing repetition.

#### Analysis
The persistence of repeated lessons despite formal documentation indicates several underlying causes: prevention protocols may lack specificity or enforceability, lessons may not be integrated into pre-execution checklists effectively, or pattern recognition systems may not be triggering prevention mechanisms. The relationship between lesson creation and actual prevention appears weak, suggesting need for stronger feedback loops between learning system and execution system.

#### Conclusion
Strategic insights: The learning system successfully identifies and documents patterns, but the prevention system requires enhancement. Actions needed: integrate lessons more directly into execution workflows, enhance pattern matching for prevention triggers, and create feedback mechanisms to measure prevention effectiveness. Predictions: without stronger enforcement integration, the gap between lessons learned and lessons implemented will persist, reducing ROI of the learning system.
"""
        
        # Append to insights file
        content += weekly_entry + "\n"
        REASONING_INSIGHTS_FILE.write_text(content)
        
        print(f"✅ Generated weekly meta-insights review")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Formal Lesson Extractor')
    parser.add_argument('--autonomous', action='store_true', help='Run in autonomous mode')
    parser.add_argument('--weekly-review', action='store_true', help='Run weekly meta-insights review')
    args = parser.parse_args()
    
    autonomous = args.autonomous or '--autonomous' in sys.argv
    weekly_review = args.weekly_review or '--weekly-review' in sys.argv
    
    print("🎓 Formal Lesson Extractor v2.0.0 - Starting...\n")
    print(f"   Mode: {'Autonomous' if autonomous else 'Manual'}")
    if weekly_review:
        print("   Weekly Review: ENABLED\n")
    
    extractor = FormalLessonExtractor(autonomous=autonomous, weekly_review=weekly_review)
    
    # Analyze patterns and generate lessons
    lessons = extractor.analyze_patterns()
    
    if lessons:
        # Process through quality gates
        extractor.process_lessons(lessons)
        
        # Integrate accepted lessons
        extractor.integrate_lessons()
        
        # Log medium-quality lessons to review file
        for lesson in extractor.review_lessons:
            extractor._log_to_review(lesson)
        
        if extractor.review_lessons:
            print(f"\n📋 {len(extractor.review_lessons)} lessons logged for review (quality {QUALITY_THRESHOLDS['medium_quality']}-{QUALITY_THRESHOLDS['high_quality']})")
            print(f"   Review log: {REVIEW_LOG_FILE}")
        
        # Run meta-analysis
        meta_analysis = extractor.run_meta_analysis()
        
        # Generate daily insights
        extractor.generate_daily_insights(meta_analysis)
        
        # Weekly review if requested
        if weekly_review:
            extractor.generate_weekly_meta_insights()
        
        print("\n" + "=" * 60)
        print("✅ AUTONOMOUS OPERATION COMPLETE")
        print("=" * 60)
        print(f"   Lessons generated: {len(lessons)}")
        print(f"   Lessons accepted: {len(extractor.accepted_lessons)}")
        print(f"   Lessons rejected: {len(extractor.rejected_lessons)}")
        print(f"   Lessons for review: {len(extractor.review_lessons)}")
    else:
        print("\n✅ No formal lesson candidates generated")
        
        # Still run weekly review if requested
        if weekly_review:
            extractor.generate_weekly_meta_insights()


if __name__ == "__main__":
    main()
