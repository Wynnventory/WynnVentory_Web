from pymongo import UpdateOne

from modules.db import get_collection
from modules.models.collection_types import Collection

COLLECTION = get_collection(Collection.MARKET_LISTINGS)


def int32(x):
    """Force a value into a 32-bit signed integer (simulate Java int arithmetic)."""
    x = x & 0xFFFFFFFF
    if x & 0x80000000:
        return -((~x & 0xFFFFFFFF) + 1)
    return x


def java_hash(obj):
    """
    Recursively compute a hash code mimicking Java's Objects.hash() behavior.
    Supports None, int, bool, str, list, and dict.
    """
    if obj is None:
        return 0
    if isinstance(obj, int):
        return int32(obj)
    if isinstance(obj, bool):
        # Java Boolean.hashCode(): true -> 1231, false -> 1237.
        return 1231 if obj else 1237
    if isinstance(obj, str):
        h = 0
        for ch in obj:
            h = int32(31 * h + ord(ch))
        return h
    if isinstance(obj, list):
        result = 1
        for elem in obj:
            result = int32(31 * result + java_hash(elem))
        return result
    if isinstance(obj, dict):
        # Special handling if this dict appears to be an ActualStatWithPercentage
        if "stat_name" in obj and "actual_roll_percentage" in obj:
            return java_hash([obj["stat_name"], obj["actual_roll_percentage"]])
        # Otherwise, process the dict keys in sorted order.
        result = 1
        for key in sorted(obj.keys()):
            result = int32(31 * result + java_hash(key))
            result = int32(31 * result + java_hash(obj[key]))
        return result
    # Fallback: convert the object to a string and hash that.
    return java_hash(str(obj))


def compute_hash(doc):
    """
    Compute the hash code using this ordered list of fields:
    name, rarity, unidentified, shiny_stat, amount, listing_price, actual_stats_with_percentage.
    """
    name = doc.get("name")
    rarity = doc.get("rarity")
    item_type = doc.get("item_type")
    type_field = doc.get("type")
    tier = doc.get("tier")
    unidentified = doc.get("unidentified")
    shiny_stat = doc.get("shiny_stat")
    amount = doc.get("amount")
    listing_price = doc.get("listing_price")
    actual_stats = doc.get("actual_stats_with_percentage")
    rerolls = doc.get("rerolls")

    values = [name, rarity, item_type, type_field, tier, unidentified, shiny_stat, amount, listing_price, actual_stats,
              rerolls]
    return java_hash(values)


def update_hash_codes_and_migrate():
    projection = {
        "name": 1,
        "rarity": 1,
        "item_type": 1,
        "type": 1,
        "tier": 1,
        "unidentified": 1,
        "shiny_stat": 1,
        "amount": 1,
        "listing_price": 1,
        "actual_stats_with_percentage": 1,
        "rerolls": 1,
    }

    BATCH_SIZE = 1000
    updates = []
    count = 0

    cursor = COLLECTION.find({}, projection)
    for doc in cursor:
        # 1) compute the new hash
        hash_code = compute_hash(doc)

        # 2) build a single update spec that:
        #    - sets hash_code + new schema fields
        #    - unsets the old schema fields
        update_spec = {
            "$set": {
                "hash_code": hash_code,
                "item_type": "GearItem",
                "type": None,
                "tier": None,
            },
            "$unset": {
                "level": "",
                "powder_slots": "",
                "rerolls": "",
                "overall_percentage": "",
                "actual_stats_with_percentage": "",
            }
        }

        updates.append(
            UpdateOne({"_id": doc["_id"]}, update_spec)
        )

        count += 1
        if len(updates) >= BATCH_SIZE:
            COLLECTION.bulk_write(updates, ordered=False)
            updates = []
            print(f"Processed & migrated {count} documents...")

    if updates:
        COLLECTION.bulk_write(updates, ordered=False)
        print(f"Processed & migrated {count} documents in total.")


def remove_duplicates():
    """
    Check for duplicate documents (those with the same hash_code) and
    remove duplicates, keeping one document per unique hash_code.
    """
    # Aggregation pipeline to group by hash_code and collect document IDs.
    pipeline = [
        {"$group": {"_id": "$hash_code", "ids": {"$addToSet": "$_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]

    duplicate_groups = list(COLLECTION.aggregate(pipeline))
    total_removed = 0
    for group in duplicate_groups:
        ids = group["ids"]
        # Keep the first document and remove the rest.
        ids_to_remove = ids[1:]
        if ids_to_remove:
            result = COLLECTION.delete_many({"_id": {"$in": ids_to_remove}})
            total_removed += result.deleted_count
            print(f"Removed {result.deleted_count} duplicate documents for hash_code {group['_id']}")
    print(f"Total duplicate documents removed: {total_removed}")


def main():
    print("Updating hash codes...")
    update_hash_codes_and_migrate()
    print("Removing duplicate documents...")
    remove_duplicates()


if __name__ == '__main__':
    main()
