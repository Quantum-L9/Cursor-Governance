#!/usr/bin/env python3
"""
Context Memory Extractor
Runs hourly - extracts session context from chat exports
Uses Bayesian probabilistic reasoning for context meaningfulness assessment
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import sys
import re

# Import Bayesian probabilistic engine
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'foundation' / 'logic'))
try:
    from probabilistic_engine import CursorProbabilisticEngine, Evidence
    BAYESIAN_AVAILABLE = True
except ImportError:
    print("⚠️  Bayesian engine not found, falling back to heuristics")
    BAYESIAN_AVAILABLE = False

class ContextExtractor:
    def __init__(self, export_dir, output_dir):
        self.export_dir = Path(export_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_context_from_export(self):
        """Extract context from latest chat export"""
        # Based on fix: Cursor stores chats in User/workspaceStorage as SQLite, NOT leveldb
        workspace_storage = self.export_dir / "User/workspaceStorage"
        
        if not workspace_storage.exists():
            print(f"No workspace storage found at {workspace_storage}")
            return None
        
        # Collect all messages from all workspace databases
        all_messages = []
        conversations = []
        
        try:
            # Process each workspace database
            workspaces = [d for d in workspace_storage.iterdir() if d.is_dir()]
            
            for workspace in workspaces:
                state_db = workspace / "state.vscdb"
                if not state_db.exists():
                    continue
                
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
                    print(f"  ⚠️  Error processing {workspace.name}: {e}")
            
            if not conversations:
                print("No conversations found in export")
                return None
            
            # Analyze conversations for context
            context = self._analyze_conversations_for_context(conversations)
            
            return context if self._is_meaningful_context(context) else None
            
        except Exception as e:
            print(f"Error extracting context: {e}")
            return None
    
    def _analyze_conversations_for_context(self, conversations):
        """Analyze conversations to extract context"""
        # Combine all conversation text
        all_text = json.dumps(conversations)
        
        context = {
            'timestamp': datetime.now().isoformat(),
            'hour': datetime.now().strftime('%Y-%m-%d-%H'),
            'message_count': len(conversations),
            'project': self._detect_project(all_text),
            'summary': self._generate_summary(all_text),
            'key_actions': self._extract_actions(all_text),
            'decisions': self._extract_decisions(all_text),
            'files_modified': self._extract_files(all_text),
            'next_steps': self._extract_next_steps(all_text),
            'context_signals': self._extract_context_signals(all_text)
        }
        
        return context
    
    def _detect_project(self, text):
        """Detect which project we're working on"""
        projects = {
            'cursor-load-pack': ['cursor load pack', 'cursor_load pack', 'load pack'],
            'mack': ['mack', 'sales agent', 'bcp'],
            'linda': ['linda', 'operations', 'logistics'],
            'governance': ['governance', 'suite 6', 'globalcommands'],
            'n8n': ['n8n', 'workflow', 'automation'],
            'neo4j': ['neo4j', 'graph', 'cypher']
        }
        
        text_lower = text.lower()
        for project, keywords in projects.items():
            if any(keyword in text_lower for keyword in keywords):
                return project
        
        return 'general'
    
    def _generate_summary(self, text):
        """Generate brief summary of what was done"""
        # Look for completion indicators
        if 'complet' in text.lower() or 'finish' in text.lower():
            return self._extract_completion_summary(text)
        elif 'build' in text.lower() or 'creat' in text.lower():
            return self._extract_creation_summary(text)
        elif 'fix' in text.lower() or 'debug' in text.lower():
            return "Debugging and fixing issues"
        elif 'commit' in text.lower() or 'github' in text.lower():
            return "Version control and GitHub operations"
        else:
            return "Active development session"
    
    def _extract_completion_summary(self, text):
        """Extract what was completed"""
        # Look for sentences with "completed" or "finished"
        sentences = text.split('.')
        for sentence in sentences:
            if 'complet' in sentence.lower() or 'finish' in sentence.lower():
                return sentence.strip()[:100]
        return "Completed development tasks"
    
    def _extract_creation_summary(self, text):
        """Extract what was created"""
        sentences = text.split('.')
        for sentence in sentences:
            if 'creat' in sentence.lower() or 'build' in sentence.lower() or 'add' in sentence.lower():
                return sentence.strip()[:100]
        return "Created new components"
    
    def _extract_actions(self, text):
        """Extract key actions taken"""
        actions = []
        action_patterns = [
            r'(?:created|built|added|implemented|fixed|updated|modified)\s+([^.,:]+)',
            r'(?:I|We)\s+(?:created|built|added|implemented|fixed|updated)\s+([^.,:]+)',
        ]
        
        for pattern in action_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                action = match.group(0).strip()
                if len(action) < 100 and action not in actions:
                    actions.append(action)
        
        return actions[:5]  # Top 5 actions
    
    def _extract_decisions(self, text):
        """Extract key decisions made"""
        decisions = []
        decision_patterns = [
            r'(?:decided|chose|selected|opted)\s+(?:to\s+)?([^.,:]+)',
            r'(?:decision|choice):\s*([^.,:]+)',
        ]
        
        for pattern in decision_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                decision = match.group(0).strip()
                if len(decision) < 150 and decision not in decisions:
                    decisions.append(decision)
        
        return decisions[:3]  # Top 3 decisions
    
    def _extract_files(self, text):
        """Extract files that were modified"""
        files = set()
        
        # Look for file paths
        file_patterns = [
            r'[\w\-./]+\.\w+',  # Basic file.ext
            r'(?:created|modified|updated|edited)\s+([\w\-./]+)',
        ]
        
        for pattern in file_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                file_path = match.group(0).strip()
                # Filter out noise
                if ('/' in file_path or '.' in file_path) and len(file_path) < 100:
                    # Clean up common prefixes
                    file_path = file_path.split()[-1] if ' ' in file_path else file_path
                    files.add(file_path)
        
        return sorted(list(files))[:10]  # Top 10 files
    
    def _extract_next_steps(self, text):
        """Extract mentioned next steps"""
        next_steps = []
        next_patterns = [
            r'(?:next|then|after|following)\s+(?:step|we|I|should|will|need to)\s+([^.,:]+)',
            r'(?:TODO|NEXT|FUTURE):\s*([^.,:]+)',
        ]
        
        for pattern in next_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                step = match.group(1).strip()
                if len(step) < 150 and step not in next_steps:
                    next_steps.append(step)
        
        return next_steps[:3]  # Top 3 next steps
    
    def _extract_context_signals(self, text):
        """Extract context signals for better understanding"""
        signals = {
            'has_code': bool(re.search(r'```|function|class|def |import ', text)),
            'has_commits': bool(re.search(r'git commit|git push|github', text, re.IGNORECASE)),
            'has_errors': bool(re.search(r'error|exception|failed|bug', text, re.IGNORECASE)),
            'has_completion': bool(re.search(r'complet|finish|done|success', text, re.IGNORECASE)),
            'has_questions': bool(re.search(r'\?|should we|what if', text)),
            'is_planning': bool(re.search(r'plan|strategy|approach|design', text, re.IGNORECASE)),
        }
        return signals
    
    def _is_meaningful_context(self, context):
        """
        Determine if context is worth saving using Bayesian probabilistic reasoning.
        
        Replaces naive heuristics with evidence-based assessment:
        - Weighs multiple signals (actions, files, decisions, messages, context signals)
        - Combines evidence using Bayesian weighted ensemble
        - Returns calibrated probability with confidence scoring
        """
        if not context:
            return False
        
        # If Bayesian engine not available, fall back to heuristics
        if not BAYESIAN_AVAILABLE:
            return (
                len(context['key_actions']) > 0 or
                len(context['files_modified']) > 0 or
                len(context['decisions']) > 0 or
                context['message_count'] > 3
            )
        
        # Use Bayesian probabilistic assessment
        try:
            # Gather evidence about context meaningfulness
            evidence_list = [
                Evidence(
                    name="actions_present",
                    value=min(len(context['key_actions']) / 3.0, 1.0),  # Normalize to 0-1
                    weight=0.25,
                    confidence=1.0,
                    source="action_detection"
                ),
                Evidence(
                    name="files_modified",
                    value=min(len(context['files_modified']) / 5.0, 1.0),  # Normalize to 0-1
                    weight=0.20,
                    confidence=1.0,
                    source="file_tracking"
                ),
                Evidence(
                    name="decisions_made",
                    value=min(len(context['decisions']) / 2.0, 1.0),  # Normalize to 0-1
                    weight=0.20,
                    confidence=1.0,
                    source="decision_detection"
                ),
                Evidence(
                    name="message_volume",
                    value=min(context['message_count'] / 10.0, 1.0),  # Normalize: 10+ messages = high signal
                    weight=0.15,
                    confidence=1.0,
                    source="conversation_length"
                ),
                Evidence(
                    name="code_present",
                    value=1.0 if context['context_signals']['has_code'] else 0.0,
                    weight=0.10,
                    confidence=1.0,
                    source="code_detection"
                ),
                Evidence(
                    name="completion_signal",
                    value=1.0 if context['context_signals']['has_completion'] else 0.3,
                    weight=0.10,
                    confidence=0.8,  # Less confident about this signal
                    source="completion_detection"
                )
            ]
            
            # Calculate weighted probability
            engine = CursorProbabilisticEngine()
            raw_probability = engine._weighted_combination(evidence_list)
            
            # Apply temperature calibration (default temp = 1.0)
            calibrated_probability = engine._apply_temperature_scaling(raw_probability, 1.0)
            
            # Calculate confidence in this assessment
            confidence = engine._calculate_confidence(evidence_list)
            
            # Log decision for learning (optional - helps calibration)
            print(f"  📊 Bayesian assessment: {calibrated_probability:.3f} (confidence: {confidence:.2f})")
            
            # Threshold: Save if probability > 0.50 (meaningful context)
            # This threshold can be auto-calibrated over time
            return calibrated_probability > 0.50
            
        except Exception as e:
            print(f"⚠️  Bayesian assessment failed: {e}, falling back to heuristics")
            # Fallback to simple heuristics
            return (
                len(context['key_actions']) > 0 or
                len(context['files_modified']) > 0 or
                len(context['decisions']) > 0 or
                context['message_count'] > 3
            )
    
    def save_context(self, context):
        """Save context to session file"""
        if not context:
            return None
        
        # Create session file
        filename = f"{context['hour']}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(context, f, indent=2)
        
        print(f"✅ Context saved: {filename}")
        
        # Update index
        self._update_index(context)
        
        return filepath
    
    def _update_index(self, context):
        """Update session index"""
        index_path = self.output_dir / "index.json"
        
        # Load existing index
        if index_path.exists():
            with open(index_path) as f:
                index = json.load(f)
        else:
            index = {'sessions': []}
        
        # Add new session
        index['sessions'].append({
            'timestamp': context['timestamp'],
            'hour': context['hour'],
            'project': context['project'],
            'summary': context['summary'],
            'file': f"{context['hour']}.json"
        })
        
        # Keep only last 168 hours (7 days)
        index['sessions'] = index['sessions'][-168:]
        
        # Save index
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract context from chat exports')
    parser.add_argument('--export-dir', required=True, help='Chat export directory')
    parser.add_argument('--output-dir', required=True, help='Output directory for contexts')
    
    args = parser.parse_args()
    
    extractor = ContextExtractor(args.export_dir, args.output_dir)
    context = extractor.extract_context_from_export()
    
    if context:
        extractor.save_context(context)
        print(f"✅ Context extracted: {context['project']} - {context['summary']}")
    else:
        print("ℹ️  No meaningful context in last hour")

if __name__ == '__main__':
    main()

