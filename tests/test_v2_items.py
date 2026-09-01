"""Tests for the /api/v2/items and /api/v2/aspects endpoints."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ApiTestBase


class ItemsTestBase(ApiTestBase):
    def setUp(self):
        super().setUp()
        # Items/aspects need a valid key but no scope.
        self.add_key('keyholder', scopes=[])


class TestGetItem(ItemsTestBase):
    def test_item_is_enveloped(self):
        self.service_mocks['fetch_item'].return_value = {'name': 'Divzer'}
        resp = self.request('GET', '/api/v2/items/Divzer', token='keyholder')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {'data': {'name': 'Divzer'}})

    def test_unknown_item_is_a_404(self):
        self.service_mocks['fetch_item'].return_value = None
        resp = self.request('GET', '/api/v2/items/Nope', token='keyholder')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['error']['code'], 'not_found')

    def test_unsupported_item_type_is_a_404_not_a_500(self):
        self.service_mocks['fetch_item'].side_effect = ValueError('bad type')
        try:
            resp = self.request('GET', '/api/v2/items/Weird', token='keyholder')
        finally:
            self.service_mocks['fetch_item'].side_effect = None
        self.assertEqual(resp.status_code, 404)

    def test_requires_a_key(self):
        resp = self.request('GET', '/api/v2/items/Divzer')
        self.assertEqual(resp.status_code, 401)

    def test_upstream_failure_is_a_502_not_a_404(self):
        from modules.routes.api.wynncraft_api import UpstreamError

        self.service_mocks['fetch_item'].side_effect = UpstreamError('down')
        try:
            resp = self.request('GET', '/api/v2/items/Divzer',
                                token='keyholder')
        finally:
            self.service_mocks['fetch_item'].side_effect = None
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json()['error']['code'],
                         'upstream_unavailable')

    def test_unknown_query_param_is_a_400(self):
        resp = self.request('GET', '/api/v2/items/Divzer?shiny=true',
                            token='keyholder')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['error']['code'], 'validation_error')


class TestItemBatch(ItemsTestBase):
    def test_batch_maps_names_to_items(self):
        self.service_mocks['fetch_item'].side_effect = (
            lambda name: {'name': name} if name != 'Missing' else None)
        try:
            resp = self.request('POST', '/api/v2/items/batch', token='keyholder',
                                json={'item_names': ['Divzer', 'Missing']})
        finally:
            self.service_mocks['fetch_item'].side_effect = None
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {
            'data': {'Divzer': {'name': 'Divzer'}, 'Missing': None}})

    def test_empty_list_is_a_400(self):
        resp = self.request('POST', '/api/v2/items/batch', token='keyholder',
                            json={'item_names': []})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['error']['code'], 'validation_error')

    def test_more_than_100_names_is_a_400(self):
        resp = self.request('POST', '/api/v2/items/batch', token='keyholder',
                            json={'item_names': ['x'] * 101})
        self.assertEqual(resp.status_code, 400)

    def test_upstream_failure_is_a_502(self):
        from modules.routes.api.wynncraft_api import UpstreamError

        self.service_mocks['fetch_item'].side_effect = UpstreamError('down')
        try:
            resp = self.request('POST', '/api/v2/items/batch', token='keyholder',
                                json={'item_names': ['Divzer']})
        finally:
            self.service_mocks['fetch_item'].side_effect = None
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.get_json()['error']['code'],
                         'upstream_unavailable')

    def test_upstream_failure_does_not_wait_for_in_flight_lookups(self):
        """The 502 must go out while the already-running lookups are still
        blocked upstream, instead of holding the worker for their timeouts.

        Queued lookups are dropped either way (Executor.map cancels them as
        it unwinds); what the explicit shutdown adds is not waiting on the
        in-flight ones.
        """
        import threading

        from modules.routes.api.wynncraft_api import UpstreamError

        release = threading.Event()
        self.addCleanup(release.set)
        lock = threading.Lock()
        started, finished = [], []

        def lookup(name):
            # The first submitted name fails immediately; the rest occupy the
            # remaining workers and stay blocked for the whole request.
            if name == 'Item0':
                raise UpstreamError('down')
            with lock:
                started.append(name)
            release.wait(timeout=10)
            with lock:
                finished.append(name)
            return {'name': name}

        self.service_mocks['fetch_item'].side_effect = lookup
        try:
            resp = self.request('POST', '/api/v2/items/batch', token='keyholder',
                                json={'item_names': [f'Item{i}'
                                                     for i in range(100)]})
        finally:
            release.set()
            self.service_mocks['fetch_item'].side_effect = None

        self.assertEqual(resp.status_code, 502)
        with lock:
            # Nothing completed: the response overtook every blocked lookup.
            self.assertEqual(finished, [])
            # And the queue behind them was never worked through.
            self.assertLessEqual(len(started), 8)

    def test_malformed_json_is_a_400(self):
        resp = self.client.post('/api/v2/items/batch',
                                headers=self.auth_headers('keyholder'),
                                data='{not json',
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['error']['code'], 'validation_error')

    def test_unknown_body_field_is_a_400(self):
        resp = self.request('POST', '/api/v2/items/batch', token='keyholder',
                            json={'item_names': ['x'], 'extra': 1})
        self.assertEqual(resp.status_code, 400)
        details = resp.get_json()['error']['details']
        self.assertEqual(details[0]['location'], 'body')


class TestQuickSearchUpstreamStatuses(unittest.TestCase):
    """quick_search_item must return None only for genuinely missing items
    (Wynncraft 400/404) and raise UpstreamError for other failures."""

    def _response(self, status):
        from unittest.mock import MagicMock

        import requests

        resp = MagicMock()
        resp.status_code = status
        if status >= 400:
            resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
                f'{status} error')
        else:
            resp.raise_for_status.return_value = None
        return resp

    def _call(self, status, name):
        from unittest.mock import patch

        from modules.routes.api import wynncraft_api

        with patch.object(wynncraft_api.requests, 'get',
                          return_value=self._response(status)):
            # Unique names per case keep the TTL cache out of the way.
            return wynncraft_api.quick_search_item(name)

    def test_404_and_400_mean_missing_item(self):
        self.assertIsNone(self._call(404, 'missing-404'))
        self.assertIsNone(self._call(400, 'missing-400'))

    def test_429_and_5xx_raise_upstream_error(self):
        from modules.routes.api.wynncraft_api import UpstreamError

        for status in (429, 500, 502):
            with self.subTest(status=status):
                with self.assertRaises(UpstreamError):
                    self._call(status, f'failing-{status}')


class TestArrayShapedUpstreamResponses(unittest.TestCase):
    """Wynncraft v3 returns arrays of objects where the code was written
    against name-keyed maps; both shapes must parse."""

    def _get_returning(self, payload):
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.return_value = payload
        return resp

    def _quick_search(self, payload, name):
        from unittest.mock import patch

        from modules.routes.api import wynncraft_api

        with patch.object(wynncraft_api.requests, 'get',
                          return_value=self._get_returning(payload)):
            # Unique names per case keep the TTL cache out of the way.
            return wynncraft_api.quick_search_item(name)

    def test_item_search_array_is_matched_by_display_name(self):
        payload = [{'displayName': 'Divzer', 'internalName': 'Divzer',
                    'type': 'weapon', 'subType': 'bow', 'tier': 'mythic'}]
        found = self._quick_search(payload, 'divzer-array')
        # 'divzer-array' != 'Divzer' after cleaning — no match — so probe
        # with the matching name (unique per test run via the payload).
        self.assertIsNone(found)
        found = self._quick_search(
            [dict(payload[0], displayName='Divzer Array')], 'Divzer Array')
        self.assertEqual(found['item_name'], 'Divzer Array')
        self.assertEqual(found['subType'], 'bow')

    def test_item_search_legacy_map_still_matched(self):
        payload = {'Divzer Legacy': {'type': 'weapon', 'weaponType': 'bow'}}
        found = self._quick_search(payload, 'Divzer Legacy')
        self.assertEqual(found['item_name'], 'Divzer Legacy')

    def test_aspects_array_is_scanned_by_name(self):
        from unittest.mock import patch

        from modules.routes.api import wynncraft_api

        payload = [
            {'name': 'Aspect of the Iron String', 'rarity': 'Legendary'},
            {'name': 'Aspect of Stinging Swarms', 'rarity': 'Fabled'},
        ]
        with patch.object(wynncraft_api.requests, 'get',
                          return_value=self._get_returning(payload)):
            hit = wynncraft_api.get_aspect_by_name(
                'archer-a', 'Aspect of the Iron String')
            case_insensitive = wynncraft_api.get_aspect_by_name(
                'archer-b', 'aspect of stinging swarms')
            miss = wynncraft_api.get_aspect_by_name('archer-c', 'Nope')
        self.assertEqual(hit['rarity'], 'Legendary')
        self.assertEqual(case_insensitive['rarity'], 'Fabled')
        self.assertIsNone(miss)


class TestNewSchemaNormalization(unittest.TestCase):
    """_process must accept the current v3 fields (displayName/tier/subType)
    as well as the legacy ones the models were written against."""

    def test_new_schema_weapon_is_processed(self):
        from modules.services.item_service import _process

        item = _process({
            'displayName': 'Divzer', 'internalName': 'Divzer',
            'type': 'weapon', 'subType': 'bow', 'tier': 'mythic',
            'attackSpeed': 'superFast', 'averageDps': 957,
            'powderSlots': 3, 'dropRestriction': 'normal',
            'requirements': {'level': 97, 'classRequirement': 'archer'},
            'identifications': {}, 'base': {},
        })
        self.assertEqual(item['name'], 'Divzer')
        self.assertEqual(item['item_type'], 'weapon')
        self.assertEqual(item['item_subtype'], 'bow')
        self.assertEqual(item['rarity'], 'Mythic')
        self.assertEqual(item['attack_speed'], 'Superfast')

    def test_legacy_schema_still_processed(self):
        from modules.services.item_service import _process

        item = _process({
            'item_name': 'Divzer', 'type': 'weapon', 'weaponType': 'bow',
            'rarity': 'mythic', 'attackSpeed': 'super_fast',
            'identifications': {}, 'base': {}, 'requirements': {},
        })
        self.assertEqual(item['item_subtype'], 'bow')
        self.assertEqual(item['rarity'], 'Mythic')

    def test_search_results_accept_array_and_legacy_map(self):
        from modules.services.item_service import _extract_result_items

        entry = {'displayName': 'Divzer', 'type': 'weapon', 'subType': 'bow'}
        as_array = _extract_result_items({'results': [dict(entry)]})
        self.assertEqual(as_array[0]['displayName'], 'Divzer')

        as_map = _extract_result_items(
            {'results': {'Divzer': {'type': 'weapon', 'weaponType': 'bow'}}})
        self.assertEqual(as_map[0]['item_name'], 'Divzer')

        self.assertEqual(_extract_result_items({'results': None}), [])


class TestItemTypeFallbackNormalization(unittest.TestCase):
    def test_unlisted_storage_values_snake_case(self):
        from modules.routes.api.v2.serializers.common import (
            item_type_from_storage)

        self.assertEqual(item_type_from_storage('EmeraldItem'), 'emerald')
        self.assertEqual(item_type_from_storage('SomeNewThingItem'),
                         'some_new_thing')


class TestAspects(ItemsTestBase):
    def test_aspect_is_enveloped(self):
        self.service_mocks['fetch_aspect'].return_value = {'name': 'Arrow Shield'}
        resp = self.request('GET', '/api/v2/aspects/archer/Arrow%20Shield',
                            token='keyholder')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['name'], 'Arrow Shield')

    def test_unknown_aspect_is_a_404_not_a_500(self):
        self.service_mocks['fetch_aspect'].return_value = None
        resp = self.request('GET', '/api/v2/aspects/archer/Nope',
                            token='keyholder')
        self.assertEqual(resp.status_code, 404)

    def test_requires_a_key_unlike_v1(self):
        resp = self.request('GET', '/api/v2/aspects/archer/Anything')
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
