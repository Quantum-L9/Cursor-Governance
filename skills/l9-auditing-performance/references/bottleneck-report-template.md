<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-auditing-performance
layer: reference
role: report_template
tags: [performance, bottleneck, profiling, optimization]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
sources:
  - harvested: analysis-performance-profile (Suite-5 legacy, stripped n8n/vendor metrics)
--- /SKILL_META ---

Purpose:
Ranked bottleneck report after profiling — web, API, DB, or batch jobs.
-->

# Bottleneck Report Template

Profile first (Lighthouse, DevTools, query logs, APM). Then fill this template.

## Executive Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| {primary latency or LCP} | | | ✅ / ⚠️ / 🔴 |
| Error / timeout rate | | | |
| P95 / P99 (if available) | | | |

**Performance score:** {0–100} — {EXCELLENT | NEEDS WORK | CRITICAL}

## Ranked Bottlenecks

Impact score (optional): `(downstream_blocked × 2) + upstream_unlocked + cross_impact`

| Rank | Bottleneck | Impact | Frequency | Evidence | Recommendation |
|------|------------|--------|-----------|----------|----------------|
| 1 | | HIGH / MED / LOW | | file:line or trace | |
| 2 | | | | | |

## Optimization Backlog

| # | Fix | Est. effort | Expected gain | Auto? |
|---|-----|-------------|---------------|-------|
| 1 | | <1h / 1–4h / >4h | | 🤖 / 🔧 / 👤 |

## Rules

- Do not recommend optimizations without measured evidence.
- Prefer highest impact × lowest effort first.
- For DB: always check N+1 and missing indexes before micro-optimizations.
