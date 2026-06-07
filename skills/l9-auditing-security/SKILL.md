---
name: l9-auditing-security
description: perform a systematic security audit of a codebase, checking for OWASP Top 10 vulnerabilities, secrets exposure, and insecure patterns. use when reviewing code for security risks, scanning for exposed secrets, or hardening before release.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, security, audit, owasp, secrets]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
---

# Security Audit

## Purpose

Perform a systematic code-level security review: secrets exposure, auth/authz, injection, dependencies, headers, and data leakage. Code review — not penetration testing.

## Core Contract

| Check | Focus | Severity output |
|-------|-------|-----------------|
| Secrets | Hardcoded keys, committed `.env` | Critical / High |
| Auth | Route guards, password hashing, sessions | Critical / High |
| Injection | SQL, XSS, command, path traversal | Critical / High |
| Dependencies | `npm audit`, `pip audit`, CVEs | High / Medium |
| Headers | CORS, CSP, HSTS, frame options | Medium |
| Data exposure | API fields, errors, logs | High / Medium |

## Authority Order

1. Explicit user scope (paths, threat model, release gate).
2. OWASP Top 10 and repo security rules when present.
3. Automated scan output (`npm audit`, gitleaks, trivy) when available.
4. This skill's checklist below.
5. `Unknown` — recommend professional pentest for production-critical systems.

## Steps

1. **Scan for hardcoded secrets** — search for API keys, tokens, passwords, and connection strings in source files. Check for patterns like:
   - `password=`, `secret=`, `token=`, `api_key=`
   - Base64-encoded credentials
   - AWS keys (`AKIA...`), Stripe keys (`sk_live_...`), GitHub tokens (`ghp_...`)
   - Files: `.env` committed to git, `config.json` with credentials

2. **Check authentication & authorization**
   - Verify all API routes check authentication before processing.
   - Ensure role-based access control is enforced server-side, not just in the UI.
   - Check that password hashing uses bcrypt/argon2 (not MD5/SHA1).
   - Verify session tokens are HTTP-only, secure, and have reasonable expiry.

3. **Check for injection vulnerabilities**
   - **SQL injection**: look for string concatenation in SQL queries instead of parameterized queries.
   - **XSS**: look for `dangerouslySetInnerHTML`, `innerHTML`, or unescaped user input rendered in templates.
   - **Command injection**: look for `exec()`, `eval()`, `child_process.exec()` with user input.
   - **Path traversal**: check file operations for unsanitized user input in paths.

4. **Review dependency security**
   - Run `npm audit` or `pip audit` to check for known vulnerabilities.
   - Flag outdated dependencies with known CVEs.
   - Check for overly permissive dependency ranges.

5. **Check CORS and CSP configuration**
   - Verify CORS doesn't use `Access-Control-Allow-Origin: *` in production.
   - Check for Content Security Policy headers.
   - Verify `X-Frame-Options`, `X-Content-Type-Options`, and `Strict-Transport-Security` headers.

6. **Review data exposure**
   - Check API responses for leaking sensitive fields (password hashes, internal IDs, PII).
   - Verify error messages don't expose stack traces or internal details in production.
   - Check logging for sensitive data being written to logs.

7. **Generate report** — produce a summary with severity ratings (Critical / High / Medium / Low) for each finding, with the file path, line number, and recommended fix.

## Notes

- This is a code review, not a penetration test. Recommend tools like `npm audit`, `trivy`, or `snyk` for automated scanning.
- Always check `.gitignore` to ensure `.env`, credentials, and key files are excluded.
- For comprehensive auditing, recommend the OWASP Testing Guide.

## Resource Map

No `references/` folder — audit checklist and report format live in this file.

## Validation

Final report MUST list each finding with severity, file path, line (when applicable), and recommended fix. Secrets findings MUST be treated as Critical until proven false positive. Verify `.gitignore` excludes credentials.

## Failure Handling

- Live secrets in repo → flag Critical; do not echo full secret values in report.
- Scope too broad → prioritize auth, injection, and secrets first.
- No dependency lockfile → note limitation; run available audit tools only.
- User expects pentest → clarify this skill is static code review; recommend external tooling.
