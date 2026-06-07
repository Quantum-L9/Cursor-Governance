---
name: l9-auditing-performance
description: audit and optimize application performance, including bundle size, rendering, database queries, and Core Web Vitals. use when the app is slow, profiling for bottlenecks, or optimizing bundle/render/query performance.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, performance, profiling, optimization, web-vitals]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
---

# Performance Audit

## Purpose

Profile and optimize application performance — bundle size, rendering, data fetching, database queries, assets, and Core Web Vitals. Profile first; optimize bottlenecks with measurable impact.

## Core Contract

| Area | Actions | Output |
|------|---------|--------|
| Bundle | Analyzer, tree-shaking, dup deps | Large dependency list |
| Render | Re-renders, memoization, keys | Hot component list |
| Data | Waterfalls, pagination, over-fetch | Fetch optimization list |
| Database | N+1, indexes, SELECT scope | Query fix list |
| Assets | Images, fonts, lazy load | Asset checklist |
| Report | Rank by impact × effort | [bottleneck-report-template.md](references/bottleneck-report-template.md) |

## Authority Order

1. Explicit user performance target (page, API, query, metric).
2. Measured evidence — Lighthouse, DevTools, profiler, EXPLAIN.
3. Repo stack conventions (Next.js, Vite, ORM, etc.).
4. This skill's steps and report template.
5. `Unknown` — profile before recommending changes.

## Steps

1. **Analyze bundle size**
   - Run `npx @next/bundle-analyzer` (Next.js) or `npx vite-bundle-visualizer` (Vite) to identify large dependencies.
   - Look for large libraries that could be replaced with lighter alternatives (e.g. `moment` → `date-fns`, `lodash` → individual imports or native methods).
   - Check for duplicated dependencies in the bundle.
   - Verify tree-shaking is working (no barrel file re-exports pulling in unused code).

2. **Audit rendering performance**
   - Identify components that re-render unnecessarily — look for inline object/array/function creation in JSX props.
   - Check for expensive computations in render paths that should use `useMemo`.
   - Verify lists use proper `key` props (not array index for dynamic lists).
   - Look for layout thrashing (reading DOM measurements then writing styles in a loop).

3. **Check data fetching**
   - Identify request waterfalls — sequential API calls that could be parallelized with `Promise.all`.
   - Look for data fetched on the client that could be fetched on the server.
   - Check for missing pagination on large data sets.
   - Verify API responses aren't over-fetching (returning fields the client doesn't need).

4. **Database query optimization**
   - Look for N+1 query patterns (a query per item in a list).
   - Check for missing indexes on columns used in WHERE, ORDER BY, and JOIN clauses.
   - Identify queries that could use `SELECT` with specific columns instead of `SELECT *`.
   - Look for missing connection pooling.

5. **Check assets**
   - Verify images use modern formats (WebP/AVIF) and are properly sized.
   - Check for missing `loading="lazy"` on below-the-fold images.
   - Verify fonts use `font-display: swap` and are preloaded.
   - Check for render-blocking CSS or JavaScript.

6. **Generate recommendations** — produce a prioritized list of optimizations ranked by impact (High / Medium / Low) with estimated effort for each. Use [references/bottleneck-report-template.md](references/bottleneck-report-template.md) for ranked output.

## Notes

- Focus on measurable improvements — use Lighthouse, WebPageTest, or the Performance tab in DevTools.
- Don't prematurely optimize — profile first, optimize bottlenecks.
- For React apps, use React DevTools Profiler to identify slow components.

## Resource Map

- [references/bottleneck-report-template.md](references/bottleneck-report-template.md) — ranked findings by impact and effort.

## Validation

Every recommendation MUST cite measurable evidence or name the profiling tool used. Rankings MUST use High / Medium / Low impact with estimated effort. Do not recommend optimizations without identifying a bottleneck first.

## Failure Handling

- No profiling data → run Lighthouse or DevTools first; do not guess bottlenecks.
- Stack unknown → detect from `package.json` / `pyproject.toml` before tool selection.
- User requests premature micro-optimization → redirect to profile step.
- Production-only slowness → ask for traces, APM screenshots, or reproducible local steps.
