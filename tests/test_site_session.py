"""Tests for the website's first-party session on /api/v2.

The website's own pages call four v2 endpoints from the browser. They carry
no API key; instead a page render sets a signed session cookie that v2 auth
accepts on exactly those four routes.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ApiTestBase
from modules import auth as v1_auth
from modules.config import resolve_secret_key


class TestResolveSecretKey(unittest.TestCase):
    def test_configured_key_is_used_as_is(self):
        self.assertEqual(resolve_secret_key('prod', 'configured-secret'),
                         'configured-secret')

    def test_missing_key_outside_dev_fails_loudly(self):
        with self.assertRaises(RuntimeError) as ctx:
            resolve_secret_key('prod', None)
        self.assertIn('SECRET_KEY', str(ctx.exception))

    def test_missing_key_in_dev_gets_an_ephemeral_one(self):
        key = resolve_secret_key('dev', None)
        self.assertIsInstance(key, str)
        self.assertGreaterEqual(len(key), 32)
        self.assertNotEqual(key, resolve_secret_key('dev', None))


class TestSiteSession(ApiTestBase):
    SITE_ROUTES = (
        '/api/v2/items/Divzer',
        '/api/v2/aspects/Archer/Test',
        '/api/v2/market/items/Divzer/history',
        '/api/v2/market/rankings',
    )

    def start_site_session(self):
        with self.client.session_transaction() as sess:
            sess['site'] = True

    def test_page_render_sets_the_site_session(self):
        resp = self.client.get('/emerald_calculator')
        self.assertEqual(resp.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get('site'))

    def test_session_cookie_is_http_only_and_same_site(self):
        resp = self.client.get('/emerald_calculator')
        cookie = resp.headers.get('Set-Cookie', '')
        self.assertIn('session=', cookie)
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)

    def test_site_session_is_accepted_on_the_routes_the_website_calls(self):
        self.start_site_session()
        with patch('modules.routes.api.v2.market.get_history', return_value=[]), \
                patch('modules.routes.api.v2.market.get_ranking', return_value=[]):
            for path in self.SITE_ROUTES:
                with self.subTest(path=path):
                    resp = self.client.get(path)
                    self.assertEqual(resp.status_code, 200,
                                     resp.get_data(as_text=True))
                    self.assertIn('data', resp.get_json())

    def test_site_session_is_denied_everywhere_else(self):
        self.start_site_session()
        for path in ('/api/v2/status', '/api/v2/market/listings',
                     '/api/v2/market/items/Divzer/price', '/api/v2/lootpools'):
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.get_json()['error']['code'], 'forbidden')

    def test_no_session_and_no_key_is_still_401(self):
        resp = self.client.get('/api/v2/items/Divzer')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['error']['code'], 'missing_api_key')

    def test_api_key_header_takes_precedence_over_the_session(self):
        self.start_site_session()
        resp = self.request('GET', '/api/v2/items/Divzer', token='no-such-key')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['error']['code'], 'invalid_api_key')

    def test_site_usage_is_recorded_under_the_website_owner(self):
        self.start_site_session()
        v1_auth.enqueue.reset_mock()
        self.client.get('/api/v2/items/Divzer')
        v1_auth.enqueue.assert_called_once()
        recorded = v1_auth.enqueue.call_args.args[0].items[0]
        self.assertEqual(recorded['owner'], 'website')
        self.assertEqual(recorded['key_hash'], 'website')


if __name__ == '__main__':
    unittest.main()
