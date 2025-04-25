from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from modules.db import get_collection
from modules.models.collection_types import Collection as ColEnum


def save(item: Dict[str, Any]) -> None:
    """
    Insert a new market item into the live collection, stamping the UTC timestamp.
    """
    item['timestamp'] = datetime.now(timezone.utc)
    get_collection(ColEnum.MARKET).insert_one(item)


def get_trade_market_item(item_name: str) -> List[Dict[str, Any]]:
    """
    Retrieve all market entries for an item by name.
    """
    cursor = get_collection(ColEnum.MARKET).find(
        {'name': item_name},
        projection={'_id': 0}
    )
    return list(cursor)


def get_trade_market_item_price(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None
) -> Dict[str, Any]:
    """
    Compute price statistics (min, max, avg, mid-80%) for identified and unidentified listings,
    taking each 'amount' into account (so a listing of amount=4 counts as four data points).
    """
    shiny_stat = '$ne' if shiny else '$eq'
    match_filter: Dict[str, Any] = {
        'name': item_name,
        'shiny_stat': {shiny_stat: None}
    }
    if tier is not None:
        match_filter['$or'] = [
            {'item_type': {'$in': ['GearItem', 'IngredientItem']}},
            {'item_type': 'MaterialItem', 'tier': tier}
        ]

    pipeline = [
        {'$match': match_filter},

        # explode each doc into 'amount' copies
        {'$addFields': {
            'unitIndex': {'$range': [0, '$amount']}
        }},
        {'$unwind': '$unitIndex'},

        {'$sort': {'listing_price': 1}},
        {'$facet': {
            'identified_prices': [
                {'$match': {'$or': [{'unidentified': False}, {'unidentified': None}]}},
                {'$group': {
                    '_id': None,
                    'minPrice': {'$min': '$listing_price'},
                    'maxPrice': {'$max': '$listing_price'},
                    'avgPrice': {'$avg': '$listing_price'},
                    'prices': {'$push': '$listing_price'}
                }},
                {'$project': {
                    '_id': 0,
                    'minPrice': {'$round': ['$minPrice', 2]},
                    'maxPrice': {'$round': ['$maxPrice', 2]},
                    'avgPrice': {'$round': ['$avgPrice', 2]},
                    'mid_80_percent': {
                        '$cond': [
                            {'$gte': [{'$size': '$prices'}, 2]},
                            {'$slice': [
                                '$prices',
                                {'$ceil': {'$multiply': [{'$size': '$prices'}, 0.1]}},
                                {'$floor': {'$multiply': [{'$size': '$prices'}, 0.8]}}
                            ]},
                            '$prices'
                        ]
                    }
                }},
                {'$project': {
                    'minPrice': 1,
                    'maxPrice': 1,
                    'avgPrice': 1,
                    'average_mid_80_percent_price': {'$round': [{'$avg': '$mid_80_percent'}, 2]}
                }}
            ],
            'unidentified_avg_price': [
                {'$match': {'unidentified': True}},
                {'$group': {
                    '_id': None,
                    'avgUnidentifiedPrice': {'$avg': '$listing_price'},
                    'prices': {'$push': '$listing_price'}
                }},
                {'$project': {
                    '_id': 0,
                    'avgUnidentifiedPrice': {'$round': ['$avgUnidentifiedPrice', 2]},
                    'mid_80_percent': {
                        '$cond': [
                            {'$gte': [{'$size': '$prices'}, 2]},
                            {'$slice': [
                                '$prices',
                                {'$ceil': {'$multiply': [{'$size': '$prices'}, 0.1]}},
                                {'$floor': {'$multiply': [{'$size': '$prices'}, 0.8]}}
                            ]},
                            '$prices'
                        ]
                    }
                }},
                {'$project': {
                    'avgUnidentifiedPrice': 1,
                    'average_mid_80_percent_price': {'$round': [{'$avg': '$mid_80_percent'}, 2]}
                }}
            ]
        }},
        {'$project': {
            'lowest_price': {'$arrayElemAt': ['$identified_prices.minPrice', 0]},
            'highest_price': {'$arrayElemAt': ['$identified_prices.maxPrice', 0]},
            'average_price': {'$arrayElemAt': ['$identified_prices.avgPrice', 0]},
            'average_mid_80_percent_price': {
                '$arrayElemAt': ['$identified_prices.average_mid_80_percent_price', 0]},
            'unidentified_average_price': {'$arrayElemAt': ['$unidentified_avg_price.avgUnidentifiedPrice', 0]},
            'unidentified_average_mid_80_percent_price':
                {'$arrayElemAt': ['$unidentified_avg_price.average_mid_80_percent_price', 0]}
        }}
    ]

    result = list(get_collection(ColEnum.MARKET).aggregate(pipeline))
    return result[0] if result else {}


