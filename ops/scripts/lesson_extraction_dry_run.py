#!/usr/bin/env python3
"""
Lesson Extraction Dry Run - Test threshold policies without modifying files

Usage:
    python lesson_extraction_dry_run.py                    # Default dry run
    python lesson_extraction_dry_run.py --compare          # Compare threshold levels
    python lesson_extraction_dry_run.py --threshold 0.50   # Test specific threshold
    python lesson_extraction_dry_run.py --verbose          # Show all lesson details
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

# Import from formal_lesson_extractor
try:
    from formal_lesson_extractor import (
        FormalLessonExtractor,
        QualityValidator,
        QUALITY_THRESHOLDS,
        MEMORY_INDEX,
        REPEATED_MISTAKES_FILE
    )
    MEMORY_INDEX_FILE = MEMORY_INDEX  # Alias for compatibility
except ImportError as e:
    print(f"❌ Error importing formal_lesson_extractor: {e}")
    print("   Make sure you're running from the ops/scripts directory")
    sys.exit(1)


class DryRunExtractor:
    """Run lesson extraction without writing to disk"""
    
    def __init__(self, verbose: bool = False, reprocess: bool = False):
        self.verbose = verbose
        self.reprocess = reprocess
        self.extractor = FormalLessonExtractor(autonomous=True, weekly_review=False)
        self.all_lessons = []
        self.quality_distribution = defaultdict(list)
        
        # If reprocessing, clear the formalized hashes
        if reprocess:
            self.extractor.formalized_hashes = set()
        
    def load_patterns(self) -> int:
        """Load patterns from memory index"""
        if not MEMORY_INDEX_FILE.exists():
            print(f"❌ Memory index not found: {MEMORY_INDEX_FILE}")
            return 0
            
        with open(MEMORY_INDEX_FILE, 'r') as f:
            data = json.load(f)
        
        patterns = data.get('learnings', [])
        print(f"📊 Loaded {len(patterns)} patterns from memory index")
        print(f"   Last updated: {data.get('last_updated', 'unknown')}")
        print(f"   Processed exports: {len(data.get('processed_exports', []))}")
        
        return len(patterns)
    
    def generate_and_score_lessons(self) -> List[Dict]:
        """Generate lessons and score them without writing"""
        print("\n🔄 Generating lessons from patterns...\n")
        
        # Use extractor's pattern analysis
        lessons = self.extractor.analyze_patterns()
        
        if not lessons:
            print("   No lesson candidates generated")
            return []
        
        print(f"   Generated {len(lessons)} lesson candidates\n")
        
        # Score each lesson
        for lesson in lessons:
            quality_score, dimensions = QualityValidator.assess_quality(lesson)
            lesson['quality_score'] = quality_score
            lesson['quality_dimensions'] = dimensions
            self.all_lessons.append(lesson)
            
            # Categorize by quality level
            if quality_score >= 0.80:
                self.quality_distribution['excellent'].append(lesson)
            elif quality_score >= 0.70:
                self.quality_distribution['high'].append(lesson)
            elif quality_score >= 0.55:
                self.quality_distribution['medium'].append(lesson)
            elif quality_score >= 0.35:
                self.quality_distribution['low'].append(lesson)
            else:
                self.quality_distribution['rejected'].append(lesson)
        
        return self.all_lessons
    
    def print_summary(self):
        """Print quality distribution summary"""
        print("=" * 70)
        print("📊 QUALITY DISTRIBUTION SUMMARY")
        print("=" * 70)
        
        total = len(self.all_lessons)
        if total == 0:
            print("   No lessons to analyze")
            return
        
        categories = [
            ('excellent', '🌟 Excellent (≥0.80)', 0.80),
            ('high', '✅ High (0.70-0.80)', 0.70),
            ('medium', '🟡 Medium (0.55-0.70)', 0.55),
            ('low', '🟠 Low (0.35-0.55)', 0.35),
            ('rejected', '❌ Rejected (<0.35)', 0.0),
        ]
        
        for cat_key, cat_name, threshold in categories:
            count = len(self.quality_distribution[cat_key])
            pct = (count / total) * 100 if total > 0 else 0
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            print(f"   {cat_name}: {count:3d} ({pct:5.1f}%) {bar}")
        
        print(f"\n   Total lessons: {total}")
        
        # Calculate what would pass at each threshold
        print("\n" + "-" * 70)
        print("📈 THRESHOLD SIMULATION")
        print("-" * 70)
        
        thresholds = [0.80, 0.70, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35]
        
        print(f"   {'Threshold':<12} {'Would Pass':<12} {'Percentage':<12} {'Action'}")
        print(f"   {'-'*10:<12} {'-'*10:<12} {'-'*10:<12} {'-'*20}")
        
        for thresh in thresholds:
            would_pass = len([l for l in self.all_lessons if l['quality_score'] >= thresh])
            pct = (would_pass / total) * 100 if total > 0 else 0
            
            # Determine recommendation
            if thresh == QUALITY_THRESHOLDS['high_quality']:
                action = "← Current HIGH threshold"
            elif thresh == QUALITY_THRESHOLDS['medium_quality']:
                action = "← Current MEDIUM threshold"
            elif thresh == QUALITY_THRESHOLDS['low_quality']:
                action = "← Current LOW threshold"
            else:
                action = ""
            
            print(f"   {thresh:<12.2f} {would_pass:<12d} {pct:<11.1f}% {action}")
    
    def print_lesson_details(self, threshold: float = None):
        """Print detailed lesson information"""
        if threshold:
            lessons = [l for l in self.all_lessons if l['quality_score'] >= threshold]
            print(f"\n📋 Lessons with quality ≥ {threshold}: {len(lessons)}")
        else:
            lessons = self.all_lessons
            print(f"\n📋 All {len(lessons)} lessons:")
        
        if not lessons:
            print("   (none)")
            return
        
        for i, lesson in enumerate(sorted(lessons, key=lambda x: x['quality_score'], reverse=True), 1):
            score = lesson['quality_score']
            dims = lesson.get('quality_dimensions', {})
            
            # Determine quality badge
            if score >= 0.80:
                badge = "🌟"
            elif score >= 0.70:
                badge = "✅"
            elif score >= 0.55:
                badge = "🟡"
            elif score >= 0.35:
                badge = "🟠"
            else:
                badge = "❌"
            
            print(f"\n   {badge} Lesson {i} (score: {score:.2f})")
            print(f"      Dimensions: comp={dims.get('completeness', 0):.2f}, "
                  f"act={dims.get('actionability', 0):.2f}, "
                  f"spec={dims.get('specificity', 0):.2f}, "
                  f"impact={dims.get('impact_quantification', 0):.2f}")
            
            if self.verbose:
                mistake = lesson.get('mistake', '')
                prevention = lesson.get('prevention', '')
                impact = lesson.get('impact', '')
                rule = lesson.get('rule', '')
                print(f"      ───────────────────────────────────────────")
                print(f"      MISTAKE: {mistake[:300]}{'...' if len(mistake) > 300 else ''}")
                print(f"      IMPACT: {impact[:200]}{'...' if len(impact) > 200 else ''}")
                print(f"      PREVENTION: {prevention[:250]}{'...' if len(prevention) > 250 else ''}")
                print(f"      RULE: {rule[:150]}{'...' if len(rule) > 150 else ''}")
    
    def compare_thresholds(self):
        """Compare different threshold policies"""
        print("\n" + "=" * 70)
        print("🔬 THRESHOLD POLICY COMPARISON")
        print("=" * 70)
        
        policies = {
            'Conservative': {'high': 0.85, 'medium': 0.70, 'low': 0.50},
            'Current': {'high': 0.70, 'medium': 0.55, 'low': 0.35},
            'Aggressive': {'high': 0.60, 'medium': 0.45, 'low': 0.30},
            'Maximum Extract': {'high': 0.50, 'medium': 0.35, 'low': 0.20},
        }
        
        total = len(self.all_lessons)
        
        print(f"\n   {'Policy':<18} {'High':<8} {'Medium':<8} {'Low':<8} "
              f"{'Auto-Add':<10} {'Review':<10} {'Reject':<10}")
        print(f"   {'-'*16:<18} {'-'*6:<8} {'-'*6:<8} {'-'*6:<8} "
              f"{'-'*8:<10} {'-'*8:<10} {'-'*8:<10}")
        
        for policy_name, thresholds in policies.items():
            auto_add = len([l for l in self.all_lessons 
                          if l['quality_score'] >= thresholds['high']])
            review = len([l for l in self.all_lessons 
                         if thresholds['medium'] <= l['quality_score'] < thresholds['high']])
            reject = len([l for l in self.all_lessons 
                         if l['quality_score'] < thresholds['medium']])
            
            marker = " ← active" if policy_name == 'Current' else ""
            
            print(f"   {policy_name:<18} {thresholds['high']:<8.2f} {thresholds['medium']:<8.2f} "
                  f"{thresholds['low']:<8.2f} {auto_add:<10d} {review:<10d} {reject:<10d}{marker}")
        
        print(f"\n   Total lessons: {total}")
    
    def check_existing_lessons(self):
        """Check how many lessons already exist"""
        if not REPEATED_MISTAKES_FILE.exists():
            print("\n⚠️  No existing repeated-mistakes.md found")
            return 0
        
        with open(REPEATED_MISTAKES_FILE, 'r') as f:
            content = f.read()
        
        # Count lesson entries (### Lesson or ### N.)
        import re
        lesson_count = len(re.findall(r'^###\s+(?:Lesson\s+)?\d+\.', content, re.MULTILINE))
        
        print(f"\n📚 Existing lessons in repeated-mistakes.md: {lesson_count}")
        return lesson_count


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Lesson Extraction Dry Run')
    parser.add_argument('--compare', action='store_true', help='Compare threshold policies')
    parser.add_argument('--threshold', type=float, help='Test specific threshold')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show lesson details')
    parser.add_argument('--show-all', action='store_true', help='Show all lessons')
    parser.add_argument('--reprocess', action='store_true', 
                        help='Reprocess ALL patterns (ignore formalized_hashes)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🧪 LESSON EXTRACTION DRY RUN")
    print("=" * 70)
    print(f"   Mode: DRY RUN (no files will be modified)")
    if args.reprocess:
        print(f"   Reprocess: ALL patterns (ignoring formalized_hashes)")
    print(f"   Current thresholds: high={QUALITY_THRESHOLDS['high_quality']}, "
          f"medium={QUALITY_THRESHOLDS['medium_quality']}, "
          f"low={QUALITY_THRESHOLDS['low_quality']}")
    print()
    
    extractor = DryRunExtractor(verbose=args.verbose, reprocess=args.reprocess)
    
    # Load patterns
    pattern_count = extractor.load_patterns()
    if pattern_count == 0:
        print("❌ No patterns found. Run memory_aggregator.py first.")
        return
    
    # Check existing lessons
    extractor.check_existing_lessons()
    
    # Generate and score
    lessons = extractor.generate_and_score_lessons()
    if not lessons:
        print("\n✅ No new lessons to extract")
        return
    
    # Print summary
    extractor.print_summary()
    
    # Compare thresholds if requested
    if args.compare:
        extractor.compare_thresholds()
    
    # Show lessons above threshold
    if args.threshold:
        extractor.print_lesson_details(args.threshold)
    elif args.show_all:
        extractor.print_lesson_details()
    elif args.verbose:
        # Show top 5 lessons
        print("\n📋 Top 5 lessons by quality:")
        sorted_lessons = sorted(extractor.all_lessons, 
                               key=lambda x: x['quality_score'], reverse=True)[:5]
        for i, lesson in enumerate(sorted_lessons, 1):
            score = lesson['quality_score']
            mistake = lesson.get('mistake', '')[:100]
            print(f"\n   {i}. (score: {score:.2f}) {mistake}...")
    
    print("\n" + "=" * 70)
    print("✅ DRY RUN COMPLETE - No files were modified")
    print("=" * 70)
    print("\nTo apply changes, run:")
    print("   python formal_lesson_extractor.py --autonomous")


if __name__ == "__main__":
    main()
