"""Generic client for county/city open-data portals built on Socrata —
property records, tax assessments, and sale history published by
county assessors, recorders, and treasurers.

Socrata is a common backend for this kind of public data (Cook County,
NYC, LA County, and many others all run it), but each portal's domain
and dataset id are specific to that county, and each dataset's field
names vary. Find yours by browsing to the portal (e.g.
datacatalog.cookcountyil.gov), opening the dataset you want, and
copying its 4-4 character id out of the URL (looks like `abcd-1234`).

    from data_sources.county_open_data import fetch_records
    records = fetch_records(
        domain="datacatalog.cookcountyil.gov",
        dataset_id="93st-4bxh",  # confirm against the portal, not this file
        where="town_name = 'CHICAGO' AND sale_year >= 2023",
    )

Set an app token via the domain-specific env var pattern
`<DOMAIN_IN_CAPS>_APP_TOKEN` (dots become underscores) to raise
Socrata's rate limit; anonymous access works for light use.
"""
import json
import os
import re
import statistics
import urllib.error
import urllib.parse
import urllib.request


def _app_token_env_var(domain):
    return re.sub(r"\W", "_", domain).upper() + "_APP_TOKEN"


def fetch_records(domain, dataset_id, where=None, select=None, limit=1000, app_token=None):
    """Fetch records from a Socrata dataset via its SoQL query API."""
    if not domain:
        raise ValueError("fetch_records() requires a domain")
    if not dataset_id:
        raise ValueError("fetch_records() requires a dataset_id")

    params = {"$limit": limit}
    if where:
        params["$where"] = where
    if select:
        params["$select"] = select

    url = f"https://{domain}/resource/{dataset_id}.json?{urllib.parse.urlencode(params)}"
    headers = {}
    app_token = app_token or os.environ.get(_app_token_env_var(domain))
    if app_token:
        headers["X-App-Token"] = app_token

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ValueError(
            f"county open data request failed for {domain}/{dataset_id}: "
            f"{exc.code} {exc.reason}"
        ) from exc


def summarize_neighborhood_sales(records, price_field):
    """Turn raw county sale records into the comp-support inputs
    `deal_finder.analyze_property` uses for its confidence rating:
    `comparable_sale_count` and `comparable_value_spread_pct` (the
    interquartile-ish spread of sale prices, as a fraction of the
    median).

    `price_field` is whatever key holds the sale price in your
    dataset's records (e.g. "sale_price").
    """
    prices = []
    for record in records:
        raw_price = record.get(price_field)
        if raw_price in (None, ""):
            continue
        try:
            prices.append(float(raw_price))
        except (TypeError, ValueError):
            continue

    if not prices:
        return {"comparable_sale_count": 0, "comparable_value_spread_pct": None}

    median_price = statistics.median(prices)
    if len(prices) == 1 or median_price == 0:
        spread_pct = None
    else:
        spread_pct = (max(prices) - min(prices)) / median_price

    return {
        "comparable_sale_count": len(prices),
        "comparable_value_spread_pct": spread_pct,
        "comparable_median_price": median_price,
    }
