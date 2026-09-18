"""Serializers turning pool repository documents into v2 response shapes.

v1 exposes pool contents under three different names (regions / region_items /
group_items with items / loot_items inside); v2 always uses
groups: [{"name": ..., "items": [...]}].
"""
from modules.routes.api.v2.serializers.common import (
    item_type_from_storage,
    rarity_from_storage,
    subtype_from_storage,
)


def _serialize_pool_item(item):
    return {
        'name': item.get('name'),
        'amount': item.get('amount'),
        'rarity': rarity_from_storage(item.get('rarity')),
        'item_type': item_type_from_storage(item.get('itemType')),
        'subtype': subtype_from_storage(item.get('subtype') or item.get('type')),
        'tier': item.get('tier'),
        'shiny': bool(item.get('shiny')),
        'shiny_stat': item.get('shinyStat'),
        'icon': item.get('icon'),
    }


def serialize_raw_pool(doc):
    """A raw pool document ({year, week, regions: [...]}) -> v2 pool object,
    grouped by region."""
    return {
        'year': doc.get('year'),
        'week': doc.get('week'),
        'groups': [
            {
                'name': region.get('region'),
                'type': region.get('type'),
                'timestamp': region.get('timestamp'),
                'items': [_serialize_pool_item(item)
                          for item in region.get('items') or []],
            }
            for region in doc.get('regions') or []
        ],
    }


def serialize_processed_region(doc):
    """A processed per-region pool document (lootpool region_items / raidpool
    group_items) -> v2 region object with uniform groups."""
    grouped = doc.get('region_items') or doc.get('group_items') or []
    return {
        'region': doc.get('region'),
        'year': doc.get('year'),
        'week': doc.get('week'),
        'timestamp': doc.get('timestamp'),
        'groups': [
            {
                'name': group.get('group'),
                'items': [_serialize_pool_item(item)
                          for item in group.get('items') or group.get('loot_items') or []],
            }
            for group in grouped
        ],
    }
