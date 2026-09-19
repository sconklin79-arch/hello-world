import json
import unittest
from unittest.mock import patch

from data_sources import chicago_open_data, zenlist


def _fake_response(payload):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    return FakeResponse()


class ZenlistTest(unittest.TestCase):
    def test_fetch_listings_requires_api_key(self):
        with self.assertRaises(ValueError):
            zenlist.fetch_listings(api_key=None)

    @patch("data_sources.zenlist.urllib.request.urlopen")
    def test_fetch_listings_returns_listings_list(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"listings": [{"price": 250000}]})
        listings = zenlist.fetch_listings(api_key="key123")
        self.assertEqual(listings, [{"price": 250000}])

    @patch("data_sources.zenlist.urllib.request.urlopen")
    def test_fetch_listings_falls_back_to_data_key(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"data": [{"price": 100000}]})
        listings = zenlist.fetch_listings(api_key="key123")
        self.assertEqual(listings, [{"price": 100000}])

    @patch("data_sources.zenlist.urllib.request.urlopen")
    def test_fetch_listings_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = zenlist.urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None
        )
        with self.assertRaises(ValueError):
            zenlist.fetch_listings(api_key="bad-key")

    @patch("data_sources.zenlist.urllib.request.urlopen")
    def test_fetch_listings_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = zenlist.urllib.error.URLError("blocked by proxy")
        with self.assertRaises(ValueError):
            zenlist.fetch_listings(api_key="key123")

    def test_normalize_listing_maps_fields(self):
        raw = {
            "address": "1 Main St",
            "price": 250000,
            "days_on_market": 45,
            "status": "expired",
            "last_sold_date": "2005-06-01",
            "square_feet": 1400,
            "id": "abc",
        }
        normalized = zenlist.normalize_listing(raw)
        self.assertEqual(normalized["address"], "1 Main St")
        self.assertEqual(normalized["asking_price"], 250000)
        self.assertEqual(normalized["days_on_market"], 45)
        self.assertTrue(normalized["was_expired_or_withdrawn"])
        self.assertEqual(normalized["last_sale_year"], 2005)
        self.assertEqual(normalized["sqft"], 1400)

    def test_normalize_listing_handles_alternate_field_names(self):
        raw = {"full_address": "2 Oak Ave", "list_price": 180000, "sqft": 1200}
        normalized = zenlist.normalize_listing(raw)
        self.assertEqual(normalized["address"], "2 Oak Ave")
        self.assertEqual(normalized["asking_price"], 180000)
        self.assertEqual(normalized["sqft"], 1200)


class ChicagoOpenDataTest(unittest.TestCase):
    def test_fetch_permits_requires_address(self):
        with self.assertRaises(ValueError):
            chicago_open_data.fetch_permits("")

    def test_fetch_violations_requires_address(self):
        with self.assertRaises(ValueError):
            chicago_open_data.fetch_violations("")

    @patch("data_sources.chicago_open_data.urllib.request.urlopen")
    def test_fetch_permits_returns_records(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response([{"permit_": "100"}])
        records = chicago_open_data.fetch_permits("Main St")
        self.assertEqual(records, [{"permit_": "100"}])

    @patch("data_sources.chicago_open_data.urllib.request.urlopen")
    def test_fetch_permits_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = chicago_open_data.urllib.error.URLError("blocked by proxy")
        with self.assertRaises(ValueError):
            chicago_open_data.fetch_permits("Main St")

    def test_enrich_property_flags_open_violations(self):
        base = {"asking_price": 100000}
        violations = [
            {"violation_status": "OPEN"},
            {"violation_status": "CLOSED"},
        ]
        enriched = chicago_open_data.enrich_property(base, permits=[{}, {}], violations=violations)
        self.assertTrue(enriched["has_code_violations"])
        self.assertEqual(enriched["_open_code_violation_count"], 1)
        self.assertEqual(enriched["_permit_count"], 2)
        self.assertEqual(base, {"asking_price": 100000})

    def test_enrich_property_no_violations(self):
        enriched = chicago_open_data.enrich_property({}, permits=[], violations=[])
        self.assertFalse(enriched["has_code_violations"])


if __name__ == "__main__":
    unittest.main()
