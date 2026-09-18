"""Regression tests for v1 request-parameter handling fixes.

Covers the fixes for:
- ?sort= on /api/trademarket/listings (was: always 500)
- non-integer ?tier= (was: uncaught ValueError -> 500)
- ?page_size=0 (was: unlimited Mongo query on listings, $limit: 0 error on pools)
"""
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ALL_SCOPES, ApiTestBase, shared_collection_mock

from modules.models.sort_options import SortOption


class TestListingsParams(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)
        # Make the listings query return a real, empty result set.
        coll = shared_collection_mock()
        coll.count_documents.return_value = 0
        cursor = MagicMock()
        cursor.sort.return_value.skip.return_value.limit.return_value = iter([])
        coll.find.return_value = cursor

    def _get(self, query):
        return self.request('GET', f'/api/trademarket/listings?{query}',
                            token='reader')

    def test_every_sort_option_is_accepted(self):
        for option in SortOption:
            with self.subTest(sort=option.value):
                resp = self._get(f'sort={option.value}')
                self.assertEqual(resp.status_code, 200)

    def test_invalid_sort_returns_400(self):
        resp = self._get('sort=price_banana')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Invalid sort option', resp.get_json()['error'])

    def test_missing_sort_defaults_to_timestamp_desc(self):
        resp = self._get('')
        self.assertEqual(resp.status_code, 200)

    def test_non_integer_tier_returns_400(self):
        resp = self._get('tier=abc')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('tier', resp.get_json()['error'].lower())

    def test_page_size_zero_is_clamped_to_one(self):
        resp = self._get('page_size=0')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['page_size'], 1)

    def test_page_size_is_capped(self):
        resp = self._get('page_size=99999')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['page_size'], 1000)


class TestRarityTierFilterCombination(ApiTestBase):
    def test_rarity_normal_with_tier_keeps_both_filters(self):
        # Regression: the tier fallback used to overwrite the rarity=normal
        # $or clause, silently dropping the rarity filter.
        coll = shared_collection_mock()
        coll.count_documents.return_value = 0
        cursor = MagicMock()
        cursor.sort.return_value.skip.return_value.limit.return_value = iter([])
        coll.find.return_value = cursor

        self.add_key('reader', scopes=ALL_SCOPES)
        resp = self.request(
            'GET',
            '/api/trademarket/listings/Oak?rarity=normal&tier=3',
            token='reader')
        self.assertEqual(resp.status_code, 200)

        query_filter = coll.find.call_args.kwargs['filter']
        self.assertIn('$and', query_filter)
        rarity_clause, tier_clause = query_filter['$and']
        self.assertIn({'rarity': {'$eq': None}}, rarity_clause['$or'])
        self.assertIn({'item_type': {'$in': ['MaterialItem', 'PowderItem',
                                             'AmplifierItem',
                                             'EmeraldPouchItem']},
                       'tier': 3}, tier_clause['$or'])


class TestTierOnOtherMarketRoutes(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)

    def test_price_route_rejects_bad_tier(self):
        resp = self.request('GET', '/api/trademarket/item/Foo/price?tier=abc',
                            token='reader')
        self.assertEqual(resp.status_code, 400)

    def test_public_history_route_rejects_bad_tier(self):
        resp = self.request('GET', '/api/trademarket/history/Foo?tier=abc')
        self.assertEqual(resp.status_code, 400)

    def test_history_price_route_rejects_bad_tier(self):
        resp = self.request('GET', '/api/trademarket/history/Foo/price?tier=abc',
                            token='reader')
        self.assertEqual(resp.status_code, 400)


class TestArchiveNameMatching(ApiTestBase):
    """The ~3M-row archive is queried by exact (indexed) name; a case
    mismatch is resolved through the small averages collection instead of a
    case-insensitive regex, which cannot use the archive's name index and
    scanned it on every history/latest call (2.5-4.5 s in prod)."""

    def setUp(self):
        super().setUp()
        from modules.repositories.market_repo import get_historic_average, get_price_history
        self.get_historic_average = get_historic_average
        self.get_price_history = get_price_history
        # The collection mock is shared process-wide; isolate call history
        # and the side effects these tests set.
        self.coll = shared_collection_mock()
        self.coll.reset_mock(return_value=True, side_effect=True)
        self.addCleanup(self.coll.reset_mock, return_value=True, side_effect=True)
        self.stats = {'name': 'Divzer', 'average_price': 100.0}

    # --- history/latest (aggregate) --------------------------------------
    def test_latest_history_matches_name_exactly_on_the_archive(self):
        self.coll.aggregate.return_value = iter([self.stats])
        result = self.get_historic_average(item_name='Divzer')
        self.assertEqual(result, self.stats)
        self.coll.aggregate.assert_called_once()
        self.assertEqual(self.coll.aggregate.call_args.args[0][0]['$match']['name'], 'Divzer')
        self.coll.find_one.assert_not_called()

    def test_latest_history_resolves_a_case_mismatch_via_stored_spelling(self):
        self.coll.aggregate.side_effect = [iter([]), iter([self.stats])]
        self.coll.find_one.return_value = {'name': 'Divzer'}
        result = self.get_historic_average(item_name='divzer')
        self.assertEqual(result, self.stats)
        lookup = self.coll.find_one.call_args.args[0]['name']
        self.assertEqual(lookup, {'$regex': '^divzer$', '$options': 'i'})
        names = [c.args[0][0]['$match']['name'] for c in self.coll.aggregate.call_args_list]
        self.assertEqual(names, ['divzer', 'Divzer'])

    def test_latest_history_for_an_unknown_name_stops_after_one_lookup(self):
        self.coll.aggregate.return_value = iter([])
        self.coll.find_one.return_value = None
        self.assertEqual(self.get_historic_average(item_name='nope'), {})
        self.coll.aggregate.assert_called_once()

    # --- history (find) ----------------------------------------------------
    def test_history_matches_name_exactly_on_the_archive(self):
        self.coll.find.return_value = iter([self.stats])
        result = self.get_price_history(item_name='Divzer')
        self.assertEqual(result, [self.stats])
        self.coll.find.assert_called_once()
        self.assertEqual(self.coll.find.call_args.kwargs['filter']['name'], 'Divzer')
        self.coll.find_one.assert_not_called()

    def test_history_resolves_a_case_mismatch_via_stored_spelling(self):
        self.coll.find.side_effect = [iter([]), iter([self.stats])]
        self.coll.find_one.return_value = {'name': 'Divzer'}
        result = self.get_price_history(item_name='divzer')
        self.assertEqual(result, [self.stats])
        names = [c.kwargs['filter']['name'] for c in self.coll.find.call_args_list]
        self.assertEqual(names, ['divzer', 'Divzer'])


class TestPoolPageSize(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)
        coll = shared_collection_mock()
        coll.aggregate.return_value = iter([])

    def test_page_size_zero_is_clamped_to_one(self):
        for pool in ('lootpool', 'raidpool'):
            with self.subTest(pool=pool):
                resp = self.request('GET', f'/api/{pool}/all?page_size=0',
                                    token='reader')
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.get_json()['page_size'], 1)

    def test_page_size_is_capped_at_five(self):
        resp = self.request('GET', '/api/lootpool/all?page_size=50',
                            token='reader')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['page_size'], 5)


if __name__ == '__main__':
    unittest.main()
