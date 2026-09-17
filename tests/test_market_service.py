import unittest

from modules.repositories.market_repo import TIERED_TYPES
from modules.routes.web.web import SUBTYPE_OPTIONS
from modules.services.market_service import _format_item_for_db
from tests.test_base import BaseTestCase


class TestMarketServiceWardItems(BaseTestCase):
    """Ward items are non-tiered trade market items submitted by the mod as itemType 'WardItem'."""

    def _ward_listing(self):
        return {
            "item": {
                "name": "Blue Ward",
                "rarity": "Common",
                "itemType": "WardItem",
                "type": "BlueWard",
                "icon": {"format": "attribute", "value": "ward.blue"},
                "amount": 1,
            },
            "amount": 1,
            "listingPrice": 12345,
            "playerName": "Tester",
            "modVersion": "2.2.4",
            "hash_code": 42,
        }

    def test_format_item_keeps_ward_item_type_and_null_tier(self):
        formatted = _format_item_for_db(self._ward_listing())

        self.assertEqual("WardItem", formatted["item_type"])
        self.assertEqual("BlueWard", formatted["type"])
        self.assertEqual("Blue Ward", formatted["name"])
        self.assertIsNone(formatted["tier"])
        self.assertEqual({"format": "attribute", "value": "ward.blue"}, formatted["icon"])
        self.assertEqual(12345, formatted["listing_price"])

    def test_ward_item_is_not_a_tiered_type(self):
        # Wards carry no tier; listing them as tiered would break per-tier price aggregation.
        self.assertNotIn("WardItem", TIERED_TYPES)

    def test_ward_subtypes_cover_all_seven_colours(self):
        self.assertIn("WardItem", SUBTYPE_OPTIONS)
        values = [value for value, _label in SUBTYPE_OPTIONS["WardItem"]]
        self.assertEqual(
            ["BlueWard", "GreenWard", "OrangeWard", "PinkWard", "PurpleWard", "RedWard", "YellowWard"],
            values,
        )


if __name__ == "__main__":
    unittest.main()
