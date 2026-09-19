import csv
import os
import tempfile
import unittest

from data_sources.csv_property_loader import load_properties, merge_latest_by_key


class CsvPropertyLoaderTest(unittest.TestCase):
    def _write_csv(self, rows, fieldnames):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(os.remove, path)
        return path

    def test_requires_field_map(self):
        with self.assertRaises(ValueError):
            load_properties("anything.csv", field_map=None)

    def test_maps_columns_and_coerces_numbers(self):
        path = self._write_csv(
            [{"SITE_ADDRESS": "1 Main St", "ASSESSED_VALUE": "185000", "TOTAL_FINISHED_AREA": "1500"}],
            fieldnames=["SITE_ADDRESS", "ASSESSED_VALUE", "TOTAL_FINISHED_AREA"],
        )
        properties = load_properties(
            path,
            field_map={
                "address": "SITE_ADDRESS",
                "asking_price": "ASSESSED_VALUE",
                "sqft": "TOTAL_FINISHED_AREA",
            },
        )
        self.assertEqual(len(properties), 1)
        prop = properties[0]
        self.assertEqual(prop["address"], "1 Main St")
        self.assertEqual(prop["asking_price"], 185000.0)
        self.assertEqual(prop["sqft"], 1500.0)

    def test_extracts_sale_year_from_date_column(self):
        path = self._write_csv(
            [{"ADDR": "2 Oak Ave", "SALE_DATE": "06/15/2007"}],
            fieldnames=["ADDR", "SALE_DATE"],
        )
        properties = load_properties(
            path, field_map={"address": "ADDR", "last_sale_year": "SALE_DATE"}
        )
        self.assertEqual(properties[0]["last_sale_year"], 2007)

    def test_missing_values_become_none(self):
        path = self._write_csv(
            [{"ADDR": "3 Pine Rd", "ASSESSED_VALUE": ""}],
            fieldnames=["ADDR", "ASSESSED_VALUE"],
        )
        properties = load_properties(
            path, field_map={"address": "ADDR", "asking_price": "ASSESSED_VALUE"}
        )
        self.assertIsNone(properties[0]["asking_price"])

    def test_loads_multiple_rows(self):
        path = self._write_csv(
            [{"ADDR": "1 A St"}, {"ADDR": "2 B St"}],
            fieldnames=["ADDR"],
        )
        properties = load_properties(path, field_map={"address": "ADDR"})
        self.assertEqual([p["address"] for p in properties], ["1 A St", "2 B St"])

    def test_load_properties_carries_key_field(self):
        path = self._write_csv(
            [{"ADDR": "1 A St", "PARCEL_ID": "P1"}],
            fieldnames=["ADDR", "PARCEL_ID"],
        )
        properties = load_properties(path, field_map={"address": "ADDR"}, key_field="PARCEL_ID")
        self.assertEqual(properties[0]["_parcel_id"], "P1")

    def test_load_properties_strips_padded_key_field(self):
        path = self._write_csv(
            [{"ADDR": "1 A St", "PARCEL_ID": "P1      "}],
            fieldnames=["ADDR", "PARCEL_ID"],
        )
        properties = load_properties(path, field_map={"address": "ADDR"}, key_field="PARCEL_ID")
        self.assertEqual(properties[0]["_parcel_id"], "P1")

    def test_merge_latest_by_key_matches_despite_padded_secondary_key(self):
        base_path = self._write_csv(
            [{"ADDR": "1 A St", "PARCEL_ID": "P1"}],
            fieldnames=["ADDR", "PARCEL_ID"],
        )
        properties = load_properties(base_path, field_map={"address": "ADDR"}, key_field="PARCEL_ID")

        sales_path = self._write_csv(
            [{"PARCEL_ID": "P1      ", "SALE_DATE": "2019-03-15"}],
            fieldnames=["PARCEL_ID", "SALE_DATE"],
        )
        merged = merge_latest_by_key(
            properties, sales_path, "PARCEL_ID", "SALE_DATE", {"last_sale_year": "SALE_DATE"}
        )
        self.assertEqual(merged[0]["last_sale_year"], 2019)

    def test_merge_latest_by_key_requires_field_map(self):
        with self.assertRaises(ValueError):
            merge_latest_by_key([], "anything.csv", "PARCEL_ID", "SALE_DATE", field_map=None)

    def test_merge_latest_by_key_picks_most_recent_sale(self):
        base_path = self._write_csv(
            [{"ADDR": "1 A St", "PARCEL_ID": "P1"}],
            fieldnames=["ADDR", "PARCEL_ID"],
        )
        properties = load_properties(base_path, field_map={"address": "ADDR"}, key_field="PARCEL_ID")

        sales_path = self._write_csv(
            [
                {"PARCEL_ID": "P1", "SALE_DATE": "2007-06-01", "SALE_AMOUNT": "150000"},
                {"PARCEL_ID": "P1", "SALE_DATE": "2019-03-15", "SALE_AMOUNT": "220000"},
            ],
            fieldnames=["PARCEL_ID", "SALE_DATE", "SALE_AMOUNT"],
        )
        merged = merge_latest_by_key(
            properties,
            sales_path,
            join_key_column="PARCEL_ID",
            date_column="SALE_DATE",
            field_map={"last_sale_year": "SALE_DATE"},
        )
        self.assertEqual(merged[0]["last_sale_year"], 2019)

    def test_merge_latest_by_key_leaves_unmatched_properties_unchanged(self):
        base_path = self._write_csv(
            [{"ADDR": "1 A St", "PARCEL_ID": "P1"}],
            fieldnames=["ADDR", "PARCEL_ID"],
        )
        properties = load_properties(base_path, field_map={"address": "ADDR"}, key_field="PARCEL_ID")

        sales_path = self._write_csv(
            [{"PARCEL_ID": "P2", "SALE_DATE": "2019-03-15"}],
            fieldnames=["PARCEL_ID", "SALE_DATE"],
        )
        merged = merge_latest_by_key(
            properties, sales_path, "PARCEL_ID", "SALE_DATE", {"last_sale_year": "SALE_DATE"}
        )
        self.assertNotIn("last_sale_year", merged[0])


if __name__ == "__main__":
    unittest.main()
