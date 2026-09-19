"""Client for the City of Chicago's public Socrata open-data portal —
building permits and building-code violations, to enrich MRED listings
with motivation signals (deferred maintenance, active violations).

No API key is required for light use; set CHICAGO_APP_TOKEN to raise
Socrata's rate limit if you're pulling a lot of data.

Dataset IDs (stable, published by the city):
  ydr8-5enu — Building Permits
  22u3-xenr — Building Violations
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

_BASE_URL = "https://data.cityofchicago.org/resource"
_PERMITS_DATASET = "ydr8-5enu"
_VIOLATIONS_DATASET = "22u3-xenr"
_ENV_APP_TOKEN = "CHICAGO_APP_TOKEN"


def _get(dataset_id, params):
    url = f"{_BASE_URL}/{dataset_id}.json?{urllib.parse.urlencode(params)}"
    headers = {}
    app_token = os.environ.get(_ENV_APP_TOKEN)
    if app_token:
        headers["X-App-Token"] = app_token

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ValueError(
            f"Chicago open data request failed: {exc.code} {exc.reason}"
        ) from exc


def fetch_permits(address, limit=50):
    """Building permits filed for `address` (matched with a SQL LIKE)."""
    if not address:
        raise ValueError("fetch_permits() requires an address")
    params = {"$where": f"upper(street_name) like upper('%{address}%')", "$limit": limit}
    return _get(_PERMITS_DATASET, params)


def fetch_violations(address, limit=50):
    """Open/closed building-code violations for `address`."""
    if not address:
        raise ValueError("fetch_violations() requires an address")
    params = {"$where": f"upper(address) like upper('%{address}%')", "$limit": limit}
    return _get(_VIOLATIONS_DATASET, params)


def enrich_property(property_data, permits, violations):
    """Merge permit/violation signals into a property dict for
    `deal_finder.analyze_property` — a nonempty open-violation list sets
    `has_code_violations`, and permit history is exposed as counts so
    callers can factor "no permits pulled in 20 years" into rehab risk.
    """
    enriched = dict(property_data)
    open_violations = [
        v for v in violations if v.get("violation_status", "").upper() == "OPEN"
    ]
    enriched["has_code_violations"] = len(open_violations) > 0
    enriched["_open_code_violation_count"] = len(open_violations)
    enriched["_permit_count"] = len(permits)
    return enriched
