"""Tests for the /api/v2/lootpools, /api/v2/raidpools and /api/v2/gambits
endpoints."""
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from api_test_base import ALL_SCOPES, ApiTestBase

RAW_POOL = {
    'year': 2026, 'week': 35,
    'regions': [
        {
            'region': 'Silent Expanse',
            'timestamp': datetime(2026, 8, 28, 18, 0, 0, tzinfo=timezone.utc),
            'type': 'Lootrun',
            'items': [
                {'name': 'Divzer', 'amount': 1, 'rarity': 'Mythic',
                 'shiny': True, 'shinyStat': {'statType': 'raidsCompleted'},
                 'icon': 'bow', 'itemType': 'Weapon', 'subtype': 'Bow',
                 'tier': None},
            ],
        },
    ],
}

PROCESSED_LOOT_REGION = {
    'region': 'Molten Heights',
    'year': 2026, 'week': 35,
    'timestamp': datetime(2026, 8, 28, tzinfo=timezone.utc),
    'region_items': [
        {'group': 'Mythic',
         'items': [{'name': 'Warp', 'amount': 1, 'rarity': 'Mythic',
                    'itemType': 'Weapon', 'type': 'Wand', 'shiny': False,
                    'shinyStat': None, 'icon': 'wand', 'tier': None}]},
    ],
}

PROCESSED_RAID_REGION = {
    'region': 'TNA',
    'year': 2026, 'week': 35,
    'timestamp': datetime(2026, 8, 28, tzinfo=timezone.utc),
    'group_items': [
        {'group': 'Aspect',
         'loot_items': [{'name': 'Aspect of the Berserker', 'amount': 1,
                         'rarity': 'Fabled', 'itemType': 'AspectItem',
                         'type': None, 'shiny': False, 'icon': 'aspect',
                         'tier': None}]},
    ],
}


class PoolsTestBase(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.add_key('reader', scopes=ALL_SCOPES)

    def patch_pools(self, target, **kwargs):
        p = patch(f'modules.routes.api.v2.pools.{target}', **kwargs)
        mock = p.start()
        self.addCleanup(p.stop)
        return mock

    def patch_service(self, name, **kwargs):
        p = patch(f'modules.services.base_pool_service.{name}', **kwargs)
        mock = p.start()
        self.addCleanup(p.stop)
        return mock


class TestPoolLists(PoolsTestBase):
    def test_lootpools_are_paginated_with_totals(self):
        self.patch_service('get_pools', return_value={
            'page': 1, 'page_size': 5, 'count': 1, 'pools': [dict(RAW_POOL)]})
        self.patch_pools('count_pool_weeks', return_value=12)
        resp = self.request('GET', '/api/v2/lootpools', token='reader')
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body['pagination'],
                         {'page': 1, 'page_size': 5,
                          'total_items': 12, 'total_pages': 3})
        pool = body['data'][0]
        self.assertEqual(pool['year'], 2026)
        group = pool['groups'][0]
        self.assertEqual(group['name'], 'Silent Expanse')
        item = group['items'][0]
        self.assertEqual(item['item_type'], 'weapon')
        self.assertEqual(item['subtype'], 'bow')
        self.assertEqual(item['rarity'], 'mythic')
        self.assertTrue(item['shiny'])
        self.assertEqual(item['shiny_stat'], {'statType': 'raidsCompleted'})
        self.assertNotIn('shinyStat', item)

    def test_page_size_above_pool_cap_is_a_400(self):
        resp = self.request('GET', '/api/v2/raidpools?page_size=50',
                            token='reader')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['error']['code'], 'validation_error')

    def test_scopes_are_pool_specific(self):
        self.add_key('loot-only', scopes=['read:lootpool'])
        ok = self.request('GET', '/api/v2/lootpools/current/items',
                          token='loot-only')
        denied = self.request('GET', '/api/v2/raidpools/current/items',
                              token='loot-only')
        self.assertNotEqual(ok.status_code, 403)
        self.assertEqual(denied.status_code, 403)


class TestSpecificPool(PoolsTestBase):
    def test_unknown_week_is_a_404(self):
        self.patch_service('get_specific_pool', return_value={})
        resp = self.request('GET', '/api/v2/lootpools/2026/2', token='reader')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['error']['code'], 'not_found')

    def test_known_week_is_enveloped(self):
        self.patch_service('get_specific_pool', return_value=dict(RAW_POOL))
        resp = self.request('GET', '/api/v2/lootpools/2026/35', token='reader')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['week'], 35)

    def test_out_of_range_week_is_a_400(self):
        resp = self.request('GET', '/api/v2/lootpools/2026/99', token='reader')
        self.assertEqual(resp.status_code, 400)
        details = resp.get_json()['error']['details']
        self.assertEqual(details[0]['field'], 'week')

    def test_current_pool_delegates_to_week_lookup(self):
        mock = self.patch_service('get_specific_pool',
                                  return_value=dict(RAW_POOL))
        resp = self.request('GET', '/api/v2/raidpools/current', token='reader')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(mock.called)


class TestProcessedItems(PoolsTestBase):
    def test_loot_and_raid_normalize_to_the_same_groups_shape(self):
        for pool, region_doc in (('lootpools', PROCESSED_LOOT_REGION),
                                 ('raidpools', PROCESSED_RAID_REGION)):
            with self.subTest(pool=pool):
                self.patch_service('get_current_pools',
                                   return_value=[dict(region_doc)])
                resp = self.request('GET', f'/api/v2/{pool}/current/items',
                                    token='reader')
                self.assertEqual(resp.status_code, 200)
                region = resp.get_json()['data'][0]
                self.assertIn('groups', region)
                self.assertNotIn('region_items', region)
                self.assertNotIn('group_items', region)
                group = region['groups'][0]
                self.assertIn('name', group)
                self.assertIn('items', group)
                self.assertNotIn('loot_items', group)

    def test_aspect_item_type_is_normalized(self):
        self.patch_service('get_current_pools',
                           return_value=[dict(PROCESSED_RAID_REGION)])
        resp = self.request('GET', '/api/v2/raidpools/current/items',
                            token='reader')
        item = resp.get_json()['data'][0]['groups'][0]['items'][0]
        self.assertEqual(item['item_type'], 'aspect')


class TestGambits(PoolsTestBase):
    def patch_gambits(self, **kwargs):
        p = patch('modules.services.raidpool_service.get_current_gambits',
                  **kwargs)
        mock = p.start()
        self.addCleanup(p.stop)
        return mock

    def test_current_gambits_are_enveloped(self):
        self.patch_gambits(return_value={'year': 2026, 'gambits': ['x']})
        resp = self.request('GET', '/api/v2/gambits/current', token='reader')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['year'], 2026)

    def test_no_gambits_is_a_404(self):
        self.patch_gambits(return_value={})
        resp = self.request('GET', '/api/v2/gambits/current', token='reader')
        self.assertEqual(resp.status_code, 404)

    def test_requires_raidpool_scope(self):
        self.add_key('loot-only', scopes=['read:lootpool'])
        resp = self.request('GET', '/api/v2/gambits/current', token='loot-only')
        self.assertEqual(resp.status_code, 403)


if __name__ == '__main__':
    unittest.main()
