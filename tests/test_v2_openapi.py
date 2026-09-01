"""Parity test between the registered /api/v2 routes and docs/openapi_v2.yaml.

Fails when a route is added without documenting it, or when the spec documents
a route that does not exist.
"""
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import get_test_app

SPEC_PATH = os.path.join(os.path.dirname(__file__), '..', 'docs', 'openapi_v2.yaml')


def _flask_rule_to_openapi(rule):
    """/api/v2/items/<item_name> -> /items/{item_name} (server-relative)."""
    path = str(rule)[len('/api/v2'):] or '/'
    out = []
    for segment in path.split('/'):
        if segment.startswith('<') and segment.endswith('>'):
            name = segment[1:-1].split(':')[-1]
            out.append('{' + name + '}')
        else:
            out.append(segment)
    return '/'.join(out)


class TestOpenApiParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SPEC_PATH, encoding='utf-8') as fh:
            cls.spec = yaml.safe_load(fh)
        cls.app = get_test_app()

    def _registered_operations(self):
        operations = set()
        for rule in self.app.url_map.iter_rules():
            if not str(rule).startswith('/api/v2'):
                continue
            path = _flask_rule_to_openapi(rule)
            for method in rule.methods:
                if method in ('HEAD', 'OPTIONS'):
                    continue
                operations.add((method.lower(), path))
        return operations

    def _documented_operations(self):
        operations = set()
        for path, item in self.spec['paths'].items():
            for method in item:
                if method in ('get', 'post', 'put', 'patch', 'delete'):
                    operations.add((method, path))
        return operations

    def test_every_route_is_documented(self):
        missing = self._registered_operations() - self._documented_operations()
        self.assertFalse(
            missing,
            f'Routes missing from docs/openapi_v2.yaml: {sorted(missing)}')

    def test_every_documented_path_exists(self):
        phantom = self._documented_operations() - self._registered_operations()
        self.assertFalse(
            phantom,
            f'docs/openapi_v2.yaml documents nonexistent routes: {sorted(phantom)}')

    def test_spec_declares_security(self):
        self.assertIn('security', self.spec)
        self.assertIn('securitySchemes', self.spec['components'])


class TestAggregatedPriceStatsParity(unittest.TestCase):
    """history/latest returns the aggregation pipeline's $project — pin the
    spec's AggregatedPriceStats to exactly those fields so they cannot
    drift apart again."""

    @classmethod
    def setUpClass(cls):
        with open(SPEC_PATH, encoding='utf-8') as fh:
            cls.spec = yaml.safe_load(fh)

    def _pipeline_fields(self):
        from unittest.mock import MagicMock, patch

        from modules.repositories import market_repo

        with patch.object(market_repo, 'get_collection') as get_collection:
            get_collection.return_value.aggregate.return_value = iter([])
            market_repo.get_historic_average('Divzer')
        pipeline = get_collection.return_value.aggregate.call_args.args[0]
        project = next(stage['$project'] for stage in pipeline
                       if '$project' in stage)
        return {field for field in project if field != '_id'}

    def test_schema_matches_aggregation_project(self):
        documented = set(
            self.spec['components']['schemas']['AggregatedPriceStats']
            ['properties'])
        self.assertEqual(documented, self._pipeline_fields())

    def test_history_latest_uses_the_aggregate_schema(self):
        response = (self.spec['paths']
                    ['/market/items/{item_name}/history/latest']['get']
                    ['responses']['200'])
        data_schema = (response['content']['application/json']['schema']
                       ['properties']['data'])
        self.assertEqual(data_schema.get('$ref'),
                         '#/components/schemas/AggregatedPriceStats')

    def test_price_stats_does_not_claim_document_count(self):
        # document_count exists only on the aggregate.
        price_stats = self.spec['components']['schemas']['PriceStats']
        self.assertNotIn('document_count', price_stats['properties'])


if __name__ == '__main__':
    unittest.main()
