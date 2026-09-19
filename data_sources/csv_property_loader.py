"""Generic loader for bulk property-data files that counties publish as
downloadable CSVs instead of a live API — e.g. Scott County, Iowa's
assessor bulk download
(https://www.scottcountyiowa.gov/assessor/property-data-bulk-download).

Column names vary by county and aren't guessed here: open the CSV you
downloaded, note its actual header names, and pass a `field_map` from
deal_finder's property keys to your file's column names.

    from data_sources.csv_property_loader import load_properties

    properties = load_properties(
        "scott_county_parcels.csv",
        field_map={
            "address": "SITE_ADDRESS",       # use your file's real headers
            "asking_price": "ASSESSED_VALUE",
            "sqft": "TOTAL_FINISHED_AREA",
            "last_sale_year": "SALE_DATE",   # a date column; only the year is kept
        },
    )

Only `address` and `field_map` keys you actually supply are populated;
everything else `deal_finder.analyze_property` needs (stabilized_value,
rehab assumptions, carrying costs, comps) still has to come from
elsewhere, since a tax/assessment file doesn't carry it.
"""
import csv


def load_properties(path, field_map):
    """Read a bulk property CSV and map its columns to deal_finder's
    property dict schema via `field_map` ({deal_finder_key: csv_column}).

    Numeric-looking values are converted to float; everything else is
    kept as a string. A `last_sale_year`-mapped column is parsed for a
    4-digit year out of whatever date format the file uses.
    """
    if not field_map:
        raise ValueError("load_properties() requires a field_map")

    properties = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            properties.append(_map_row(row, field_map))
    return properties


def _map_row(row, field_map):
    mapped = {}
    for deal_finder_key, csv_column in field_map.items():
        raw_value = row.get(csv_column)
        if raw_value in (None, ""):
            mapped[deal_finder_key] = None
            continue

        if deal_finder_key == "last_sale_year":
            mapped[deal_finder_key] = _extract_year(raw_value)
        else:
            mapped[deal_finder_key] = _coerce_number(raw_value)
    return mapped


def _coerce_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _extract_year(date_str):
    digit_groups = "".join(c if c.isdigit() else " " for c in date_str).split()
    for group in digit_groups:
        if len(group) == 4:
            return int(group)
    return None
