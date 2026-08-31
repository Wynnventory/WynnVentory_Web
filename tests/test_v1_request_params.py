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
