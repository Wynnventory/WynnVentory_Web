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
