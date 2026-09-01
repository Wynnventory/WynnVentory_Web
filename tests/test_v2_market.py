"""Tests for the /api/v2/market endpoints."""
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ALL_SCOPES, ApiTestBase

RAW_LISTING = {
    '_id': 'should-never-leak',
    'name': 'Divzer',
    'rarity': 'Legendary',
    'item_type': 'GearItem',
    'type': 'Bow',
    'tier': None,
    'unidentified': False,
    'shiny_stat': None,
    'overall_roll': 87.4,
    'stat_rolls': {'dexterity': 95.2},
    'reroll_count': 0,
    'amount': 1,
    'listing_price': 15000,
    'icon': 'bow_icon',
    'mod_version': '1.2.0',
    'hash_code': 'abc123',
    'timestamp': datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc),
}


class MarketTestBase(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)

    def patch_service(self, name, **kwargs):
        p = patch(f'modules.routes.api.v2.market.{name}', **kwargs)
        mock = p.start()
        self.addCleanup(p.stop)
        return mock


class TestListings(MarketTestBase):
    def test_listing_serialization(self):
        self.patch_service('get_item_listings', return_value={
            'page': 1, 'page_size': 50, 'count': 1, 'total': 1,
            'items': [dict(RAW_LISTING)],
        })
        resp = self.request('GET', '/api/v2/market/listings', token='reader')
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body['pagination'],
                         {'page': 1, 'page_size': 50,
                          'total_items': 1, 'total_pages': 1})
        item = body['data'][0]
        self.assertEqual(item['item_type'], 'gear')
        self.assertEqual(item['subtype'], 'bow')
        self.assertEqual(item['rarity'], 'legendary')
        self.assertFalse(item['shiny'])
        self.assertIsNone(item['shiny_stat'])
        self.assertEqual(item['timestamp'], '2026-08-30T12:00:00Z')
        for internal in ('_id', 'hash_code', 'mod_version', 'type'):
            self.assertNotIn(internal, item)

    def test_shiny_listing_sets_boolean(self):
        shiny_doc = dict(RAW_LISTING, shiny_stat={'statType': 'raidsCompleted'})
        self.patch_service('get_item_listings', return_value={
            'page': 1, 'page_size': 50, 'count': 1, 'total': 1,
            'items': [shiny_doc],
        })
        resp = self.request('GET', '/api/v2/market/listings', token='reader')
        item = resp.get_json()['data'][0]
        self.assertTrue(item['shiny'])
        self.assertEqual(item['shiny_stat'], {'statType': 'raidsCompleted'})

    def test_filters_are_translated_to_storage_vocabulary(self):
        mock = self.patch_service('get_item_listings', return_value={
            'page': 1, 'page_size': 50, 'count': 0, 'total': 0, 'items': [],
        })
        resp = self.request(
            'GET',
            '/api/v2/market/listings?item_type=material&subtype=bow'
            '&sort=listing_price_asc',
            token='reader')
        self.assertEqual(resp.status_code, 200)
        kwargs = mock.call_args.kwargs
        self.assertEqual(kwargs['item_type'], 'MaterialItem')
        # Subtypes pass through unchanged; the repository matches them
        # case-insensitively because stored casing is not uniform.
        self.assertEqual(kwargs['sub_type'], 'bow')
        self.assertEqual(kwargs['sort_option'].value, 'listing_price_asc')

    def test_compound_subtype_filter_is_not_recased(self):
        """Values v2 emits must survive the round trip back into a filter."""
        mock = self.patch_service('get_item_listings', return_value={
            'page': 1, 'page_size': 50, 'count': 0, 'total': 0, 'items': [],
        })
        for emitted in ('waterpowder', 'uthrune', 'chestplate'):
            with self.subTest(subtype=emitted):
                self.request(
                    'GET', f'/api/v2/market/listings?subtype={emitted}',
                    token='reader')
                self.assertEqual(mock.call_args.kwargs['sub_type'], emitted)

    def test_gear_filter_translates_to_storage(self):
        mock = self.patch_service('get_item_listings', return_value={
            'page': 1, 'page_size': 50, 'count': 0, 'total': 0, 'items': [],
        })
        self.request('GET', '/api/v2/market/listings?item_type=gear',
                     token='reader')
        self.assertEqual(mock.call_args.kwargs['item_type'], 'GearItem')

    def test_unknown_query_param_is_a_400(self):
        resp = self.request('GET', '/api/v2/market/listings?itemType=Weapon',
                            token='reader')
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body['error']['code'], 'validation_error')
        self.assertEqual(body['error']['details'][0]['field'], 'itemType')
        self.assertEqual(body['error']['details'][0]['location'], 'query')

    def test_invalid_sort_is_a_400(self):
        resp = self.request('GET', '/api/v2/market/listings?sort=banana',
                            token='reader')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['error']['code'], 'validation_error')

    def test_invalid_item_type_is_a_400(self):
        resp = self.request('GET', '/api/v2/market/listings?item_type=Weapon',
                            token='reader')
        self.assertEqual(resp.status_code, 400)

    def test_listing_item_type_values_round_trip_as_filters(self):
        # Every label the serializer can emit for market storage values must
        # be accepted back by the listings filter.
        from modules.routes.api.v2.serializers.common import (
            ITEM_TYPE_TO_STORAGE, item_type_from_storage)

        for storage_value in ('GearItem', 'MaterialItem', 'IngredientItem',
                              'PowderItem', 'RuneItem', 'DungeonKeyItem',
                              'AmplifierItem', 'EmeraldPouchItem'):
            label = item_type_from_storage(storage_value)
            self.assertEqual(ITEM_TYPE_TO_STORAGE[label], storage_value)

    def test_page_size_zero_is_a_400(self):
        resp = self.request('GET', '/api/v2/market/listings?page_size=0',
                            token='reader')
        self.assertEqual(resp.status_code, 400)

    def test_invalid_boolean_is_a_400(self):
        resp = self.request('GET', '/api/v2/market/listings?shiny=yes',
                            token='reader')
        self.assertEqual(resp.status_code, 400)

    def test_requires_read_market_scope(self):
        self.add_key('scopeless', scopes=[])
        resp = self.request('GET', '/api/v2/market/listings', token='scopeless')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()['error']['code'], 'missing_scope')