def get_price_history(
        item_name: str,
        shiny: bool = False,
        days: int = 14,
        tier: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the price history of an item over the past `days` days.
    """
    shiny_stat = '$ne' if shiny else '$eq'
    query_filter: Dict[str, Any] = {
        'name': item_name,
        'shiny_stat': {shiny_stat: None}
    }
    if tier is not None:
        query_filter['$or'] = [
            {'item_type': {'$in': ['GearItem', 'IngredientItem']}},
            {'item_type': 'MaterialItem', 'tier': tier}
        ]
    start_date = datetime.now(timezone.utc) - timedelta(days=days + 8)
    query_filter['date'] = {'$gte': start_date}

    cursor = get_collection(ColEnum.MARKET_ARCHIVE).find(
        filter=query_filter,
        sort=[('date', 1)],
        projection={'_id': 0}
    )
    return list(cursor)


def get_latest_price_history(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None,
        days: int = 7,
) -> Dict[str, Any]:
    """
    Aggregate the last N documents (default 7) to compute averages.
    """
    shiny_stat = '$ne' if shiny else '$eq'
    query_filter: Dict[str, Any] = {
        'name': item_name,
        'shiny_stat': {shiny_stat: None}
    }
    if tier is not None:
        query_filter['$or'] = [
            {'item_type': {'$in': ['GearItem', 'IngredientItem']}},
            {'item_type': 'MaterialItem', 'tier': tier}
        ]
    cursor = get_collection(ColEnum.MARKET_ARCHIVE).find(
        filter=query_filter,
        sort=[('date', -1)],
        projection={'_id': 0}
    ).limit(days)
    docs = list(cursor)
    stats: Dict[str, Any] = {}
    if docs:
        fields = [
            'lowest_price', 'highest_price', 'average_price',
            'total_count', 'average_mid_80_percent_price',
            'unidentified_average_price', 'unidentified_average_mid_80_percent_price',
            'unidentified_count'
        ]
        for f in fields:
            vals = [d.get(f) for d in docs if d.get(f) is not None]
            stats[f] = sum(vals) / len(vals) if vals else None
        stats['name'] = item_name
        stats['document_count'] = len(docs)
    return stats


def get_all_items_ranking() -> List[Dict[str, Any]]:
    """
    Generate a ranking of all items based on archived average price.
    """
    pipeline = [
        {'$group': {
            '_id': '$name',
            'lowest_price': {'$min': '$lowest_price'},
            'highest_price': {'$max': '$highest_price'},
            'average_price': {'$avg': '$average_price'},
            'average_total_count': {'$avg': '$total_count'},
            'average_unidentified_count': {'$avg': '$unidentified_count'},
            'average_mid_80_percent_price': {'$avg': '$average_mid_80_percent_price'},
            'unidentified_average_mid_80_percent_price': {'$avg': '$unidentified_average_mid_80_percent_price'}
        }},
        {'$match': {
            'average_mid_80_percent_price': {'$gte': 20480},
            'average_total_count': {'$gte': 2}
        }},
        {'$sort': {'average_price': -1}}
    ]
    cursor = get_collection(ColEnum.MARKET_ARCHIVE).aggregate(pipeline)
    return [
        dict(name=doc['_id'], **{k: doc[k] for k in doc if k != '_id'})
        for doc in cursor
    ]


def delete_all() -> int:
    """
    Delete every document in the live market collection.
    Returns the number of documents deleted.
    """
    result = get_collection(ColEnum.MARKET).delete_many({})
    return result.deleted_count
