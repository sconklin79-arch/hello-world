"""Client for the Zenlist listings API.

Requires a real Zenlist API key — this module does not embed or fabricate
one. Configure it via the ZENLIST_API_KEY environment variable (set as a
GitHub Actions secret for CI, or in your own shell for local use), or pass
it directly to the functions below.

    ZENLIST_API_KEY   your Zenlist API key
    ZENLIST_BASE_URL  API base URL (defaults to https://api.zenlist.com/v1)

Note: this module targets Zenlist's public listings API shape as
documented at https://zenlist.com — confirm the exact endpoint path and
response fields against your account's API docs before relying on this in
production, since API details can vary by plan/version. Nothing here
makes a network call at import time, and every function raises
`ValueError` up front if the key it needs is missing.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

_ENV_API_KEY = "ZENLIST_API_KEY"
_ENV_BASE_URL = "ZENLIST_BASE_URL"
_DEFAULT_BASE_URL = "https://api.zenlist.com/v1"


def _require(value, name):
    if not value:
        raise ValueError(f"{name} is required (set it or the {name} env var)")
    return value


def fetch_listings(api_key=None, base_url=None, params=None, limit=50):
    """Fetch raw listing records from the Zenlist API."""
    api_key = _require(api_key or os.environ.get(_ENV_API_KEY), _ENV_API_KEY)
    base_url = base_url or os.environ.get(_ENV_BASE_URL) or _DEFAULT_BASE_URL

    query = dict(params or {})
    query["limit"] = limit
    url = f"{base_url.rstrip('/')}/listings?{urllib.parse.urlencode(query)}"

    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Zenlist listings request failed: {exc.code} {exc.reason}") from exc

    return payload.get("listings", payload.get("data", []))


def normalize_listing(raw):
    """Map a raw Zenlist listing record to the property dict schema that
    `deal_finder.analyze_property` expects.

    Fills in what Zenlist can tell us directly (asking price, days on
    market, address, listing status, prior sale info where present) and
    leaves fields it doesn't carry — stabilized value, rehab assumptions,
    carrying costs, comps — for the caller to supply from other sources.
    """
    return {
        "address": raw.get("address") or raw.get("full_address"),
        "asking_price": raw.get("price") or raw.get("list_price"),
        "days_on_market": raw.get("days_on_market"),
        "was_expired_or_withdrawn": raw.get("status") in ("expired", "withdrawn", "canceled"),
        "last_sale_year": _year_from_date(raw.get("last_sold_date")),
        "sqft": raw.get("square_feet") or raw.get("sqft"),
        "_zenlist_listing_id": raw.get("id"),
        "_zenlist_status": raw.get("status"),
    }


def _year_from_date(date_str):
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (TypeError, ValueError):
        return None
