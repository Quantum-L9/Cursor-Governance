#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "INT-ARD-001"
component_name: "Adaptive Reasoning Depth"
layer: "intelligence"
domain: "reasoning"
type: "adaptive"
status: "active"
created: "2025-11-17T22:06:00Z"
updated: "2025-11-17T22:06:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3"]
integrates_with: ["INT-RSN-001", "OPS-CLI-001"]
data_sources: ["confidence_scores", "task_complexity"]
outputs: ["reasoning_depth", "reasoning_mode"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "interactive"

# === BUSINESS METADATA ===
purpose: "Adjust reasoning depth based on task complexity and confidence"
summary: "Adaptive reasoning system that selects optimal reasoning depth based on confidence and complexity"
business_value: "Optimizes reasoning resources and improves efficiency"
success_metrics: ["depth_selection_accuracy >= 90%", "reasoning_efficiency >= 85%"]

# === TAGS & CLASSIFICATION ===
tags: ["reasoning", "adaptive", "depth", "optimization"]
keywords: ["adaptive", "reasoning", "depth", "confidence", "complexity"]
related_components: ["INT-RSN-001", "OPS-CLI-001"]
"""

from typing import Dict, Any, Optional
from enum import Enum

class ReasoningDepth(Enum):
    """Reasoning depth levels"""
    MINIMAL = 1      # Simple factual, confidence > 0.95
    STANDARD = 3    # Moderate complexity, 0.85-0.95
    ENHANCED = 5    # Complex, 0.75-0.85
    HEAVY_FORGE = 8 # Highly complex, < 0.75


class AdaptiveReasoning:
    """Adaptive reasoning depth selector"""
    
    @staticmethod
    def determine_depth(confidence: float, complexity: Optional[str] = None) -> ReasoningDepth:
        """
        Determine reasoning depth based on confidence and complexity
        
        Args:
            confidence: Confidence score (0.0-1.0)
            complexity: Optional complexity indicator ('simple', 'moderate', 'complex', 'highly_complex')
        
        Returns:
            ReasoningDepth enum value
        """
        # Use complexity if provided, otherwise infer from confidence
        if complexity:
            complexity_map = {
                'simple': ReasoningDepth.MINIMAL,
                'moderate': ReasoningDepth.STANDARD,
                'complex': ReasoningDepth.ENHANCED,
                'highly_complex': ReasoningDepth.HEAVY_FORGE
            }
            return complexity_map.get(complexity, ReasoningDepth.STANDARD)
        
        # Determine from confidence
        if confidence > 0.95:
            return ReasoningDepth.MINIMAL
        elif confidence > 0.85:
            return ReasoningDepth.STANDARD
        elif confidence > 0.75:
            return ReasoningDepth.ENHANCED
        else:
            return ReasoningDepth.HEAVY_FORGE
    
    @staticmethod
    def get_depth_config(depth: ReasoningDepth) -> Dict[str, Any]:
        """Get configuration for a reasoning depth level"""
        configs = {
            ReasoningDepth.MINIMAL: {
                'depth': 1,
                'blocks': ['objective', 'execution', 'synthesis'],
                'description': 'Simple factual reasoning',
                'use_cases': ['Data lookup', 'Simple queries', 'High-confidence tasks']
            },
            ReasoningDepth.STANDARD: {
                'depth': 3,
                'blocks': ['objective', 'context', 'execution', 'synthesis'],
                'description': 'Moderate complexity reasoning',
                'use_cases': ['Standard tasks', 'Moderate complexity', 'Normal confidence']
            },
            ReasoningDepth.ENHANCED: {
                'depth': 5,
                'blocks': ['objective', 'context', 'decomposition', 'leverage', 'execution', 'synthesis'],
                'description': 'Complex reasoning',
                'use_cases': ['Complex tasks', 'Lower confidence', 'Strategic decisions']
            },
            ReasoningDepth.HEAVY_FORGE: {
                'depth': 8,
                'blocks': ['objective', 'context', 'decomposition', 'leverage', 'strategy', 'execution', 'synthesis'],
                'description': 'Highly complex reasoning',
                'use_cases': ['Highly complex tasks', 'Low confidence', 'Critical decisions', 'Heavy forge mode']
            }
        }
        
        return configs.get(depth, configs[ReasoningDepth.STANDARD])
    
    @staticmethod
    def should_increase_depth(current_depth: ReasoningDepth, confidence: float, 
                             recent_failures: int = 0) -> bool:
        """Determine if reasoning depth should be increased"""
        # Increase if confidence is low for current depth
        depth_thresholds = {
            ReasoningDepth.MINIMAL: 0.95,
            ReasoningDepth.STANDARD: 0.85,
            ReasoningDepth.ENHANCED: 0.75
        }
        
        threshold = depth_thresholds.get(current_depth, 0.75)
        
        # Increase if confidence below threshold or recent failures
        return confidence < threshold or recent_failures >= 2
    
    @staticmethod
    def should_decrease_depth(current_depth: ReasoningDepth, confidence: float,
                              recent_successes: int = 0) -> bool:
        """Determine if reasoning depth should be decreased"""
        # Decrease if confidence is high and we're using more depth than needed
        if current_depth == ReasoningDepth.HEAVY_FORGE and confidence > 0.75:
            return True
        if current_depth == ReasoningDepth.ENHANCED and confidence > 0.85:
            return True
        if current_depth == ReasoningDepth.STANDARD and confidence > 0.95:
            return True
        
        # Also decrease if many recent successes
        return recent_successes >= 5


def main():
    """CLI interface for testing"""
    import sys
    
    adaptive = AdaptiveReasoning()
    
    if len(sys.argv) > 1:
        try:
            confidence = float(sys.argv[1])
            complexity = sys.argv[2] if len(sys.argv) > 2 else None
            
            depth = adaptive.determine_depth(confidence, complexity)
            config = adaptive.get_depth_config(depth)
            
            print(f"\n🧠 Adaptive Reasoning Depth Selection:")
            print(f"   Confidence: {confidence:.2%}")
            print(f"   Complexity: {complexity or 'inferred'}")
            print(f"   Selected Depth: {depth.name} ({config['depth']} blocks)")
            print(f"   Description: {config['description']}")
            print(f"   Blocks: {', '.join(config['blocks'])}")
        except ValueError:
            print("Usage: adaptive_reasoning.py <confidence> [complexity]")
            print("Example: adaptive_reasoning.py 0.75 complex")
    else:
        # Show all depth levels
        print("\n🧠 Adaptive Reasoning Depth Levels:\n")
        for depth in ReasoningDepth:
            config = adaptive.get_depth_config(depth)
            print(f"{depth.name} (Depth {config['depth']}):")
            print(f"  {config['description']}")
            print(f"  Blocks: {', '.join(config['blocks'])}")
            print()


if __name__ == "__main__":
    main()

