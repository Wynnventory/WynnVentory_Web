from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict, Optional

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.utils.time_validation import get_lootpool_week, get_lootpool_week_for_timestamp, get_raidpool_week


def build_pool_pipeline(year: Optional[int] = None, week: Optional[int] = None) -> List[Dict]:
    pipeline: List[Dict] = []

    # 1) optionally match this week/year
    if year is not None and week is not None:
        pipeline.append({"$match": {"year": year, "week": week}})
    elif (year is None) ^ (week is None):
        raise ValueError("Both year and week must be provided, or neither.")

    # 2) unwind the items array
    pipeline.append({"$unwind": "$items"})

    # 3) copy type → subtype
    pipeline.append({
        "$set": {"items.subtype": "$items.type"}
    })

    # 4) group by region only, collecting all items in one list
    pipeline.append({
        "$group": {
            "_id": {
                "year": "$year",
                "week": "$week",
                "region": "$region",
                "timestamp": "$timestamp"
            },
            "items": {"$push": {
                "name": "$items.name",
                "amount": "$items.amount",
                "rarity": "$items.rarity",
                "shiny": "$items.shiny",
                "shinyStat": "$items.shinyStat",
                "itemType": "$items.itemType",
                "subtype": "$items.subtype"
            }}
        }
    })

    # 5) project region-level docs
    pipeline.append({
        "$project": {
            "year": "$_id.year",
            "week": "$_id.week",
            "region": "$_id.region",
            "timestamp": "$_id.timestamp",
            "items": 1
        }
    })

    # 6) gather all regions under each year/week into "regions" list
    pipeline.append({
        "$group": {
            "_id": {"year": "$year", "week": "$week"},
            "regions": {"$push": {
                "region": "$region",
                "timestamp": "$timestamp",
                "items": "$items"
            }}
        }
    })

    # 7) replace root with { year, week, regions }
    pipeline.append({
        "$replaceWith": {
            "year": "$_id.year",
            "week": "$_id.week",
            "regions": "$regions"
        }
    })

    return pipeline


class BasePoolRepo:
    """
    Base repository class for lootpool and raidpool operations.
    Provides common functionality for saving and retrieving pool data.
    """

    def __init__(self, collection_type: Collection):
        self.collection_type = collection_type

    def save(self, pools: List[Dict]) -> None:
        """
        Insert or update pool documents for each dict in the given list,
        applying duplicate checks and timestamp logic.
        """
        collection = get_collection(self.collection_type)

        for pool in pools:
            # Compute week/year from the payload's collectionTime
            year, week = get_lootpool_week_for_timestamp(pool.get('collectionTime'))
            pool['week'] = week
            pool['year'] = year
            pool['timestamp'] = datetime.now(timezone.utc)

            # Build a filter for existing documents in same region/week/year
            region = pool.get('region')
            filter_q = {'region': region, 'week': week, 'year': year}
            existing = collection.find_one(filter_q)

            if existing:
                # Apply replacement rules
                existing_ts = existing['timestamp']
                if existing_ts.tzinfo is None:
                    existing_ts = existing_ts.replace(tzinfo=timezone.utc)

                age = datetime.now(timezone.utc) - existing_ts
                new_items = pool.get('items', [])
                old_items = existing.get('items', [])

                has_more = len(new_items) > len(old_items)
                has_enough_and_stale = age > timedelta(hours=1) and len(new_items) >= len(old_items)
                is_older_week = (existing['year'], existing['week']) < (year, week)

                if has_more or has_enough_and_stale or is_older_week:
                    # Replace the old document
                    collection.delete_one(filter_q)
                    collection.insert_one(pool)
                else:
                    # Skip insertion
                    continue
            else:
                # No duplicate, insert fresh
                collection.insert_one(pool)

    def fetch_pool_raw(self) -> List[dict]:
        """
        Retrieve the raw pool documents for the current week/year.
        """
        year, week = self._get_week_year()
        cursor = get_collection(self.collection_type).find(
            {'year': year, 'week': week},
            projection={'_id': 0}
        )
        return list(cursor)

    def _get_week_year(self) -> Tuple[int, int]:
        """
        Get the appropriate week and year based on collection type.
        """
        if self.collection_type == Collection.RAID:
            return get_raidpool_week()
        else:
            return get_lootpool_week()

