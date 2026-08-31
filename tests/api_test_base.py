"""Shared fixture for HTTP-level API tests.

Builds the real app via create_app() exactly once per test process (the route
blueprints are module-level singletons and cannot be re-registered), with all
external boundaries patched for the lifetime of the process: Mongo
(modules.db.get_client), the auth key lookup (modules.auth.get_collection),
usage recording (modules.auth.enqueue), and the Wynncraft upstream services.

Per-test state (the fake API key store) lives in module-level dicts that
ApiTestBase.setUp resets.

The filename intentionally does not match the test discovery pattern.
"""
import hashlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

ALL_SCOPES = [
    'read:market', 'write:market', 'read:market_archive',
    'read:lootpool', 'write:lootpool',
    'read:raidpool', 'write:raidpool',
]

MOD_TOKEN = 'test-mod-key-token'
MOD_KEY_HASH = hashlib.sha256(MOD_TOKEN.encode()).hexdigest()

# Fake api_keys store consulted by the patched auth lookup: hash -> key doc.
_keys_by_hash = {}

_app = None
_service_mocks = {}

# The patched Mongo client. Every non-auth collection resolves to the same
# child mock: mongo_client_mock.get_default_database()[<any name>].
mongo_client_mock = MagicMock()


def shared_collection_mock():
    """The mock object all repository collections resolve to."""
    return mongo_client_mock.get_default_database.return_value.__getitem__.return_value


def _find_key_doc(query, *args, **kwargs):
    doc = _keys_by_hash.get(query.get('key_hash'))
    if doc is None:
        return None
    return {'owner': doc['owner'], 'scopes': doc['scopes']}


def get_test_app():
    """Create (once) and return the fully patched app."""
    global _app
    if _app is not None:
        return _app

    # All repository code reaches Mongo through modules.db.get_collection,
    # which resolves get_client at call time — one patch blocks every collection.
    patch('modules.db.get_client', return_value=mongo_client_mock).start()
    patch('modules.db.ensure_debug_indexes').start()

    # modules.auth holds its own get_collection reference for key lookups.
    api_keys_coll = MagicMock()
    api_keys_coll.find_one.side_effect = _find_key_doc
    patch('modules.auth.get_collection', return_value=api_keys_coll).start()
    patch('modules.auth.enqueue').start()

    # The mod key is compared against modules.auth._MOD_KEY_HASH.
    patch('modules.auth._MOD_KEY_HASH', new=MOD_KEY_HASH).start()

    # Never call the real Wynncraft API from tests.
    _service_mocks['fetch_item'] = patch(
        'modules.services.item_service.fetch_item',
        return_value={'name': 'Test Item'}).start()
    _service_mocks['search_items'] = patch(
        'modules.services.item_service.search_items',
        return_value={'items': [], 'next_page': None}).start()
    _service_mocks['fetch_aspect'] = patch(
        'modules.services.aspect_service.fetch_aspect',
        return_value={'name': 'Test Aspect'}).start()

    from modules import create_app
    _app = create_app()
    _app.config['TESTING'] = True
    return _app


class ApiTestBase(unittest.TestCase):
    """Base test case that serves the full app through Flask's test client."""

    def setUp(self):
        self.app = get_test_app()
        self.client = self.app.test_client()
        self.service_mocks = _service_mocks
        _keys_by_hash.clear()
        _keys_by_hash[MOD_KEY_HASH] = {'owner': 'mod', 'scopes': list(ALL_SCOPES)}
        # Reset shared upstream-service mocks to their defaults.
        for mock in _service_mocks.values():
            mock.reset_mock(return_value=False, side_effect=True)
        _service_mocks['fetch_item'].return_value = {'name': 'Test Item'}
        _service_mocks['search_items'].return_value = {'items': [], 'next_page': None}
        _service_mocks['fetch_aspect'].return_value = {'name': 'Test Aspect'}

    def add_key(self, token, scopes, owner='tester'):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        _keys_by_hash[token_hash] = {'owner': owner, 'scopes': list(scopes)}
        return token_hash

    @staticmethod
    def auth_headers(token):
        return {'Authorization': f'Api-Key {token}'}

    def request(self, method, path, token=None, **kwargs):
        headers = kwargs.pop('headers', {})
        if token is not None:
            headers.update(self.auth_headers(token))
        return self.client.open(path, method=method, headers=headers, **kwargs)
