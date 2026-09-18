"""Tests for /api/v2 authentication semantics."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ALL_SCOPES, MOD_TOKEN, ApiTestBase


class TestV2Auth(ApiTestBase):
    def test_missing_key_returns_401(self):
        resp = self.request('GET', '/api/v2/status')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['error']['code'], 'missing_api_key')
        self.assertEqual(resp.headers.get('WWW-Authenticate'), 'Api-Key')

    def test_invalid_key_returns_401_not_403(self):
        resp = self.request('GET', '/api/v2/status', token='no-such-key')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['error']['code'], 'invalid_api_key')
        self.assertEqual(resp.headers.get('WWW-Authenticate'), 'Api-Key')

    def test_valid_key_is_accepted(self):
        self.add_key('reader', scopes=[])
        resp = self.request('GET', '/api/v2/status', token='reader')
        self.assertEqual(resp.status_code, 200)

    def test_x_api_key_header_is_accepted(self):
        self.add_key('reader', scopes=[])
        resp = self.client.get('/api/v2/status',
                               headers={'X-API-Key': 'reader'})
        self.assertEqual(resp.status_code, 200)

    def test_mod_key_is_denied_on_v2_routes_the_mod_does_not_use(self):
        for path in ('/api/v2/status', '/api/v2/market/listings',
                     '/api/v2/lootpools'):
            with self.subTest(path=path):
                resp = self.request('GET', path, token=MOD_TOKEN)
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.get_json()['error']['code'], 'forbidden')

    def test_mod_key_is_accepted_on_the_routes_the_mod_reads(self):
        price = {'name': 'Divzer', 'tier': None, 'shiny': False,
                 'item_type': 'GearItem', 'lowest_price': 12000}
        pool = {'year': 2026, 'week': 38, 'regions': []}
        with patch('modules.routes.api.v2.market.get_price',
                   return_value=price), \
                patch('modules.routes.api.v2.market.get_historic_item_price',
                      return_value=price), \
                patch('modules.services.base_pool_service.get_specific_pool',
                      return_value=pool):
            for path in ('/api/v2/market/items/Divzer/price',
                         '/api/v2/market/items/Divzer/history/latest',
                         '/api/v2/lootpools/current',
                         '/api/v2/raidpools/current'):
                with self.subTest(path=path):
                    resp = self.request('GET', path, token=MOD_TOKEN)
                    self.assertEqual(resp.status_code, 200,
                                     resp.get_data(as_text=True))
                    self.assertIn('data', resp.get_json())

    def test_mod_key_still_works_on_v1(self):
        resp = self.request('GET', '/api/lootpool/current', token=MOD_TOKEN)
        self.assertNotIn(resp.status_code, (401, 403))


if __name__ == '__main__':
    unittest.main()
