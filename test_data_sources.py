import json
import unittest
from unittest.mock import patch

from data_sources import chicago_open_data, mred


def _fake_response(payload):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode()

    return FakeResponse()


class MredTest(unittest.TestCase):
    def test_get_access_token_requires_credentials(self):
        with self.assertRaises(ValueError):
            mred.get_access_token(client_id=None, client_secret=None, token_url=None)

    @patch("data_sources.mred.urllib.request.urlopen")
    def test_get_access_token_returns_token(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"access_token": "abc123"})
        token = mred.get_access_token(
            client_id="id", client_secret="secret", token_url="https://example.test/token"
        )
        self.assertEqual(token, "abc123")

    @patch("data_sources.mred.urllib.request.urlopen")
    def test_get_access_token_bad_response(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"error": "invalid_client"})
        with self.assertRaises(ValueError):
            mred.get_access_token(
                client_id="id", client_secret="secret", token_url="https://example.test/token"
            )

    def test_fetch_listings_requires_token(self):
        with self.assertRaises(ValueError):
            mred.fetch_listings(access_token=None, base_url="https://example.test")

    @patch("data_sources.mred.urllib.request.urlopen")
    def test_fetch_listings_returns_value_list(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"value": [{"ListPrice": 100000}]})
        listings = mred.fetch_listings(access_token="tok", base_url="https://example.test")
        self.assertEqual(listings, [{"ListPrice": 100000}])

    def test_normalize_listing_maps_fields(self):
        raw = {
            "UnparsedAddress": "1 Main St",
            "ListPrice": 250000,
            "DaysOnMarket": 45,
            "StandardStatus": "Expired",
            "PurchaseContractDate": "2005-06-01",
            "LivingArea": 1400,
            "ListingKey": "XYZ",
        }
        normalized = mred.normalize_listing(raw)
        self.assertEqual(normalized["address"], "1 Main St")
        self.assertEqual(normalized["asking_price"], 250000)
        self.assertEqual(normalized["days_on_market"], 45)
        self.assertTrue(normalized["was_expired_or_withdrawn"])
        self.assertEqual(normalized["last_sale_year"], 2005)
        self.assertEqual(normalized["sqft"], 1400)


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
