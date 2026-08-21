---
name: ""
overview: ""
todos: []
isProject: false
---

Here's your rewritten plan — copy and paste directly:

---

```markdown
# Harden Geo Backfill Cron for Rate Limiting

## Problem Summary

The `cron_geo_backfill` in `plasticos_geolocalize/models/res_partner_geo.py` is getting
HTTP 429 (Too Many Requests) from OpenStreetMap Nominatim on every request. Nominatim
returns an HTML error page, `response.json()` chokes on it, and `base_geolocalize` wraps
the `JSONDecodeError` in a `UserError`. The current implementation:

- Has no early-abort logic — continues hammering the API after consecutive failures
- Has no backoff — uses fixed 1.1s delay even after failures
- Never commits progress — if the worker times out, all successful geocodes are lost
- Uses BATCH_SIZE=100 which holds an Odoo worker hostage for the full loop duration
- Will retry the same failing partners every night forever with no deprioritization

The root cause is that Odoo.sh shared IPs are rate-limited/banned by Nominatim's CDN
(Varnish). The hardened cron won't fix that, but it will fail fast and stop wasting
worker time.

## Files Changed

### 1. `plasticos_geolocalize/models/res_partner_geo.py`

**Full method rewrite of `cron_geo_backfill`:**

- Reduce `BATCH_SIZE` from 100 → 50 (less worker hold time)
- Add `MAX_CONSECUTIVE_FAILURES = 3` — abort the batch when hit
- Add `FAILURE_DELAY = 5.0` — longer fixed cooldown after each failure
- Add `self.env.cr.commit()` after each successful geocode so progress survives
  worker timeouts or cron kills (with `# pylint: disable=invalid-commit`)
- Reset `consecutive_failures` counter to 0 on any success
- On abort, log at ERROR level with explicit "likely rate-limited" message
- Move all tuning constants to module level for visibility

**Before (current):**
```python
_NOMINATIM_DELAY_SECONDS = 1.1

@api.model
def cron_geo_backfill(self):
    BATCH_SIZE = 100
    # ... searches partners ...
    for partner in partners:
        try:
            partner.geo_localize()
            if partner.partner_latitude:
                success += 1
            time.sleep(_NOMINATIM_DELAY_SECONDS)
        except Exception:
            failed += 1
            _logger.warning(...)
            time.sleep(_NOMINATIM_DELAY_SECONDS)
```

**After (replacement):**

```python
_NOMINATIM_DELAY = 1.1
_FAILURE_DELAY = 5.0
_MAX_CONSECUTIVE_FAIL = 3
_BATCH_SIZE = 50

@api.model
def cron_geo_backfill(self):
    domain = [
        ("partner_latitude", "in", [0.0, False]),
        "|",
        ("street", "!=", False),
        ("city", "!=", False),
    ]
    partners = self.search(domain, limit=_BATCH_SIZE)
    if not partners:
        _logger.info("Geo backfill: no partners need geocoding.")
        return

    success = 0
    failed = 0
    consecutive_failures = 0

    for partner in partners:
        try:
            partner.geo_localize()
            if partner.partner_latitude:
                success += 1
                consecutive_failures = 0
                self.env.cr.commit()  # pylint: disable=invalid-commit
            time.sleep(_NOMINATIM_DELAY)
        except Exception:
            failed += 1
            consecutive_failures += 1
            _logger.warning(
                "Geo backfill: failed for partner %s (%s).",
                partner.id, partner.name, exc_info=True,
            )
            if consecutive_failures >= _MAX_CONSECUTIVE_FAIL:
                _logger.error(
                    "Geo backfill: %d consecutive failures — "
                    "aborting (likely rate-limited or banned).",
                    consecutive_failures,
                )
                break
            time.sleep(_FAILURE_DELAY)

    _logger.info(
        "Geo backfill complete: %d/%d geocoded, %d failed.",
        success, len(partners), failed,
    )
```

### 2. No other files changed

The cron XML at `plasticos_geolocalize/data/cron_geo_backfill.xml` does not need changes.
The `__manifest__.py` does not need changes. No new dependencies.

## What This Does NOT Fix

The 429s are caused by Nominatim blocking Odoo.sh shared IPs at the CDN level. This
hardening makes the cron fail fast (~15s instead of ~47s) and preserve progress, but
the actual geocoding will remain broken until one of these is done:

- **Switch geocoding provider** in Settings → Technical → Geolocation to Google Maps
or MapBox (config change, zero code, recommended)
- **Or** self-host a Nominatim instance and point `base_geolocalize` at it

Those are separate tasks and out of scope for this change.

## Verification

After deploying, trigger the cron manually and check logs for:

- `Geo backfill: 3 consecutive failures — aborting (likely rate-limited or banned).`
confirms early abort is working
- Total runtime should be ~15s instead of ~47s
- If a paid provider is configured later, look for `Geo backfill complete: N/50 geocoded, 0 failed.` with `cr.commit()` keeping progress across runs

```

```

