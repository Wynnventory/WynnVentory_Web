"""Tests for the /api/v2 cross-cutting conventions: envelope, ISO-8601 dates,
JSON 404/405, and CORS."""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ALL_SCOPES, ApiTestBase


class TestEnvelope(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)

    def test_status_route_uses_data_envelope(self):
        resp = self.request('GET', '/api/v2/status', token='reader')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {'data': {'status': 'ok', 'version': 'v2'}})

    def test_content_type_is_json(self):
        resp = self.request('GET', '/api/v2/status', token='reader')
        self.assertEqual(resp.mimetype, 'application/json')


class TestNotFoundAndMethods(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)

    def test_unknown_v2_path_returns_json_404(self):
        resp = self.request('GET', '/api/v2/definitely/not/here', token='reader')
        self.assertEqual(resp.status_code, 404)
        body = resp.get_json()
        self.assertEqual(body['error']['code'], 'not_found')
        self.assertIn('/api/v2/definitely/not/here', body['error']['message'])

    def test_unknown_v2_path_is_json_even_without_key(self):
        # Auth never runs for unmatched routes; the 404 must still be JSON.
        resp = self.request('GET', '/api/v2/nope')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['error']['code'], 'not_found')

    def test_unknown_web_path_still_redirects_to_homepage(self):
        resp = self.request('GET', '/definitely-not-a-page')
        self.assertEqual(resp.status_code, 302)

    def test_unknown_v1_path_still_redirects(self):
        # v1 behavior is frozen: typo'd /api paths keep the legacy redirect.
        resp = self.request('GET', '/api/definitely-not-a-route')
        self.assertEqual(resp.status_code, 302)

    def test_wrong_method_returns_json_405(self):
        resp = self.request('POST', '/api/v2/status', token='reader', json={})
        self.assertEqual(resp.status_code, 405)
        self.assertEqual(resp.get_json()['error']['code'], 'method_not_allowed')


class TestCors(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)

    def test_success_responses_carry_cors_headers(self):
        resp = self.request('GET', '/api/v2/status', token='reader')
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')

    def test_error_responses_carry_cors_headers(self):
        resp = self.request('GET', '/api/v2/nope')
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')

    def test_preflight_does_not_require_a_key(self):
        resp = self.client.open('/api/v2/status', method='OPTIONS')
        self.assertNotIn(resp.status_code, (401, 403))
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')


class TestResponseSerialization(unittest.TestCase):
    def test_datetimes_serialize_as_iso8601_utc(self):
        from modules.routes.api.v2.responses import v2_json

        aware = datetime(2026, 8, 31, 12, 0, 0, 123456, tzinfo=timezone.utc)
        naive = datetime(2026, 8, 31, 12, 0, 0)
        resp = v2_json({'aware': aware, 'naive': naive})
        self.assertEqual(
            resp.get_json(),
            {'aware': '2026-08-31T12:00:00Z', 'naive': '2026-08-31T12:00:00Z'})

    def test_paginated_envelope_math(self):
        from modules.routes.api.v2.responses import paginated

        resp = paginated([1, 2, 3], page=2, page_size=3, total_items=7)
        self.assertEqual(resp.get_json()['pagination'], {
            'page': 2, 'page_size': 3, 'total_items': 7, 'total_pages': 3})

    def test_paginated_empty_result_has_one_page(self):
        from modules.routes.api.v2.responses import paginated

        resp = paginated([], page=1, page_size=50, total_items=0)
        self.assertEqual(resp.get_json()['pagination']['total_pages'], 1)


class TestSchemaPrimitives(unittest.TestCase):
    def test_strict_bool_matrix(self):
        from pydantic import BaseModel, ValidationError

        from modules.schemas.v2.common import StrictBool

        class Model(BaseModel):
            flag: StrictBool

        for raw, expected in (('true', True), ('TRUE', True), ('1', True),
                              ('false', False), ('False', False), ('0', False)):
            self.assertEqual(Model.model_validate({'flag': raw}).flag, expected)

        for raw in ('yes', 'no', '2', ''):
            with self.assertRaises(ValidationError):
                Model.model_validate({'flag': raw})

    def test_utc_date_parsing(self):
        from pydantic import BaseModel

        from modules.schemas.v2.common import UtcDate

        class Model(BaseModel):
            when: UtcDate

        parsed = Model.model_validate({'when': '2026-08-31'}).when
        self.assertEqual(parsed, datetime(2026, 8, 31, tzinfo=timezone.utc))

    def test_query_models_forbid_unknown_params(self):
        from pydantic import ValidationError

        from modules.schemas.v2.common import PaginationParams

        with self.assertRaises(ValidationError):
            PaginationParams.model_validate({'page': 1, 'pageSize': 5})


if __name__ == '__main__':
    unittest.main()
