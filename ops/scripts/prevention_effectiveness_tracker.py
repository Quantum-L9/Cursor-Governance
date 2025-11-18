#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-PET-001"
component_name: "Prevention Effectiveness Tracker"
layer: "operations"
domain: "learning"
type: "tracker"
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
dependencies: ["python3", "json", "pathlib", "os"]
integrates_with: ["OPS-PEC-001", "OPS-FLE-001", "OPS-CLI-001"]
data_sources: ["ops/logs/prevention_attempts.json", "ops/logs/pre_execution_checker_audit.jsonl"]
outputs: ["ops/logs/effectiveness_reports/", "effectiveness_metrics.json"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Measure if lessons actually prevent mistakes"
summary: "Tracks prevention attempts, outcomes, and calculates effectiveness metrics"
business_value: "Enables data-driven improvement of prevention system and lesson quality"
success_metrics: ["effectiveness_rate >= 80%", "prevention_rate >= 95%", "report_generation_success >= 99%"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "effectiveness", "tracking", "metrics", "analytics"]
keywords: ["prevention", "effectiveness", "tracking", "metrics", "analytics", "roi"]
related_components: ["OPS-PEC-001", "OPS-FLE-001", "OPS-CLI-001"]
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Configuration - Use Dropbox as single source of truth
def get_global_commands_path():
    """Get GlobalCommands path, preferring Dropbox location"""
    fallback_log = Path.home() / ".cursor-globalcommands-fallback.log"
    disable_fallback = os.environ.get("DISABLE_FALLBACK", "0") == "1"
    
    dropbox_paths = [
        Path.home() / "Dropbox/Cursor Governance/GlobalCommands"
    ]
    library_path = Path(os.path.expanduser("~/Library/Application Support/Cursor/GlobalCommands"))
    
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
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: prevention_effectiveness_tracker.py
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
PREVENTION_ATTEMPTS_FILE = GLOBAL_COMMANDS / "ops/logs/prevention_attempts.json"
AUDIT_LOG_FILE = GLOBAL_COMMANDS / "ops/logs/pre_execution_checker_audit.jsonl"
EFFECTIVENESS_REPORTS_DIR = GLOBAL_COMMANDS / "ops/logs/effectiveness_reports"
EFFECTIVENESS_METRICS_FILE = GLOBAL_COMMANDS / "ops/logs/effectiveness_metrics.json"
REPEATED_MISTAKES_FILE = GLOBAL_COMMANDS / "learning/failures/repeated-mistakes.md"
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"


class PreventionEffectivenessTracker:
    """Track prevention attempts and calculate effectiveness metrics"""
    
    def __init__(self):
        self.attempts = self._load_attempts()
        self.effectiveness_metrics = self._load_metrics()
    
    def _load_attempts(self) -> List[Dict[str, Any]]:
        """Load prevention attempts from audit log"""
        attempts = []
        
        if AUDIT_LOG_FILE.exists():
            with open(AUDIT_LOG_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            attempts.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        
        return attempts
    
    def _load_metrics(self) -> Dict[str, Any]:
        """Load effectiveness metrics"""
        if EFFECTIVENESS_METRICS_FILE.exists():
            try:
                with open(EFFECTIVENESS_METRICS_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {
            'last_calculated': None,
            'prevention_rate': 0.0,
            'mistake_repetition_rate': 0.0,
            'lesson_effectiveness': {},
            'pattern_decay_rate': {},
            'roi_calculations': {}
        }
    
    def track_prevention_attempt(self, lesson_id: str, action_description: str, 
                                 blocked: bool, confidence: float, severity: str):
        """Track a prevention attempt"""
        attempt = {
            'timestamp': datetime.now().isoformat(),
            'lesson_id': lesson_id,
            'action_description': action_description[:200],
            'blocked': blocked,
            'confidence': confidence,
            'severity': severity
        }
        
        # Append to attempts file
        PREVENTION_ATTEMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        attempts_list = []
        if PREVENTION_ATTEMPTS_FILE.exists():
            try:
                with open(PREVENTION_ATTEMPTS_FILE, 'r') as f:
                    attempts_list = json.load(f).get('attempts', [])
            except json.JSONDecodeError:
                pass
        
        attempts_list.append(attempt)
        
        # Keep only last 10000 attempts
        attempts_list = attempts_list[-10000:]
        
        with open(PREVENTION_ATTEMPTS_FILE, 'w') as f:
            json.dump({'attempts': attempts_list, 'last_updated': datetime.now().isoformat()}, f, indent=2)
    
    def calculate_effectiveness_metrics(self) -> Dict[str, Any]:
        """Calculate effectiveness metrics"""
        # Reload attempts
        self.attempts = self._load_attempts()
        
        if not self.attempts:
            return {
                'prevention_rate': 0.0,
                'mistake_repetition_rate': 0.0,
                'total_attempts': 0,
                'blocked_actions': 0,
                'warned_actions': 0,
                'message': 'No prevention attempts recorded yet'
            }
        
        # Calculate prevention rate
        total_attempts = len(self.attempts)
        blocked_actions = len([a for a in self.attempts if a.get('blocked', False)])
        prevention_rate = (blocked_actions / total_attempts * 100) if total_attempts > 0 else 0.0
        
        # Calculate mistake repetition rate
        # Check if patterns matching lessons occurred AFTER lesson date
        mistake_repetition_rate = self._calculate_mistake_repetition_rate()
        
        # Calculate lesson effectiveness
        lesson_effectiveness = self._calculate_lesson_effectiveness()
        
        # Calculate pattern decay rate
        pattern_decay_rate = self._calculate_pattern_decay_rate()
        
        # Calculate ROI
        roi_calculations = self._calculate_roi()
        
        metrics = {
            'last_calculated': datetime.now().isoformat(),
            'prevention_rate': prevention_rate,
            'mistake_repetition_rate': mistake_repetition_rate,
            'total_attempts': total_attempts,
            'blocked_actions': blocked_actions,
            'warned_actions': len([a for a in self.attempts if not a.get('blocked', False) and a.get('severity') in ['MEDIUM', 'LOW']]),
            'lesson_effectiveness': lesson_effectiveness,
            'pattern_decay_rate': pattern_decay_rate,
            'roi_calculations': roi_calculations
        }
        
        # Save metrics
        self.effectiveness_metrics = metrics
        EFFECTIVENESS_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EFFECTIVENESS_METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        return metrics
    
    def _calculate_mistake_repetition_rate(self) -> float:
        """Calculate mistake repetition rate"""
        if not REPEATED_MISTAKES_FILE.exists() or not MEMORY_INDEX.exists():
            return 0.0
        
        # Load lessons and their dates
        content = REPEATED_MISTAKES_FILE.read_text()
        lesson_dates = {}
        
        lesson_pattern = r'### \*\*(\d+)\.\s*(.*?)\*\*\n.*?\*\*Date Added:\*\*\s*(\d{4}-\d{2}-\d{2})'
        matches = re.findall(lesson_pattern, content, re.DOTALL)
        
        for match in matches:
            lesson_num, title, date_added = match
            lesson_dates[f"lesson_{lesson_num}"] = date_added
        
        # Load learnings from memory_index
        with open(MEMORY_INDEX, 'r') as f:
            memory_data = json.load(f)
        
        learnings = memory_data.get('learnings', [])
        
        # Count repetitions (patterns matching lessons after lesson date)
        total_lessons = len(lesson_dates)
        repeated_lessons = 0
        
        for lesson_id, lesson_date in lesson_dates.items():
            # Find patterns matching this lesson after lesson date
            matching_patterns = [
                l for l in learnings
                if l.get('timestamp', '')[:10] > lesson_date
                and self._pattern_matches_lesson(l, lesson_id)
            ]
            
            if matching_patterns:
                repeated_lessons += 1
        
        repetition_rate = (repeated_lessons / total_lessons * 100) if total_lessons > 0 else 0.0
        return repetition_rate
    
    def _pattern_matches_lesson(self, pattern: Dict, lesson_id: str) -> bool:
        """Check if pattern matches a lesson"""
        # Simple matching - check if pattern content contains lesson keywords
        pattern_content = pattern.get('content', '').lower()
        lesson_num = lesson_id.replace('lesson_', '')
        
        # Extract keywords from lesson title in repeated-mistakes.md
        if REPEATED_MISTAKES_FILE.exists():
            content = REPEATED_MISTAKES_FILE.read_text()
            lesson_match = re.search(rf'### \*\*{lesson_num}\.\s*(.*?)\*\*', content)
            if lesson_match:
                title = lesson_match.group(1).lower()
                keywords = [w for w in re.findall(r'\b\w{4,}\b', title) if len(w) > 3]
                matches = sum(1 for kw in keywords if kw in pattern_content)
                return matches >= 2
        
        return False
    
    def _calculate_lesson_effectiveness(self) -> Dict[str, float]:
        """Calculate effectiveness for each lesson"""
        lesson_effectiveness = {}
        
        # Group attempts by lesson_id
        attempts_by_lesson = defaultdict(list)
        for attempt in self.attempts:
            lesson_id = attempt.get('lesson_id', 'unknown')
            attempts_by_lesson[lesson_id].append(attempt)
        
        # Calculate effectiveness for each lesson
        for lesson_id, attempts in attempts_by_lesson.items():
            if not attempts:
                continue
            
            # Effectiveness = (blocks / total_attempts) * 100
            total = len(attempts)
            blocks = len([a for a in attempts if a.get('blocked', False)])
            effectiveness = (blocks / total * 100) if total > 0 else 0.0
            
            lesson_effectiveness[lesson_id] = effectiveness
        
        return lesson_effectiveness
    
    def _calculate_pattern_decay_rate(self) -> Dict[str, float]:
        """Calculate how quickly lessons become ineffective"""
        decay_rates = {}
        
        # Group attempts by lesson_id and time
        attempts_by_lesson = defaultdict(list)
        for attempt in self.attempts:
            lesson_id = attempt.get('lesson_id', 'unknown')
            attempts_by_lesson[lesson_id].append(attempt)
        
        for lesson_id, attempts in attempts_by_lesson.items():
            if len(attempts) < 10:  # Need enough data
                continue
            
            # Sort by timestamp
            attempts.sort(key=lambda x: x.get('timestamp', ''))
            
            # Calculate effectiveness over time windows
            window_size = len(attempts) // 4  # 4 time windows
            if window_size < 2:
                continue
            
            effectiveness_by_window = []
            for i in range(0, len(attempts), window_size):
                window = attempts[i:i+window_size]
                if window:
                    blocks = len([a for a in window if a.get('blocked', False)])
                    effectiveness = (blocks / len(window) * 100) if window else 0.0
                    effectiveness_by_window.append(effectiveness)
            
            # Calculate decay rate (slope of effectiveness over time)
            if len(effectiveness_by_window) >= 2:
                decay_rate = (effectiveness_by_window[-1] - effectiveness_by_window[0]) / len(effectiveness_by_window)
                decay_rates[lesson_id] = decay_rate
        
        return decay_rates
    
    def _calculate_roi(self) -> Dict[str, Any]:
        """Calculate ROI (time saved / time invested)"""
        # Estimate time saved from blocked actions
        # Assume each blocked action saves 30 minutes (average rework time)
        blocked_actions = len([a for a in self.attempts if a.get('blocked', False)])
        time_saved_hours = blocked_actions * 0.5  # 30 minutes per block
        
        # Estimate time invested in lesson creation
        # Assume 15 minutes per lesson
        if REPEATED_MISTAKES_FILE.exists():
            content = REPEATED_MISTAKES_FILE.read_text()
            lesson_count = len(re.findall(r'### \*\*\d+\.', content))
            time_invested_hours = lesson_count * 0.25  # 15 minutes per lesson
        else:
            time_invested_hours = 0
        
        roi = (time_saved_hours / time_invested_hours) if time_invested_hours > 0 else 0.0
        
        return {
            'time_saved_hours': time_saved_hours,
            'time_invested_hours': time_invested_hours,
            'roi': roi,
            'blocked_actions': blocked_actions
        }
    
    def generate_daily_report(self) -> str:
        """Generate daily effectiveness report"""
        metrics = self.calculate_effectiveness_metrics()
        
        report = f"""
# Prevention Effectiveness Report - {datetime.now().strftime('%Y-%m-%d')}

## Summary Metrics

- **Prevention Rate:** {metrics['prevention_rate']:.2f}%
- **Mistake Repetition Rate:** {metrics['mistake_repetition_rate']:.2f}%
- **Total Prevention Attempts:** {metrics['total_attempts']}
- **Actions Blocked:** {metrics['blocked_actions']}
- **Actions Warned:** {metrics['warned_actions']}

## ROI Analysis

- **Time Saved:** {metrics['roi_calculations']['time_saved_hours']:.2f} hours
- **Time Invested:** {metrics['roi_calculations']['time_invested_hours']:.2f} hours
- **ROI:** {metrics['roi_calculations']['roi']:.2f}x

## Lesson Effectiveness

"""
        
        # Top 5 most effective lessons
        lesson_effectiveness = metrics.get('lesson_effectiveness', {})
        sorted_lessons = sorted(lesson_effectiveness.items(), key=lambda x: x[1], reverse=True)[:5]
        
        report += "### Top 5 Most Effective Lessons\n\n"
        for lesson_id, effectiveness in sorted_lessons:
            report += f"- **{lesson_id}**: {effectiveness:.2f}% effectiveness\n"
        
        # Ineffective lessons (effectiveness < 50%)
        ineffective = [(lid, eff) for lid, eff in lesson_effectiveness.items() if eff < 50.0]
        if ineffective:
            report += "\n### Lessons Needing Revision (Effectiveness < 50%)\n\n"
            for lesson_id, effectiveness in ineffective:
                report += f"- **{lesson_id}**: {effectiveness:.2f}% effectiveness ⚠️\n"
        
        # Save report
        EFFECTIVENESS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_file = EFFECTIVENESS_REPORTS_DIR / f"effectiveness_report_{datetime.now().strftime('%Y%m%d')}.md"
        report_file.write_text(report)
        
        return report
    
    def generate_weekly_trend_analysis(self) -> str:
        """Generate weekly trend analysis"""
        # Load last 7 days of reports
        reports = []
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            report_file = EFFECTIVENESS_REPORTS_DIR / f"effectiveness_report_{date.strftime('%Y%m%d')}.md"
            if report_file.exists():
                reports.append(report_file.read_text())
        
        if not reports:
            return "No reports available for trend analysis"
        
        # Extract metrics from reports
        prevention_rates = []
        for report in reports:
            rate_match = re.search(r'Prevention Rate:\s*([\d.]+)%', report)
            if rate_match:
                prevention_rates.append(float(rate_match.group(1)))
        
        if not prevention_rates:
            return "Could not extract metrics from reports"
        
        avg_rate = sum(prevention_rates) / len(prevention_rates)
        trend = "improving" if len(prevention_rates) >= 2 and prevention_rates[-1] > prevention_rates[0] else "declining" if len(prevention_rates) >= 2 and prevention_rates[-1] < prevention_rates[0] else "stable"
        
        analysis = f"""
# Weekly Trend Analysis - Week Ending {datetime.now().strftime('%Y-%m-%d')}

## Prevention Rate Trend

- **Average Prevention Rate:** {avg_rate:.2f}%
- **Trend:** {trend}
- **Data Points:** {len(prevention_rates)} days

## Recommendations

"""
        
        if trend == "declining":
            analysis += "- ⚠️ Prevention rate is declining - review lesson patterns\n"
            analysis += "- Consider updating prevention rules\n"
            analysis += "- Check for new mistake patterns not covered\n"
        elif trend == "improving":
            analysis += "- ✅ Prevention rate is improving - system is working\n"
            analysis += "- Continue monitoring effectiveness\n"
        else:
            analysis += "- ➡️ Prevention rate is stable\n"
            analysis += "- Monitor for changes\n"
        
        # Save analysis
        analysis_file = EFFECTIVENESS_REPORTS_DIR / f"weekly_trend_{datetime.now().strftime('%Y%m%d')}.md"
        analysis_file.write_text(analysis)
        
        return analysis


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prevention Effectiveness Tracker')
    parser.add_argument('--daily-report', action='store_true', help='Generate daily report')
    parser.add_argument('--weekly-trend', action='store_true', help='Generate weekly trend analysis')
    parser.add_argument('--calculate', action='store_true', help='Calculate effectiveness metrics')
    args = parser.parse_args()
    
    print("📊 Prevention Effectiveness Tracker v1.0.0 - Starting...\n")
    
    tracker = PreventionEffectivenessTracker()
    
    if args.calculate or (not args.daily_report and not args.weekly_trend):
        metrics = tracker.calculate_effectiveness_metrics()
        print(f"✅ Effectiveness Metrics Calculated:")
        print(f"   Prevention Rate: {metrics['prevention_rate']:.2f}%")
        print(f"   Mistake Repetition Rate: {metrics['mistake_repetition_rate']:.2f}%")
        print(f"   Total Attempts: {metrics['total_attempts']}")
        print(f"   ROI: {metrics['roi_calculations']['roi']:.2f}x")
    
    if args.daily_report:
        report = tracker.generate_daily_report()
        print(f"\n✅ Daily report generated:")
        print(f"   {EFFECTIVENESS_REPORTS_DIR / f'effectiveness_report_{datetime.now().strftime(\"%Y%m%d\")}.md'}")
    
    if args.weekly_trend:
        analysis = tracker.generate_weekly_trend_analysis()
        print(f"\n✅ Weekly trend analysis generated:")
        print(f"   {EFFECTIVENESS_REPORTS_DIR / f'weekly_trend_{datetime.now().strftime(\"%Y%m%d\")}.md'}")


if __name__ == "__main__":
    import re
    main()

