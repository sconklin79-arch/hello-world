"""Client for MRED (Midwest Real Estate Data), a RESO Web API MLS feed.

Requires real MRED/RESO Web API credentials — this module does not embed
or fabricate any. Configure them via environment variables (or pass them
in directly):

    MRED_CLIENT_ID       OAuth2 client id issued by MRED/your vendor
    MRED_CLIENT_SECRET   OAuth2 client secret
    MRED_TOKEN_URL       OAuth2 token endpoint (client_credentials grant)
    MRED_BASE_URL        RESO Web API base URL, e.g. https://api.mlsgrid.com/v2

Nothing in this module makes a network call at import time, and every
function raises `ValueError` up front if the credentials it needs are
missing, rather than silently hitting the network with bad auth.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

_ENV_CLIENT_ID = "MRED_CLIENT_ID"
_ENV_CLIENT_SECRET = "MRED_CLIENT_SECRET"
_ENV_TOKEN_URL = "MRED_TOKEN_URL"
_ENV_BASE_URL = "MRED_BASE_URL"


def _require(value, name):
    if not value:
        raise ValueError(f"{name} is required (set it or the {name} env var)")
    return value


def get_access_token(client_id=None, client_secret=None, token_url=None):
    """Fetch an OAuth2 access token via the client_credentials grant."""
    client_id = _require(client_id or os.environ.get(_ENV_CLIENT_ID), _ENV_CLIENT_ID)
    client_secret = _require(
        client_secret or os.environ.get(_ENV_CLIENT_SECRET), _ENV_CLIENT_SECRET
    )
    token_url = _require(token_url or os.environ.get(_ENV_TOKEN_URL), _ENV_TOKEN_URL)

    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api",
        }
    ).encode()
    request = urllib.request.Request(
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"MRED token request failed: {exc.code} {exc.reason}") from exc

    if "access_token" not in payload:
        raise ValueError(f"MRED token response missing access_token: {payload!r}")
    return payload["access_token"]


def fetch_listings(access_token, base_url=None, odata_filter=None, top=50):
    """Fetch raw RESO Property resources from the MLS Web API.

    `odata_filter` is a raw OData `$filter` expression, e.g.
    "StandardStatus eq 'Active' and City eq 'Chicago'".
    """
    access_token = _require(access_token, "access_token")
    base_url = _require(base_url or os.environ.get(_ENV_BASE_URL), _ENV_BASE_URL)

    params = {"$top": top}
    if odata_filter:
        params["$filter"] = odata_filter
    url = f"{base_url.rstrip('/')}/Property?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"MRED listings request failed: {exc.code} {exc.reason}") from exc

    return payload.get("value", [])


def normalize_listing(raw):
    """Map a raw RESO `Property` resource to the property dict schema
    that `deal_finder.analyze_property` expects.

    This fills in what the MLS feed can tell us directly (asking price,
    days on market, address, prior sale info where present) and leaves
    fields the MLS doesn't carry — stabilized value, rehab assumptions,
    carrying costs, comps — for the caller to supply from other sources.
    """
    return {
        "address": raw.get("UnparsedAddress"),
        "asking_price": raw.get("ListPrice"),
        "days_on_market": raw.get("DaysOnMarket"),
        "was_expired_or_withdrawn": raw.get("StandardStatus")
        in ("Expired", "Withdrawn", "Canceled"),
        "last_sale_year": _year_from_date(raw.get("PurchaseContractDate")),
        "sqft": raw.get("LivingArea"),
        "_mred_listing_key": raw.get("ListingKey"),
        "_mred_status": raw.get("StandardStatus"),
    }


def _year_from_date(date_str):
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (TypeError, ValueError):
        return None
