#!/usr/bin/env python3
"""
Remove duplicate market-listing documents.

A document is considered a duplicate if another document has the same
(name, overall_roll, stat_rolls).  We keep one arbitrary instance of each
duplicate group and delete the others.
Usage:
    python cleanup_listing_duplicates.py
"""
import logging
import sys
import json
from typing import Dict, Tuple, Any, List

from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.repositories.market_repo import update_moving_averages_complete

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def cleanup_duplicates() -> None:
    """
    Scan the MARKET_LISTINGS collection and remove duplicates.
    """
    try:
        coll = get_collection(Collection.MARKET_LISTINGS)
    except Exception as exc:
        logging.error("Error connecting to MongoDB: %s", exc, exc_info=True)
        sys.exit(1)

    logging.info("Scanning MARKET_LISTINGS for duplicates...")

    # Fetch only the fields we need
    cursor = coll.find(
        {"item_type": "GearItem"},
        {"_id": 1, "name": 1, "overall_roll": 1, "stat_rolls": 1}
    )

    # key -> the one doc to keep
    seen: Dict[Tuple[str, float, str], dict] = {}
    to_delete: List[Any] = []

    for doc in cursor:
        name = doc.get("name")
        overall = doc.get("overall_roll")
        stat_rolls = doc.get("stat_rolls", [])

        # Canonicalize the stat_rolls list by sorting on apiName
        sorted_rolls = sorted(stat_rolls, key=lambda s: s.get("apiName"))
        # Serialize to a string for grouping
        stat_key = json.dumps(sorted_rolls, sort_keys=True)

        key = (name, overall, stat_key)
        if key not in seen:
            seen[key] = doc
        else:
            # Already saw one—mark this one for deletion
            to_delete.append(doc["_id"])

    cursor.close()

    if not to_delete:
        logging.info("No duplicates found. Nothing to delete.")
        return

    result = coll.delete_many({"_id": {"$in": to_delete}})
    logging.info("Deleted %d duplicate document(s)", result.deleted_count)


if __name__ == "__main__":
    cleanup_duplicates()

    logging.info(f"Updating moving averages")
    update_moving_averages_complete(force_update=True)
