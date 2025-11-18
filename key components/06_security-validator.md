---
title: Security Validator
purpose: Ensure secure credentials and patterns in n8n and infrastructure
summary: Scans for security misconfigurations, secret exposures, and weak patterns
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: 06_security-validator.md
tags: [security, validator, n8n]
domain: security
type: scanner
production_ready: true
---

## 🔒 VALIDATION CHECKS
- Supabase: `predefinedCredentialType` used (no manual headers)
- No hardcoded API keys
- Valid secret paths for all services
- n8n node naming conforms (no emojis, sensitive names)

## 📜 RUN IT
```bash
validate-security --project ./ --output ./logs/security_audit.md
```