#!/usr/bin/env python3
"""
Remove duplicate market-archive documents.

For every (name, tier, shiny) triple at 00:00 UTC on the given date the
collection should contain exactly **one** document – the one with the highest
`total_count`.  All others are deleted.

Usage:
    python cleanup_duplicates.py 2025-06-02
"""
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Tuple, List, Any

from modules.db import get_collection
from modules.models.collection_types import Collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# ──────────────────────────────────────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────────────────────────────────────


def cleanup_duplicates(target_date: datetime) -> None:
    """
    Delete duplicates whose `timestamp` exactly equals `target_date`
    (forced to 00:00:00 UTC).

    For each (name, tier, shiny) we keep the document with the highest
    `total_count`.
    """
    ts = target_date.replace(
        tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0
    )

    try:
        coll = get_collection(Collection.MARKET_ARCHIVE)
    except Exception as exc:  # pragma: no cover
        logging.error("Error connecting to MongoDB: %s", exc, exc_info=True)
        sys.exit(1)

    logging.info("Scanning duplicates for timestamp %s", ts.isoformat())

    cursor = coll.find(
        {"timestamp": ts},
        {"_id": 1, "name": 1, "tier": 1, "shiny": 1, "total_count": 1},
    )

    best_docs: Dict[Tuple[str, Any, bool], dict] = {}
    to_delete: List = []

    for doc in cursor:
        key = (doc["name"], doc.get("tier"), doc["shiny"])
        prev = best_docs.get(key)

        if prev is None or doc["total_count"] > prev["total_count"]:
            if prev is not None:
                to_delete.append(prev["_id"])
            best_docs[key] = doc
        else:
            to_delete.append(doc["_id"])

    cursor.close()

    if to_delete:
        result = coll.delete_many({"_id": {"$in": to_delete}})
        logging.info("Removed %d duplicate document(s)", result.deleted_count)
    else:
        logging.info("No duplicates found – nothing to delete.")


if __name__ == "__main__":
    target_date = datetime(2025, 5, 25, tzinfo=timezone.utc)
    cleanup_duplicates(target_date)
