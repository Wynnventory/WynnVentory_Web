"""Lock-in tests for the v1 /api auth matrix.

These tests pin the CURRENT auth behavior of every v1 route — which routes are
public, which accept the mod key, and which scopes are enforced — so that the
auth-registry refactor (and any later change) cannot silently alter v1 access.

Notes on intent:
- /api/aspect/... is reachable without a key. Historically this was accidental
  (a view-function name collision with the public item view), but the website's
  JS depends on keyless access, so it is locked in here as intended behavior.
- Assertions on allowed requests check only that auth passed (no 401/403);
  many views then fail deeper in mocked infrastructure, which is irrelevant here.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ALL_SCOPES, MOD_TOKEN, ApiTestBase

# Routes reachable without any API key.
PUBLIC_ROUTES = [
    ('GET', '/api/item/TestItem'),
    ('POST', '/api/items'),
    ('GET', '/api/aspect/archer/TestAspect'),
    ('GET', '/api/trademarket/history/TestItem'),
    ('GET', '/api/trademarket/ranking'),
]

# (method, path) -> required scope for key-holding callers.
SCOPED_ROUTES = {
    ('POST', '/api/trademarket/items'): 'write:market',
    ('GET', '/api/trademarket/listings'): 'read:market',
    ('GET', '/api/trademarket/listings/TestItem'): 'read:market',
    ('GET', '/api/trademarket/item/TestItem/price'): 'read:market',
    ('GET', '/api/trademarket/history/TestItem/price'): 'read:market_archive',
    ('GET', '/api/trademarket/history/TestItem/latest'): 'read:market_archive',
    ('POST', '/api/lootpool/items'): 'write:lootpool',
    ('GET', '/api/lootpool/items'): 'read:lootpool',
    ('GET', '/api/lootpool/current'): 'read:lootpool',
    ('GET', '/api/lootpool/all'): 'read:lootpool',
    ('GET', '/api/lootpool/2026/10'): 'read:lootpool',
    ('POST', '/api/raidpool/items'): 'write:raidpool',
    ('GET', '/api/raidpool/items'): 'read:raidpool',
    ('GET', '/api/raidpool/current'): 'read:raidpool',
    ('GET', '/api/raidpool/all'): 'read:raidpool',
    ('GET', '/api/raidpool/2026/10'): 'read:raidpool',
    ('POST', '/api/raidpool/gambits'): 'write:raidpool',
    ('GET', '/api/raidpool/gambits/current'): 'read:raidpool',
}

# Subset of SCOPED_ROUTES the shared mod key may call (default-deny elsewhere).
MOD_ALLOWED_ROUTES = [
    ('POST', '/api/trademarket/items'),
    ('GET', '/api/trademarket/item/TestItem/price'),
    ('GET', '/api/trademarket/history/TestItem/price'),
    ('GET', '/api/trademarket/history/TestItem/latest'),
    ('POST', '/api/lootpool/items'),
    ('GET', '/api/lootpool/current'),
    ('POST', '/api/raidpool/items'),
    ('GET', '/api/raidpool/current'),
    ('POST', '/api/raidpool/gambits'),
]

MOD_DENIED_ROUTES = [r for r in SCOPED_ROUTES if r not in MOD_ALLOWED_ROUTES]


def _kwargs(method):
    # A JSON body so POST views fail fast (400) instead of touching services.
    return {'json': []} if method == 'POST' else {}


class TestPublicRoutes(ApiTestBase):
    def test_public_routes_do_not_require_a_key(self):
        for method, path in PUBLIC_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, **_kwargs(method))
                self.assertNotIn(resp.status_code, (401, 403),
                                 f'{method} {path} should be public')

    def test_aspect_route_is_public(self):
        # Locked in deliberately: the website calls this endpoint keyless.
        resp = self.request('GET', '/api/aspect/archer/TestAspect')
        self.assertEqual(resp.status_code, 200)


class TestScopedRoutes(ApiTestBase):
    def test_missing_key_returns_401(self):
        for (method, path) in SCOPED_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, **_kwargs(method))
                self.assertEqual(resp.status_code, 401)
                self.assertEqual(resp.get_json(), {'error': 'Missing API key'})

    def test_unknown_key_returns_403(self):
        for (method, path) in SCOPED_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, token='not-a-real-key',
                                    **_kwargs(method))
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.get_json(),
                                 {'error': 'Invalid or revoked API key'})

    def test_key_without_scope_returns_403(self):
        self.add_key('scopeless-key', scopes=[])
        for (method, path) in SCOPED_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, token='scopeless-key',
                                    **_kwargs(method))
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(resp.get_json(),
                                 {'error': 'Forbidden, missing scope'})

    def test_key_with_scope_passes_auth(self):
        self.add_key('full-key', scopes=ALL_SCOPES)
        for (method, path) in SCOPED_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, token='full-key',
                                    **_kwargs(method))
                self.assertNotIn(resp.status_code, (401, 403),
                                 f'{method} {path} should accept a scoped key')


class TestModKey(ApiTestBase):
    def test_mod_key_passes_on_allowed_routes(self):
        for method, path in MOD_ALLOWED_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, token=MOD_TOKEN,
                                    **_kwargs(method))
                self.assertNotIn(resp.status_code, (401, 403),
                                 f'{method} {path} should accept the mod key')

    def test_mod_key_denied_everywhere_else(self):
        for method, path in MOD_DENIED_ROUTES:
            with self.subTest(route=f'{method} {path}'):
                resp = self.request(method, path, token=MOD_TOKEN,
                                    **_kwargs(method))
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(
                    resp.get_json(),
                    {'error': 'Forbidden, mod key not allowed on this endpoint'})


if __name__ == '__main__':
    unittest.main()
