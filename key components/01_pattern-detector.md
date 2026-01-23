---
title: Pattern Detector
purpose: Identify and extract reusable patterns from workflows or reasoning
summary: Scans content for structural or logic patterns and annotates them for reuse
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: 01_ultimate-master-guide.md
tags: [reasoning, pattern-detection, productivity]
domain: reasoning
type: analyzer
production_ready: true
---

## 🧠 USE CASE
Use this tool when reviewing logic chains or workflows to extract reusable patterns or heuristics.

## 🔁 USAGE
- Accepts markdown, YAML, JSON, or L9 exported nodes.
- Detects:
  - Repeated node structures
  - Reasoning chains (e.g. "if → validate → mutate → return")
  - Reusable field patterns (e.g. `SM#####`)
- Annotates and indexes into pattern memory

## ⛓️ COMMAND
```bash
run-pattern-detector --input ./workflow.md --output ./patterns/patterns_v1.md
```