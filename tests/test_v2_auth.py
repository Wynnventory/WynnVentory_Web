"""Tests for /api/v2 authentication semantics."""
import os
import sys
import unittest

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

    def test_mod_key_is_denied_on_v2(self):
        resp = self.request('GET', '/api/v2/status', token=MOD_TOKEN)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()['error']['code'], 'forbidden')

    def test_mod_key_still_works_on_v1(self):
        resp = self.request('GET', '/api/lootpool/current', token=MOD_TOKEN)
        self.assertNotIn(resp.status_code, (401, 403))


if __name__ == '__main__':
    unittest.main()
