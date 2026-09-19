import json
import unittest
from unittest.mock import patch

from data_sources import county_open_data


def _fake_response(payload):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    return FakeResponse()


class CountyOpenDataTest(unittest.TestCase):
    def test_fetch_records_requires_domain(self):
        with self.assertRaises(ValueError):
            county_open_data.fetch_records(domain="", dataset_id="abcd-1234")

    def test_fetch_records_requires_dataset_id(self):
        with self.assertRaises(ValueError):
            county_open_data.fetch_records(domain="example.gov", dataset_id="")

    @patch("data_sources.county_open_data.urllib.request.urlopen")
    def test_fetch_records_returns_records(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response([{"sale_price": "250000"}])
        records = county_open_data.fetch_records(domain="example.gov", dataset_id="abcd-1234")
        self.assertEqual(records, [{"sale_price": "250000"}])

    @patch("data_sources.county_open_data.urllib.request.urlopen")
    def test_fetch_records_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = county_open_data.urllib.error.HTTPError(
            "url", 404, "Not Found", {}, None
        )
        with self.assertRaises(ValueError):
            county_open_data.fetch_records(domain="example.gov", dataset_id="abcd-1234")

    @patch("data_sources.county_open_data.urllib.request.urlopen")
    def test_fetch_records_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = county_open_data.urllib.error.URLError(
            "Tunnel connection failed: 403 Forbidden"
        )
        with self.assertRaises(ValueError):
            county_open_data.fetch_records(domain="example.gov", dataset_id="abcd-1234")

    def test_summarize_neighborhood_sales(self):
        records = [
            {"sale_price": "200000"},
            {"sale_price": "220000"},
            {"sale_price": "260000"},
        ]
        summary = county_open_data.summarize_neighborhood_sales(records, "sale_price")
        self.assertEqual(summary["comparable_sale_count"], 3)
        self.assertEqual(summary["comparable_median_price"], 220000)
        self.assertAlmostEqual(summary["comparable_value_spread_pct"], 60000 / 220000)

    def test_summarize_neighborhood_sales_ignores_missing_prices(self):
        records = [{"sale_price": "200000"}, {"sale_price": ""}, {"sale_price": None}]
        summary = county_open_data.summarize_neighborhood_sales(records, "sale_price")
        self.assertEqual(summary["comparable_sale_count"], 1)

    def test_summarize_neighborhood_sales_no_records(self):
        summary = county_open_data.summarize_neighborhood_sales([], "sale_price")
        self.assertEqual(summary["comparable_sale_count"], 0)
        self.assertIsNone(summary["comparable_value_spread_pct"])


if __name__ == "__main__":
    unittest.main()
