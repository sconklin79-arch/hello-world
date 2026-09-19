"""Run deal_finder's funnel over a JSON list of property records and
print a summary of each stage's survivors.

Usage:
    python scripts/run_deal_funnel.py [path/to/properties.json]

    # optionally enrich each property's comp confidence from a real
    # county open-data portal before scoring (see data_sources/county_open_data.py
    # for how to find a domain/dataset id for your own county):
    python scripts/run_deal_funnel.py --county-domain datacatalog.cookcountyil.gov \\
        --county-dataset-id 93st-4bxh --county-price-field sale_price \\
        --county-where-template "upper(property_address) like upper('%{address}%')"

Defaults to sample_properties.json in the repo root. County enrichment is
opt-in and best-effort: if a lookup fails (bad domain/dataset id, no
network access) it prints a warning and leaves that property's comp
inputs as given in the JSON, rather than aborting the whole run.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources.county_open_data import fetch_records, summarize_neighborhood_sales
from deal_finder import analyze_property, run_funnel


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "properties_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "sample_properties.json"),
    )
    parser.add_argument("--county-domain", help="Socrata open-data domain, e.g. datacatalog.cookcountyil.gov")
    parser.add_argument("--county-dataset-id", help="Socrata dataset id, e.g. 93st-4bxh")
    parser.add_argument("--county-price-field", default="sale_price", help="Sale-price field name in that dataset")
    parser.add_argument(
        "--county-where-template",
        default="upper(address) like upper('%{address}%')",
        help="SoQL $where clause template; {address} is replaced with the property's address",
    )
    return parser.parse_args()


def enrich_with_county_comps(prop, domain, dataset_id, price_field, where_template):
    address = prop.get("address")
    if not address:
        return prop

    try:
        records = fetch_records(
            domain=domain, dataset_id=dataset_id, where=where_template.format(address=address)
        )
        comp_summary = summarize_neighborhood_sales(records, price_field)
    except ValueError as exc:
        print(f"  (county comp lookup failed for {address}: {exc})")
        return prop

    enriched = dict(prop)
    enriched["comparable_sale_count"] = comp_summary["comparable_sale_count"]
    enriched["comparable_value_spread_pct"] = comp_summary["comparable_value_spread_pct"]
    return enriched


def main():
    args = parse_args()
    with open(args.properties_path) as f:
        properties = json.load(f)

    if args.county_domain and args.county_dataset_id:
        properties = [
            enrich_with_county_comps(
                prop, args.county_domain, args.county_dataset_id,
                args.county_price_field, args.county_where_template,
            )
            for prop in properties
        ]

    stage_sizes = tuple(size for size in (500, 100, 25, 8, 3) if size <= len(properties))
    stages = run_funnel(properties, stage_sizes=stage_sizes)

    for size, stage in zip(stage_sizes, stages):
        print(f"\n=== Top {size} ===")
        for prop in stage:
            analysis = analyze_property(prop)
            print(f"{prop.get('address', '(unknown)')}")
            print(f"  Asking: ${analysis['asking_price']:,.0f}")
            print(f"  Estimated stabilized value: ${analysis['stabilized_value']:,.0f}")
            print(f"  Estimated rehab: ${analysis['rehab_cost']:,.0f}")
            print(f"  Acquisition + rehab + carrying: ${analysis['total_cost']:,.0f}")
            print(f"  Potential gross spread: ${analysis['spread']:,.0f}")
            print(f"  Confidence: {analysis['confidence']}")
            if analysis["reasons"]:
                print(f"  Why it surfaced: {', '.join(analysis['reasons'])}")


if __name__ == "__main__":
    main()
