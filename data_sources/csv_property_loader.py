"""Generic loader for bulk property-data files that counties publish as
downloadable CSVs instead of a live API — e.g. Scott County, Iowa's
assessor bulk download
(https://www.scottcountyiowa.gov/assessor/property-data-bulk-download),
which ships as a set of linked files (base property data, sales
history, dwelling details, etc.) joined by a shared parcel id.

Column names vary by county and aren't guessed here: open the CSV you
downloaded, note its actual header names, and pass a `field_map` from
deal_finder's property keys to your file's column names.

    from data_sources.csv_property_loader import load_properties, merge_latest_by_key

    # base file (e.g. Scott County's "1-cert - base prop data")
    properties = load_properties(
        "1-cert.csv",
        field_map={
            "address": "SITE_ADDRESS",       # use your file's real headers
            "asking_price": "ASSESSED_VALUE",
            "sqft": "TOTAL_FINISHED_AREA",
        },
        key_field="PARCEL_ID",
    )

    # sales file (e.g. "9-cert - sales data"), one-to-many per parcel;
    # merge_latest_by_key keeps only the most recent sale per parcel
    properties = merge_latest_by_key(
        properties,
        "9-cert.csv",
        join_key_column="PARCEL_ID",
        date_column="SALE_DATE",
        field_map={"last_sale_year": "SALE_DATE"},
    )

Only `address` and the `field_map` keys you actually supply are
populated; everything else `deal_finder.analyze_property` needs
(stabilized_value, rehab assumptions, carrying costs, comps) still has
to come from elsewhere, since a tax/assessment file doesn't carry it.
"""
import csv


def load_properties(path, field_map, key_field=None, key_as="_parcel_id"):
    """Read a bulk property CSV and map its columns to deal_finder's
    property dict schema via `field_map` ({deal_finder_key: csv_column}).

    Numeric-looking values are converted to float; everything else is
    kept as a string. A `last_sale_year`-mapped column is parsed for a
    4-digit year out of whatever date format the file uses.

    Pass `key_field` (the CSV column holding the shared parcel/property
    id) to carry it through into each result under `key_as`, so
    `merge_latest_by_key` can later join in data from one of the
    county's other linked files.
    """
    if not field_map:
        raise ValueError("load_properties() requires a field_map")

    properties = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapped = _map_row(row, field_map)
            if key_field:
                mapped[key_as] = _normalize_key(row.get(key_field))
            properties.append(mapped)
    return properties


def merge_latest_by_key(properties, secondary_path, join_key_column, date_column, field_map, key_as="_parcel_id"):
    """Enrich `properties` (as returned by `load_properties(..., key_field=...)`)
    with fields from a one-to-many secondary CSV (e.g. a sales-history
    file), keeping only the most recent secondary row per parcel — the
    one with the lexicographically greatest `date_column` value (works
    for ISO-ish `YYYY-MM-DD` dates; reformat the file first if it uses a
    different layout).
    """
    if not field_map:
        raise ValueError("merge_latest_by_key() requires a field_map")

    latest_by_key = {}
    with open(secondary_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = _normalize_key(row.get(join_key_column))
            date_value = row.get(date_column) or ""
            if key not in latest_by_key or date_value > (latest_by_key[key].get(date_column) or ""):
                latest_by_key[key] = row

    merged = []
    for prop in properties:
        prop = dict(prop)
        secondary_row = latest_by_key.get(prop.get(key_as))
        if secondary_row:
            for deal_finder_key, csv_column in field_map.items():
                raw_value = secondary_row.get(csv_column)
                if raw_value in (None, ""):
                    continue
                if deal_finder_key == "last_sale_year":
                    prop[deal_finder_key] = _extract_year(raw_value)
                else:
                    prop[deal_finder_key] = _coerce_number(raw_value)
        merged.append(prop)
    return merged


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


def _normalize_key(value):
    """Strip surrounding whitespace from a join-key value — some county
    exports pad ids to a fixed width (e.g. `"010101001      "`)."""
    return value.strip() if isinstance(value, str) else value