class TestItemPrice(MarketTestBase):
    def test_unknown_item_is_a_404(self):
        self.patch_service('get_price', return_value={})
        resp = self.request('GET', '/api/v2/market/items/Nope/price',
                            token='reader')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['error']['code'], 'not_found')

    def test_price_is_enveloped_and_normalized(self):
        self.patch_service('get_price', return_value={
            'name': 'Divzer', 'tier': None, 'item_type': 'Weapon',
            'average_price': 14200.0, 'shiny': False,
            'timestamp': datetime(2026, 8, 30, tzinfo=timezone.utc),
        })
        resp = self.request('GET', '/api/v2/market/items/Divzer/price',
                            token='reader')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['item_type'], 'weapon')
        self.assertEqual(data['timestamp'], '2026-08-30T00:00:00Z')
        self.assertEqual(data['average_price'], 14200.0)


class TestHistory(MarketTestBase):
    def test_history_is_paginated(self):
        points = [{'name': 'Divzer', 'average_price': float(i)}
                  for i in range(5)]
        self.patch_service('get_history', return_value=points)
        resp = self.request(
            'GET', '/api/v2/market/items/Divzer/history?page=2&page_size=2',
            token='reader')
        body = resp.get_json()
        self.assertEqual(body['pagination'],
                         {'page': 2, 'page_size': 2,
                          'total_items': 5, 'total_pages': 3})
        self.assertEqual([p['average_price'] for p in body['data']], [2.0, 3.0])

    def test_empty_range_is_a_200(self):
        self.patch_service('get_history', return_value=[])
        resp = self.request('GET', '/api/v2/market/items/Divzer/history',
                            token='reader')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data'], [])

    def test_dates_are_parsed_to_utc(self):
        mock = self.patch_service('get_history', return_value=[])
        self.request(
            'GET',
            '/api/v2/market/items/Divzer/history'
            '?start_date=2026-08-01&end_date=2026-08-07',
            token='reader')
        kwargs = mock.call_args.kwargs
        self.assertEqual(kwargs['start_date'],
                         datetime(2026, 8, 1, tzinfo=timezone.utc))
        self.assertEqual(kwargs['end_date'],
                         datetime(2026, 8, 7, tzinfo=timezone.utc))

    def test_invalid_date_is_a_400(self):
        resp = self.request(
            'GET', '/api/v2/market/items/Divzer/history?start_date=08-01-2026',
            token='reader')
        self.assertEqual(resp.status_code, 400)


class TestHistoryLatest(MarketTestBase):
    def test_requires_archive_scope(self):
        self.add_key('market-only', scopes=['read:market'])
        resp = self.request('GET', '/api/v2/market/items/Divzer/history/latest',
                            token='market-only')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()['error']['code'], 'missing_scope')

    def test_no_data_is_a_404(self):
        self.patch_service('get_historic_item_price', return_value={})
        resp = self.request('GET', '/api/v2/market/items/Divzer/history/latest',
                            token='reader')
        self.assertEqual(resp.status_code, 404)


class TestRankings(MarketTestBase):
    def test_rankings_are_normalized_and_paginated(self):
        rows = [{'rank': i, 'name': f'Item{i}', 'itemType': 'Weapon',
                 'average_price': 100.0 - i} for i in range(1, 8)]
        self.patch_service('get_ranking', return_value=rows)
        resp = self.request('GET', '/api/v2/market/rankings?page_size=3',
                            token='reader')
        body = resp.get_json()
        self.assertEqual(body['pagination']['total_items'], 7)
        self.assertEqual(body['pagination']['total_pages'], 3)
        first = body['data'][0]
        self.assertEqual(first['item_type'], 'weapon')
        self.assertNotIn('itemType', first)
        self.assertEqual(first['rank'], 1)


class TestSubtypeFilterIsCaseInsensitive(unittest.TestCase):
    """The stored `type` spelling varies by item family, so the subtype
    filter has to match regardless of the caller's casing."""

    def _query_filter(self, sub_type):
        from modules.repositories import market_repo

        with patch.object(market_repo, 'get_collection') as get_collection:
            market_repo.get_trade_market_item_listings(sub_type=sub_type)
        return get_collection.return_value.count_documents.call_args.args[0]

    def test_lowercased_subtype_matches_stored_casing(self):
        for emitted in ('waterpowder', 'uthrune', 'chestplate'):
            with self.subTest(subtype=emitted):
                self.assertEqual(self._query_filter(emitted)['type'],
                                 {'$regex': f'^{emitted}$', '$options': 'i'})

    def test_regex_metacharacters_are_escaped(self):
        self.assertEqual(self._query_filter('a.b')['type']['$regex'],
                         r'^a\.b$')


if __name__ == '__main__':
    unittest.main()
