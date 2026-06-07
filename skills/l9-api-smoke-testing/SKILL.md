---
name: l9-api-smoke-testing
description: start the dev server, discover API routes from the codebase, hit every endpoint, and report which ones return errors. use when verifying API health after changes, smoke-testing endpoints, or hunting 404/500 regressions across routes.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, api, testing, smoke-test, http]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
---

# API Smoke Testing

## Purpose

Verify all API endpoints return healthy responses by combining codebase route discovery with live HTTP requests. Report regressions (404/500) and fix root causes when requested.

## Core Contract

| Phase | Output |
|-------|--------|
| Discover | Route list with HTTP methods from codebase |
| Smoke | Status code per endpoint |
| Classify | OK / auth-expected / bug |
| Report | Summary table with error details |
| Fix | Stack-trace-driven patch for 500/404 bugs |

## Authority Order

1. Explicit user server URL, port, and auth requirements.
2. Route definitions in repo — source of truth for expected endpoints.
3. Live HTTP responses — classify against actual status codes.
4. Terminal/server logs for 500 root cause.
5. `Unknown` — ask before hitting production or authenticated routes without credentials.

## Workflow

### 1. Discover Routes

Search the codebase for API route definitions:

**Next.js (App Router):** `app/api/**/route.ts`
**Next.js (Pages Router):** `pages/api/**/*.ts`
**Express:** Look for `app.get(`, `app.post(`, `router.get(`, etc.
**Django:** Look for `urlpatterns` in `urls.py`
**FastAPI:** Look for `@app.get(`, `@app.post(`, decorators
**Rails:** Look for `routes.rb`

Build a list of endpoints with their HTTP methods.

### 2. Ensure Server is Running

Check terminal files for a running dev server. If none found, start one.

### 3. Hit Every Endpoint

For each route:

```bash
curl -s -o /dev/null -w "%{http_code}" -X <METHOD> http://localhost:<PORT><PATH>
```

For endpoints that require a body (POST/PUT/PATCH), send a minimal valid JSON:

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:<PORT><PATH> \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 4. Classify Results

| Status | Meaning |
|--------|---------|
| 200-299 | OK |
| 301/302 | Redirect (OK) |
| 400 | Bad request (expected for empty POST bodies) |
| 401/403 | Auth required (expected for protected routes) |
| 404 | Route not found (BUG — route exists in code but not served) |
| 500 | Server error (BUG) |
| 000/timeout | Server not responding (BUG) |

### 5. Report

```
API Smoke Test Results:
  Tested: 15 endpoints
  Passed: 12
  Auth required: 2 (GET /api/user, POST /api/settings)
  Errors:
    500 — POST /api/webhooks/stripe (TypeError: Cannot read property 'id' of undefined)
    404 — GET /api/v2/health (route defined but not mounted)
```

### 6. Fix Errors

For 500 errors, read the terminal output for the stack trace and fix the root cause. For 404s, check that the route file is in the correct location and properly exported.

## Resource Map

No `references/` folder — workflow and status classification live in this file.

## Validation

Every discovered route MUST be hit at least once. Report MUST separate auth-expected (401/403) from bugs (404/500/timeout). 500 findings MUST include the error message or stack trace excerpt.

## Failure Handling

- Server not running → start dev server or ask user for URL/port.
- Auth-required routes without credentials → classify as auth-expected; do not mark as bug.
- Cannot discover routes → search by framework patterns; ask user for router entrypoint if ambiguous.
- Production URL requested → confirm explicitly before sending requests.
