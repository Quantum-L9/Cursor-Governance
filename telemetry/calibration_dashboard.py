#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "2.0.0"
component_id: "TEL-CD-001"
component_name: "Calibration Dashboard"
layer: "telemetry"
domain: "monitoring"
type: "dashboard"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "medium"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["json", "datetime", "pathlib", "collections"]
integrates_with: ["FND-PE-001", "INT-AC-001", "TEL-TC-001"]
api_endpoints: []
data_sources: ["telemetry/logs/probabilistic_decisions.jsonl"]
outputs: ["telemetry/reports/calibration/*.md", "calibration_metrics", "drift_alerts"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: false
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Monitor and visualize probabilistic governance calibration quality"
summary: "Generates weekly calibration reports with reliability diagrams, performance metrics, and drift detection"
business_value: "Provides visibility into governance AI quality and automatic alerting for calibration issues"
success_metrics: ["report_generation_success = 1.0", "drift_detection_accuracy > 0.95"]

# === INTEGRATION METADATA ===
suite_2_origin: "New component - built by Claude Sonnet 4.5"
migration_notes: "Monitoring and visualization system for probabilistic governance"

# === TAGS & CLASSIFICATION ===
tags: ["monitoring", "calibration", "dashboard", "reporting", "visualization"]
keywords: ["calibration", "ece", "reliability", "monitoring", "dashboard"]
related_components: ["FND-PE-001", "INT-AC-001"]

# === DESCRIPTION ===
Calibration Dashboard and Monitoring for Probabilistic Governance

Generates:
1. Weekly calibration reports
2. Reliability diagrams (visual calibration)
3. Performance metrics
4. Drift detection alerts

Runs automatically, outputs to telemetry/reports/
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from collections import defaultdict
import urllib.request
import urllib.error


@dataclass
class CalibrationMetrics:
    """Calibration quality metrics"""
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    decisions_evaluated: int
    timestamp: str


@dataclass
class MCPMemoryMetrics:
    """MCP-Memory learning metrics"""
    total_lessons: int
    lessons_this_week: int
    retrieval_count: int  # How often lessons were queried
    avg_importance: float
    avg_confidence: float
    top_tags: List[str]
    coverage_gaps: List[str]  # Error patterns without lessons
    timestamp: str


class CalibrationDashboard:
    """
    Monitoring and visualization for probabilistic governance.
    
    Outputs:
    - Weekly calibration reports (markdown)
    - Reliability diagrams (ASCII art for terminal)
    - Performance trends
    - Alert generation for drift
    - MCP-Memory learning metrics
    """
    
    # MCP-Memory configuration
    MCP_MEMORY_URL = os.environ.get(
        "MCP_MEMORY_URL",
        "https://l9.quantumaipartners.com/mcp/memory"
    )
    MCP_USER_ID = os.environ.get("MCP_USER_ID", "cursor")
    
    def __init__(
        self,
        telemetry_path: str = "telemetry/logs/probabilistic_decisions.jsonl",
        report_dir: str = "telemetry/reports/calibration"
    ):
        self.telemetry_path = Path(telemetry_path)
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.decisions = []
        self._load_decisions()
    
    def _load_decisions(self, days: int = 7):
        """Load recent decisions"""
        if not self.telemetry_path.exists():
            return
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with open(self.telemetry_path) as f:
            for line in f:
                try:
                    decision = json.loads(line.strip())
                    if datetime.fromisoformat(decision['timestamp']) >= cutoff:
                        self.decisions.append(decision)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
    
    def generate_weekly_report(self) -> str:
        """Generate comprehensive weekly calibration report"""
        decisions_with_outcomes = [d for d in self.decisions if d.get('outcome') is not None]
        
        if len(decisions_with_outcomes) < 10:
            return self._insufficient_data_report()
        
        # Calculate metrics
        metrics = self._calculate_metrics(decisions_with_outcomes)
        
        # Generate reliability diagram
        reliability_diagram = self._generate_reliability_diagram(decisions_with_outcomes)
        
        # Performance breakdown by model
        model_performance = self._breakdown_by_model(decisions_with_outcomes)
        
        # Threshold performance
        threshold_performance = self._analyze_thresholds(decisions_with_outcomes)
        
        # Generate report
        report = f"""# Probabilistic Governance - Weekly Calibration Report

**Report Period:** {datetime.utcnow().strftime('%Y-%m-%d')} (Last 7 days)
**Generated:** {datetime.utcnow().isoformat()}

---

## 📊 Overall Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **ECE** | {metrics.ece:.4f} | <0.05 | {'✅' if metrics.ece < 0.05 else '⚠️'} |
| **Accuracy** | {metrics.accuracy:.2%} | >90% | {'✅' if metrics.accuracy > 0.90 else '⚠️'} |
| **Precision** | {metrics.precision:.2%} | >85% | {'✅' if metrics.precision > 0.85 else '⚠️'} |
| **Recall** | {metrics.recall:.2%} | >80% | {'✅' if metrics.recall > 0.80 else '⚠️'} |
| **F1 Score** | {metrics.f1_score:.3f} | >0.85 | {'✅' if metrics.f1_score > 0.85 else '⚠️'} |

**Decisions Analyzed:** {metrics.decisions_evaluated} ({len(decisions_with_outcomes)} with outcomes)

---

## 📈 Reliability Diagram

{reliability_diagram}

**Interpretation:**
- Perfect calibration = bars touch diagonal
- Above diagonal = underconfident
- Below diagonal = overconfident

---

## 🎯 Model Performance Breakdown

{model_performance}

---

## 🎚️ Threshold Performance

{threshold_performance}

---

## 💡 Recommendations

{self._generate_recommendations(metrics, decisions_with_outcomes)}

{self.generate_mcp_memory_section()}

## 🔄 Next Calibration

**Scheduled:** {(datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d 02:00 UTC')}

**Actions:**
- Optimize temperature parameter
- Adjust thresholds for target precision
- Update evidence weights
- Detect new correlations

---

_Generated by Cursor Probabilistic Governance System_
_Report saved to: `{self.report_dir / f"report_{datetime.utcnow().strftime('%Y%m%d')}.md"}`_
"""
        
        # Save report
        report_path = self.report_dir / f"report_{datetime.utcnow().strftime('%Y%m%d')}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        return report
    
    def _calculate_metrics(self, decisions: List[Dict]) -> CalibrationMetrics:
        """Calculate all calibration metrics"""
        # ECE calculation
        ece = self._calculate_ece(decisions)
        mce = self._calculate_mce(decisions)
        
        # Classification metrics
        correct = sum(1 for d in decisions if d['outcome'] == 'correct')
        total = len(decisions)
        accuracy = correct / total if total > 0 else 0.0
        
        # For precision/recall, consider "high risk" predictions
        high_risk_predictions = [
            d for d in decisions 
            if d.get('risk_level') in ['high', 'critical'] or d.get('calibrated_probability', 0) > 0.80
        ]
        
        if high_risk_predictions:
            tp = sum(1 for d in high_risk_predictions if d['outcome'] == 'correct')
            fp = len(high_risk_predictions) - tp
            precision = tp / len(high_risk_predictions) if high_risk_predictions else 0.0
        else:
            precision = 0.0
            tp = 0
        
        # Recall: of all actual high-risk situations, how many did we catch
        actual_high_risk = [
            d for d in decisions
            if d['outcome'] in ['correct', 'too_lenient']  # Should have flagged
        ]
        recall = tp / len(actual_high_risk) if actual_high_risk else 0.0
        
        # F1 score
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        
        return CalibrationMetrics(
            ece=round(ece, 4),
            mce=round(mce, 4),
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            decisions_evaluated=total,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _calculate_ece(self, decisions: List[Dict]) -> float:
        """Calculate Expected Calibration Error"""
        num_bins = 10
        bins = [[] for _ in range(num_bins)]
        
        for d in decisions:
            prob = d.get('calibrated_probability', 0.5)
            bin_idx = min(int(prob * num_bins), num_bins - 1)
            bins[bin_idx].append(d)
        
        ece = 0.0
        total = len(decisions)
        
        for bin_decisions in bins:
            if not bin_decisions:
                continue
            
            confidence = sum(d.get('calibrated_probability', 0.5) for d in bin_decisions) / len(bin_decisions)
            correct = sum(1 for d in bin_decisions if d['outcome'] == 'correct')
            accuracy = correct / len(bin_decisions)
            
            ece += (len(bin_decisions) / total) * abs(confidence - accuracy)
        
        return ece
    
    def _calculate_mce(self, decisions: List[Dict]) -> float:
        """Calculate Maximum Calibration Error"""
        num_bins = 10
        bins = [[] for _ in range(num_bins)]
        
        for d in decisions:
            prob = d.get('calibrated_probability', 0.5)
            bin_idx = min(int(prob * num_bins), num_bins - 1)
            bins[bin_idx].append(d)
        
        max_error = 0.0
        
        for bin_decisions in bins:
            if not bin_decisions:
                continue
            
            confidence = sum(d.get('calibrated_probability', 0.5) for d in bin_decisions) / len(bin_decisions)
            correct = sum(1 for d in bin_decisions if d['outcome'] == 'correct')
            accuracy = correct / len(bin_decisions)
            
            max_error = max(max_error, abs(confidence - accuracy))
        
        return max_error
    
    def _generate_reliability_diagram(self, decisions: List[Dict]) -> str:
        """Generate ASCII reliability diagram"""
        num_bins = 10
        bins = [[] for _ in range(num_bins)]
        
        for d in decisions:
            prob = d.get('calibrated_probability', 0.5)
            bin_idx = min(int(prob * num_bins), num_bins - 1)
            bins[bin_idx].append(d)
        
        diagram = []
        diagram.append("```")
        diagram.append("Confidence →")
        diagram.append(" Accuracy")
        diagram.append("    ↑")
        diagram.append("1.0 │")
        
        for i in range(9, -1, -1):
            line = f"{i/10:.1f} │"
            
            bin_decisions = bins[i]
            if bin_decisions:
                confidence = sum(d.get('calibrated_probability', 0.5) for d in bin_decisions) / len(bin_decisions)
                correct = sum(1 for d in bin_decisions if d['outcome'] == 'correct')
                accuracy = correct / len(bin_decisions)
                
                # Visual representation
                target_pos = int(confidence * 40)
                actual_pos = int(accuracy * 40)
                
                line += " " * min(target_pos, actual_pos)
                if abs(target_pos - actual_pos) > 1:
                    line += "║"  # Gap indicates miscalibration
                else:
                    line += "│"  # Well calibrated
                
                line += f" ({len(bin_decisions)} decisions, acc={accuracy:.2f})"
            
            diagram.append(line)
        
        diagram.append("0.0 └" + "─" * 40)
        diagram.append("    0.0                                    1.0")
        diagram.append("```")
        
        return "\n".join(diagram)
    
    def _breakdown_by_model(self, decisions: List[Dict]) -> str:
        """Performance breakdown by model type"""
        by_model = defaultdict(list)
        
        for d in decisions:
            model = d.get('model_used', 'unknown')
            by_model[model].append(d)
        
        lines = []
        for model, model_decisions in by_model.items():
            correct = sum(1 for d in model_decisions if d['outcome'] == 'correct')
            accuracy = correct / len(model_decisions)
            avg_confidence = sum(d.get('confidence', 0.5) for d in model_decisions) / len(model_decisions)
            
            lines.append(f"### {model}")
            lines.append(f"- Decisions: {len(model_decisions)}")
            lines.append(f"- Accuracy: {accuracy:.2%}")
            lines.append(f"- Avg Confidence: {avg_confidence:.2f}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _analyze_thresholds(self, decisions: List[Dict]) -> str:
        """Analyze threshold performance"""
        thresholds = {
            'high_risk': 0.85,
            'medium_risk': 0.65,
            'low_risk': 0.40
        }
        
        lines = []
        for threshold_name, threshold_value in thresholds.items():
            above = [d for d in decisions if d.get('calibrated_probability', 0) >= threshold_value]
            
            if above:
                correct = sum(1 for d in above if d['outcome'] == 'correct')
                precision = correct / len(above)
                
                lines.append(f"### {threshold_name.replace('_', ' ').title()} (≥{threshold_value})")
                lines.append(f"- Triggered: {len(above)} times")
                lines.append(f"- Precision: {precision:.2%}")
                lines.append(f"- Status: {'✅ Good' if precision > 0.80 else '⚠️ Needs adjustment'}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_recommendations(self, metrics: CalibrationMetrics, decisions: List[Dict]) -> str:
        """Generate actionable recommendations"""
        recommendations = []
        
        # ECE-based
        if metrics.ece > 0.08:
            recommendations.append("⚠️ **High calibration error** - Run temperature optimization")
        elif metrics.ece > 0.05:
            recommendations.append("⚠️ **Moderate calibration error** - Monitor closely, may need adjustment")
        else:
            recommendations.append("✅ **Well-calibrated** - Continue current approach")
        
        # Accuracy-based
        if metrics.accuracy < 0.85:
            recommendations.append("⚠️ **Low accuracy** - Review evidence weights and model logic")
        elif metrics.accuracy < 0.90:
            recommendations.append("ℹ️ **Acceptable accuracy** - Consider fine-tuning for improvement")
        else:
            recommendations.append("✅ **High accuracy** - Model performing well")
        
        # Precision/recall balance
        if metrics.precision < 0.75:
            recommendations.append("⚠️ **Low precision** - Too many false positives, raise thresholds")
        if metrics.recall < 0.75:
            recommendations.append("⚠️ **Low recall** - Missing risky situations, lower thresholds")
        
        # Data sufficiency
        if metrics.decisions_evaluated < 50:
            recommendations.append("ℹ️ **Limited data** - Metrics will stabilize with more decisions")
        
        return "\n".join(f"- {rec}" for rec in recommendations)
    
    def _insufficient_data_report(self) -> str:
        """Report when insufficient data available"""
        return f"""# Probabilistic Governance - Calibration Report

**Report Period:** Last 7 days
**Generated:** {datetime.utcnow().isoformat()}

---

## ⚠️ Insufficient Data

**Decisions With Outcomes:** {len([d for d in self.decisions if d.get('outcome')])}
**Required:** 10 minimum

**Status:** Collecting data for initial calibration.

**Next Steps:**
- Continue using probabilistic governance
- Provide feedback on decisions
- First full calibration will run after 50+ decisions with outcomes

---

_Report will update automatically once sufficient data is collected._
"""
    
    def detect_calibration_drift(self) -> Optional[Dict]:
        """
        Detect if calibration has drifted significantly.
        
        Returns alert if drift detected, None otherwise.
        """
        if len(self.decisions) < 50:
            return None
        
        # Compare last 20 vs previous 30 decisions
        recent = self.decisions[-20:]
        previous = self.decisions[-50:-20]
        
        recent_with_outcomes = [d for d in recent if d.get('outcome')]
        previous_with_outcomes = [d for d in previous if d.get('outcome')]
        
        if len(recent_with_outcomes) < 10 or len(previous_with_outcomes) < 10:
            return None
        
        # Calculate ECE for both periods
        ece_recent = self._calculate_ece(recent_with_outcomes)
        ece_previous = self._calculate_ece(previous_with_outcomes)
        
        # Check for significant drift
        drift = abs(ece_recent - ece_previous)
        
        if drift > 0.10:  # 10% drift threshold
            return {
                'alert_type': 'calibration_drift',
                'ece_previous': ece_previous,
                'ece_recent': ece_recent,
                'drift_magnitude': drift,
                'recommendation': 'trigger_immediate_recalibration',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return None
    
    # =========================================================================
    # MCP-Memory Learning Metrics
    # =========================================================================
    
    def get_mcp_memory_metrics(self) -> Optional[MCPMemoryMetrics]:
        """
        Fetch learning metrics from MCP-Memory.
        
        Metrics:
        - Total lessons stored
        - Lessons added this week
        - Retrieval frequency
        - Average importance/confidence
        - Top tags
        - Coverage gaps
        """
        try:
            # Query MCP-Memory for lesson stats
            stats = self._query_mcp_stats()
            if not stats:
                return None
            
            # Query lessons for tag analysis
            lessons = self._query_mcp_lessons()
            
            # Analyze tags
            tag_counts = defaultdict(int)
            total_importance = 0.0
            total_confidence = 0.0
            lessons_this_week = 0
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            for lesson in lessons:
                # Count tags
                for tag in lesson.get('tags', []):
                    tag_counts[tag] += 1
                
                # Accumulate metrics
                total_importance += lesson.get('importance', 0.5)
                total_confidence += lesson.get('metadata', {}).get('confidence', 0.8)
                
                # Check if added this week
                created_at = lesson.get('created_at', '')
                if created_at:
                    try:
                        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created >= week_ago:
                            lessons_this_week += 1
                    except (ValueError, TypeError):
                        pass
            
            # Top 5 tags
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_tag_names = [t[0] for t in top_tags]
            
            # Calculate averages
            lesson_count = len(lessons) or 1
            avg_importance = total_importance / lesson_count
            avg_confidence = total_confidence / lesson_count
            
            # Identify coverage gaps (error patterns without lessons)
            coverage_gaps = self._identify_coverage_gaps(lessons)
            
            return MCPMemoryMetrics(
                total_lessons=len(lessons),
                lessons_this_week=lessons_this_week,
                retrieval_count=stats.get('query_count', 0),
                avg_importance=round(avg_importance, 2),
                avg_confidence=round(avg_confidence, 2),
                top_tags=top_tag_names,
                coverage_gaps=coverage_gaps,
                timestamp=datetime.utcnow().isoformat()
            )
        
        except Exception as e:
            print(f"⚠️ Failed to get MCP memory metrics: {e}")
            return None
    
    def _query_mcp_stats(self) -> Optional[Dict]:
        """Query MCP-Memory stats endpoint."""
        try:
            req = urllib.request.Request(
                f"{self.MCP_MEMORY_URL}/stats?user_id={self.MCP_USER_ID}",
                headers={'Content-Type': 'application/json'},
                method='GET'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception:
            return None
    
    def _query_mcp_lessons(self) -> List[Dict]:
        """Query all lessons from MCP-Memory."""
        try:
            payload = {
                "query": "lesson mistake prevention rule",
                "user_id": self.MCP_USER_ID,
                "kinds": ["lesson"],
                "top_k": 100,
                "threshold": 0.0
            }
            req = urllib.request.Request(
                f"{self.MCP_MEMORY_URL}/search",
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('results', [])
        except Exception:
            return []
    
    def _identify_coverage_gaps(self, lessons: List[Dict]) -> List[str]:
        """Identify error patterns that don't have corresponding lessons."""
        # Known error patterns from decisions
        error_patterns = set()
        for decision in self.decisions:
            if decision.get('outcome') == 'incorrect':
                pattern = decision.get('error_type', decision.get('action', 'unknown'))
                error_patterns.add(pattern)
        
        # Check which patterns have lessons
        lesson_tags = set()
        for lesson in lessons:
            lesson_tags.update(lesson.get('tags', []))
        
        # Find gaps
        gaps = []
        for pattern in list(error_patterns)[:10]:  # Top 10 gaps
            pattern_lower = pattern.lower()
            if not any(tag.lower() in pattern_lower or pattern_lower in tag.lower() 
                      for tag in lesson_tags):
                gaps.append(pattern)
        
        return gaps[:5]  # Return top 5 gaps
    
    def generate_mcp_memory_section(self) -> str:
        """Generate MCP-Memory section for weekly report."""
        metrics = self.get_mcp_memory_metrics()
        
        if not metrics:
            return """
## 📚 MCP-Memory Learning Metrics

⚠️ **Unable to fetch MCP-Memory metrics**

Check MCP-Memory service availability.
"""
        
        gaps_str = "\n".join(f"- {gap}" for gap in metrics.coverage_gaps) if metrics.coverage_gaps else "- None identified"
        tags_str = ", ".join(f"`{tag}`" for tag in metrics.top_tags) if metrics.top_tags else "None"
        
        return f"""
## 📚 MCP-Memory Learning Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Total Lessons** | {metrics.total_lessons} | {'✅' if metrics.total_lessons >= 10 else '⚠️ Add more'} |
| **Added This Week** | {metrics.lessons_this_week} | {'✅' if metrics.lessons_this_week > 0 else 'ℹ️ Stable'} |
| **Avg Importance** | {metrics.avg_importance:.2f} | {'✅' if metrics.avg_importance > 0.7 else '⚠️'} |
| **Avg Confidence** | {metrics.avg_confidence:.2f} | {'✅' if metrics.avg_confidence > 0.8 else '⚠️'} |

**Top Tags:** {tags_str}

**Coverage Gaps** (error patterns without lessons):
{gaps_str}

---
"""


def generate_weekly_report():
    """Entry point for scheduled weekly report generation"""
    dashboard = CalibrationDashboard()
    report = dashboard.generate_weekly_report()
    
    print(report)
    
    # Check for drift
    drift_alert = dashboard.detect_calibration_drift()
    if drift_alert:
        print("\n⚠️  DRIFT ALERT DETECTED")
        print(json.dumps(drift_alert, indent=2))
    
    return report


if __name__ == '__main__':
    generate_weekly_report()

