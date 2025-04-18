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

# Connection details
MONGO_URI = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"
DB_NAME = "wynnventory"
COLLECTION_NAME = "tm_items_ARCH_DEV"  # change if your archive collection is named differently

def main():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
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
