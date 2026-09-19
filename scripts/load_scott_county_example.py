"""Concrete example of loading real Scott County, Iowa assessor data
into deal_finder's property schema, based on the actual headers in the
county's bulk-download files (checked directly against the "1-cert -
base prop data" and "9-cert - sales data" files):

    1-cert: Parcel, Class, Class_Descr, ..., Prop_Hse_Num, Prop_Street, ...,
            Net_Assessed_Value, Total_Gba, ...
    9-cert: Parcel, Sale_Indx, Sale_Date, Adj_Sale_Amt, ..., Seller, Buyer

Both files download as .xlsx — convert each to CSV first (Excel:
File > Save As > CSV UTF-8) before running this script, since
data_sources.csv_property_loader reads CSV.

Usage:
    python scripts/load_scott_county_example.py 1-cert.csv 9-cert.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources.csv_property_loader import load_properties, merge_latest_by_key

BASE_FIELD_MAP = {
    "_house_num": "Prop_Hse_Num",
    "_street": "Prop_Street",
    "asking_price": "Net_Assessed_Value",
    "sqft": "Total_Gba",
}

SALES_FIELD_MAP = {
    "last_sale_year": "Sale_Date",
}


def main():
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {sys.argv[0]} 1-cert.csv 9-cert.csv")

    base_path, sales_path = sys.argv[1], sys.argv[2]

    properties = load_properties(base_path, field_map=BASE_FIELD_MAP, key_field="Parcel")
    properties = merge_latest_by_key(
        properties, sales_path, join_key_column="Parcel", date_column="Sale_Date",
        field_map=SALES_FIELD_MAP,
    )

    for prop in properties:
        house_num = _clean_str(prop.pop("_house_num", None))
        street = _clean_str(prop.pop("_street", None))
        prop["address"] = f"{house_num} {street}".strip()

    for prop in properties[:5]:
        print(prop)
    print(f"... {len(properties)} properties total")


def _clean_str(value):
    """csv_property_loader coerces numeric-looking columns (like a house
    number) to float; put it back to a plain string for display."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


if __name__ == "__main__":
    main()
