#!/usr/bin/env python3
"""
migrate_archives.py

Adds the following fields to every document in the 'archive' collection:
  - shiny_stat: None
  - tier: None
  - item_type: "GearItem"
"""

from pymongo import MongoClient
import sys

from modules.db import get_collection
from modules.models.collection_types import Collection


# Connection details

def main():
    try:
        collection = get_collection(Collection.MARKET_ARCHIVE)
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    # Build the update: set the new fields
    update_spec = {
        "$set": {
            "shiny_stat": None,
            "tier": None,
            "item_type": "GearItem"
        }
    }

    # Optionally only update docs where item_type doesn't yet exist:
    # filter_query = {"item_type": {"$exists": False}}
    # result = collection.update_many(filter_query, update_spec)

    # Unconditionally update all documents:
    result = collection.update_many({}, update_spec)

    print(f"Matched {result.matched_count} documents.")
    print(f"Modified {result.modified_count} documents.")


if __name__ == "__main__":
    main()
