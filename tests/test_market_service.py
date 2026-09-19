import unittest
from datetime import datetime
from unittest.mock import patch

from modules.repositories.market_repo import TIERED_TYPES
from modules.routes.web.web import SUBTYPE_OPTIONS
from modules.services import market_service
from modules.services.market_service import _format_item_for_db, get_ranking
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


class TestRankingCache(BaseTestCase):
    """get_ranking recomputes the whole archive ranking; v2 pages through it
    200 rows at a time, so the result is cached briefly per date range."""

    def setUp(self):
        super().setUp()
        market_service.clear_ranking_cache()
        self.repo = self.create_patch('modules.services.market_service.get_all_items_ranking')
        self.repo.return_value = [{'rank': 1, 'name': 'Slayer'}]
        self.start = datetime(2026, 9, 10)
        self.end = datetime(2026, 9, 17)

    def test_same_date_range_is_computed_once(self):
        first = get_ranking(start_date=self.start, end_date=self.end)
        second = get_ranking(start_date=self.start, end_date=self.end)
        self.assertEqual(first, second)
        self.repo.assert_called_once_with(start_date=self.start, end_date=self.end)

    def test_different_date_range_is_computed_again(self):
        get_ranking(start_date=self.start, end_date=self.end)
        get_ranking(start_date=self.start, end_date=datetime(2026, 9, 18))
        self.assertEqual(self.repo.call_count, 2)

    def test_sub_day_timestamps_share_the_day_range_entry(self):
        # v1 accepts arbitrary ISO timestamps; the repository normalises them
        # to day boundaries, so they must not mint distinct cache entries.
        get_ranking(start_date=datetime(2026, 9, 10, 8, 15), end_date=datetime(2026, 9, 17, 23, 59, 59))
        get_ranking(start_date=datetime(2026, 9, 10, 0, 0, 1), end_date=datetime(2026, 9, 17, 12, 0))
        self.repo.assert_called_once()
        self.assertEqual(len(market_service._ranking_cache), 1)

    def test_cache_size_is_bounded(self):
        limit = market_service.RANKING_CACHE_MAX_ENTRIES
        for day in range(1, limit + 6):
            get_ranking(start_date=datetime(2026, 1, day), end_date=datetime(2026, 2, day))
        self.assertEqual(len(market_service._ranking_cache), limit)
        # the most recent range is still served from the cache
        self.repo.reset_mock()
        get_ranking(start_date=datetime(2026, 1, limit + 5), end_date=datetime(2026, 2, limit + 5))
        self.repo.assert_not_called()

    def test_expired_entries_are_evicted_on_store(self):
        with patch('modules.services.market_service.time.monotonic') as clock:
            clock.return_value = 1000.0
            get_ranking(start_date=self.start, end_date=self.end)
            clock.return_value = 1000.0 + market_service.RANKING_CACHE_TTL_SECONDS + 1
            get_ranking(start_date=self.start, end_date=datetime(2026, 9, 18))
        self.assertEqual(len(market_service._ranking_cache), 1)

    def test_cached_ranking_expires(self):
        with patch('modules.services.market_service.time.monotonic') as clock:
            clock.return_value = 1000.0
            get_ranking(start_date=self.start, end_date=self.end)
            clock.return_value = 1000.0 + market_service.RANKING_CACHE_TTL_SECONDS - 1
            get_ranking(start_date=self.start, end_date=self.end)
            self.assertEqual(self.repo.call_count, 1)
            clock.return_value = 1000.0 + market_service.RANKING_CACHE_TTL_SECONDS + 1
            get_ranking(start_date=self.start, end_date=self.end)
            self.assertEqual(self.repo.call_count, 2)


if __name__ == "__main__":
    unittest.main()
