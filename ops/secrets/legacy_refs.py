"""Legacy AWS ref -> Infisical name map (ADR-0053, CANONICAL_LAW §14.1).

Infisical project ``cursor-governance`` is the secret store. Older law, docs
and callers name secrets by their legacy AWS Secrets Manager ref,
``openclaw-igorbot/<service>#<json_key>``. This module is the one place that
says which Infisical name such a ref means, so following a legacy ref lands on
Infisical, never on AWS. ``port_aws_to_infisical.py`` (the one-way port) and
``capability_bind.py --check`` both read it.

Data only: no AWS import, no network, no values.
"""

from __future__ import annotations

import re

LEGACY_NAMESPACE = "openclaw-igorbot"

#: (service, json_key) -> Infisical env-var name at path ``/``.
ENV_MAP: dict[tuple[str, str], str] = {
    ("anthropic", "apikey"): "ANTHROPIC_API_KEY",
    ("ceg", "API_SECRET_KEY"): "CEG_API_KEY",
    ("clawhub", "token"): "CLAWHUB_API_KEY",
    ("cloudflare", "apitoken"): "CLOUDFLARE_API_TOKEN",
    ("cloudflare", "accountid"): "CLOUDFLARE_ACCOUNT_ID",
    ("coderabbit", "apikey"): "CODERABBIT_API_KEY",
    ("context7", "apikey"): "CONTEXT7_API_KEY",
    ("coolify", "apikey"): "COOLIFY_TOKEN",
    ("coolify", "url"): "COOLIFY_API_URL",
    ("dataforseo", "apikey"): "DATAFORSEO_API_KEY",
    ("dataforseo", "login"): "DATAFORSEO_LOGIN",
    ("dataforseo", "password"): "DATAFORSEO_PASSWORD",
    ("deepseek", "apikey"): "DEEPSEEK_API_KEY",
    ("emma-telegram", "botToken"): "EMMA_TELEGRAM_BOT_TOKEN",
    ("gitguardian", "apikey"): "GITGUARDIAN_API_KEY",
    ("gemini", "apikey"): "GEMINI_API_KEY",
    ("github", "token"): "GITHUB_TOKEN",
    ("google-places", "apikey"): "GOOGLE_PLACES_API_KEY",
    ("hetzner", "apitoken"): "HCLOUD_TOKEN",
    ("igorbot-gateway-secret", "token"): "IGORBOT_GATEWAY_TOKEN",
    ("mistral", "apikey"): "MISTRAL_API_KEY",
    ("n8n", "api_key"): "N8N_API_KEY",
    ("n8n", "api_url"): "N8N_API_URL",
    ("n8n", "workflow_host"): "N8N_WORKFLOW_HOST",
    ("nano-banana-pro", "apiKey"): "NANO_BANANA_API_KEY",
    ("neo4j", "password"): "NEO4J_PASSWORD",
    ("neo4j", "uri"): "NEO4J_URI",
    ("notion", "token"): "NOTION_API_KEY",
    ("odoo-web-lead", "api_key"): "ODOO_WEB_LEAD_API_KEY",
    ("odoo-web-lead", "api_url"): "ODOO_WEB_LEAD_API_URL",
    ("odoo-web-lead", "environment"): "ODOO_WEB_LEAD_ENVIRONMENT",
    ("odoo-web-lead", "webhook_path"): "ODOO_WEB_LEAD_WEBHOOK_PATH",
    ("openai", "apikey"): "OPENAI_API_KEY",
    ("openai-whisper", "apiKey"): "OPENAI_WHISPER_API_KEY",
    ("openrouter", "apikey"): "OPENROUTER_API_KEY",
    ("pagespeed", "apikey"): "PAGESPEED_API_KEY",
    ("perplexity", "apikey"): "PERPLEXITY_API_KEY",
    ("posthog", "host"): "POSTHOG_HOST",
    ("posthog", "personal_api_key"): "POSTHOG_PERSONAL_API_KEY",
    ("posthog", "project_api_key"): "POSTHOG_PROJECT_API_KEY",
    ("posthog", "project_id"): "POSTHOG_PROJECT_ID",
    ("pypi", "token"): "PYPI_TOKEN",
    ("pypi", "username"): "PYPI_USERNAME",
    ("semgrep", "token"): "SEMGREP_APP_TOKEN",
    ("seo-bot", "apikey"): "SEO_BOT_API_KEY",
    ("sonarcloud", "token"): "SONAR_TOKEN",
    ("stripe", "apikey"): "STRIPE_API_KEY",
    ("telegram", "bottoken"): "TELEGRAM_BOT_TOKEN",
    ("telegram-allowed-users", "ids"): "TELEGRAM_ALLOWED_USER_IDS",
    ("telegram-chat-id", "id"): "TELEGRAM_CHAT_ID",
    ("vercel", "token"): "VERCEL_TOKEN",
}

_REF_RE = re.compile(r"^" + re.escape(LEGACY_NAMESPACE) + r"/([A-Za-z0-9._-]+)#([A-Za-z0-9._-]+)$")


_SECRET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"K_{cleaned}"
    if not cleaned:
        cleaned = "VALUE"
    if not _SECRET_NAME_RE.match(cleaned):
        cleaned = "VALUE"
    return cleaned


def env_name(suffix: str, json_key: str) -> str:
    """The Infisical name the port tool gave ``<suffix>#<json_key>``.

    Explicit ``ENV_MAP`` entries first, then the same deterministic fallback
    the port applied (``<SUFFIX>_API_KEY`` / ``<SUFFIX>_TOKEN`` /
    ``<SUFFIX>_<KEY>``), so every ported ref translates the way it was ported.
    """
    mapped = ENV_MAP.get((suffix, json_key))
    if mapped:
        return mapped
    suffix_u = sanitize_key(suffix.replace("-", "_")).upper()
    key_u = sanitize_key(json_key).upper()
    if key_u in {"APIKEY", "API_KEY"}:
        return f"{suffix_u}_API_KEY"
    if key_u in {"TOKEN", "APITOKEN", "API_TOKEN"}:
        return f"{suffix_u}_TOKEN"
    return f"{suffix_u}_{key_u}"


def is_legacy_ref(text: str) -> bool:
    return bool(_REF_RE.match(text.strip()))


def infisical_name(ref: str) -> str | None:
    """The Infisical name a legacy ``openclaw-igorbot/<svc>#<key>`` ref means.

    The caller still gates the result: ``capability_bind`` only binds names in
    ``root_env_keys``, so a translated name that was never ported checks as
    ``<not-in-inventory>``.
    """
    match = _REF_RE.match(ref.strip())
    if not match:
        return None
    return env_name(match.group(1), match.group(2))
