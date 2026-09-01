"""Serializers turning market repository documents into v2 response shapes."""
from modules.routes.api.v2.serializers.common import (
    item_type_from_storage,
    rarity_from_storage,
    subtype_from_storage,
)


def serialize_listing(doc):
    """A trademarket_listings document -> v2 listing object.

    Internal bookkeeping fields (hash_code, mod_version) are not exposed.
    """
    shiny_stat = doc.get('shiny_stat')
    return {
        'name': doc.get('name'),
        'rarity': rarity_from_storage(doc.get('rarity')),
        'item_type': item_type_from_storage(doc.get('item_type')),
        'subtype': subtype_from_storage(doc.get('type')),
        'tier': doc.get('tier'),
        'unidentified': bool(doc.get('unidentified')),
        'shiny': shiny_stat is not None,
        'shiny_stat': shiny_stat,
        'overall_roll': doc.get('overall_roll'),
        'stat_rolls': doc.get('stat_rolls'),
        'reroll_count': doc.get('reroll_count'),
        'amount': doc.get('amount'),
        'listing_price': doc.get('listing_price'),
        'icon': doc.get('icon'),
        'timestamp': doc.get('timestamp'),
    }


def serialize_price_stats(doc):
    """A trademarket_averages/_archive document (or the aggregated history
    stats) -> v2 price-statistics object. Passes computed price fields through
    untouched and normalizes the vocabulary fields."""
    out = {key: value for key, value in doc.items() if key != '_id'}
    if 'item_type' in out:
        out['item_type'] = item_type_from_storage(out['item_type'])
    if 'rarity' in out:
        out['rarity'] = rarity_from_storage(out['rarity'])
    return out


def serialize_ranking_entry(doc):
    """A ranking row -> v2 shape (camelCase itemType becomes item_type)."""
    out = {key: value for key, value in doc.items() if key != 'itemType'}
    if 'itemType' in doc:
        out['item_type'] = item_type_from_storage(doc['itemType'])
    return out
