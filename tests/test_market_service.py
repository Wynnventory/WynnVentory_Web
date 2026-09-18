import unittest

from modules.repositories.market_repo import TIERED_TYPES
from modules.routes.web.web import SUBTYPE_OPTIONS
from modules.services.market_service import _format_item_for_db
from tests.test_base import BaseTestCase


class TestMarketServiceItemTypes(BaseTestCase):
    """Item types the mod submits as plain trade market listings: wards, charms and gathering tools."""

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

    def test_format_item_keeps_charm_roll_fields(self):
        listing = {
            "item": {
                "name": "Charm of the Corruption",
                "rarity": "Fabled",
                "itemType": "CharmItem",
                "type": "CHARM",
                "icon": {"format": "attribute", "value": "charm.corruption"},
                "amount": 1,
                "unidentified": False,
                "rerollCount": 2,
                "overallRollPercentage": 87.5,
                "actualStatsWithPercentage": [{"statActualValue": {"statType": {"key": "xpBonus"}, "value": 12}}],
            },
            "amount": 1,
            "listingPrice": 500000,
            "playerName": "Tester",
            "modVersion": "2.2.4",
            "hash_code": 43,
        }

        formatted = _format_item_for_db(listing)

        self.assertEqual("CharmItem", formatted["item_type"])
        self.assertEqual("CHARM", formatted["type"])
        self.assertIsNone(formatted["tier"])
        self.assertFalse(formatted["unidentified"])
        self.assertEqual(2, formatted["reroll_count"])
        self.assertEqual(87.5, formatted["overall_roll"])
        self.assertEqual(1, len(formatted["stat_rolls"]))

    def test_format_item_keeps_gathering_tool_name_with_tier_suffix(self):
        listing = {
            "item": {
                "name": "Bronze Axe T4",
                "rarity": "Unique",
                "itemType": "GatheringToolItem",
                "type": "AXE",
                "icon": {"format": "attribute", "value": "tool.bronzeAxe"},
                "amount": 1,
            },
            "amount": 1,
            "listingPrice": 2048,
            "playerName": "Tester",
            "modVersion": "2.2.4",
            "hash_code": 44,
        }

        formatted = _format_item_for_db(listing)

        self.assertEqual("GatheringToolItem", formatted["item_type"])
        self.assertEqual("Bronze Axe T4", formatted["name"])
        self.assertEqual("AXE", formatted["type"])
        self.assertIsNone(formatted["tier"])

    def test_charms_and_gathering_tools_are_not_tiered_types(self):
        # Charms have no tier and a gathering tool's tier is part of its unique name.
        self.assertNotIn("CharmItem", TIERED_TYPES)
        self.assertNotIn("GatheringToolItem", TIERED_TYPES)

    def test_gathering_tool_subtypes_cover_all_tool_kinds(self):
        self.assertIn("GatheringToolItem", SUBTYPE_OPTIONS)
        values = [value for value, _label in SUBTYPE_OPTIONS["GatheringToolItem"]]
        self.assertEqual(["AXE", "PICKAXE", "FISHING_ROD", "SCYTHE"], values)

    def test_ward_subtypes_cover_all_seven_colours(self):
        self.assertIn("WardItem", SUBTYPE_OPTIONS)
        values = [value for value, _label in SUBTYPE_OPTIONS["WardItem"]]
        self.assertEqual(
            ["BlueWard", "GreenWard", "OrangeWard", "PinkWard", "PurpleWard", "RedWard", "YellowWard"],
            values,
        )


if __name__ == "__main__":
    unittest.main()
