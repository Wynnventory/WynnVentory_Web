"""
Server-side hash computation that mirrors Java's TrademarketListing.hashCode().

This replicates the mod's hash chain to ensure deterministic hash_code values
regardless of client JVM or mod version:

    TrademarketListing.hashCode() = Objects.hash(item, price, quantity)
      SimpleItem.hashCode()       = Objects.hash(name, rarityName, itemTypeName, type, amount)
      SimpleGearItem.hashCode()   = Objects.hash(super, unidentified, rerollCount, shinyStr, sortedStats)
      SimpleTierItem.hashCode()   = Objects.hash(super, tier)
      ItemStat.hashCode()         = Objects.hash(apiName, statRoll)
"""


def int32(x):
    """Force a value into a 32-bit signed integer (simulate Java int overflow)."""
    x = x & 0xFFFFFFFF
    if x & 0x80000000:
        return -((~x & 0xFFFFFFFF) + 1)
    return x


def java_hash(obj):
    """
    Recursively compute a hash code mimicking Java's Objects.hash() / hashCode() behavior.
    Supports None, bool, int, str, and list.
    """
    if obj is None:
        return 0
    # bool check MUST come before int (Python bool is a subclass of int)
    if isinstance(obj, bool):
        return 1231 if obj else 1237
    if isinstance(obj, int):
        return int32(obj)
    if isinstance(obj, str):
        h = 0
        for ch in obj:
            h = int32(31 * h + ord(ch))
        return h
    if isinstance(obj, list):
        # Mirrors Java's Arrays.hashCode(Object[]) / List.hashCode()
        result = 1
        for elem in obj:
            result = int32(31 * result + java_hash(elem))
        return result
    return java_hash(str(obj))


def _format_shiny_stat(shiny_stat):
    """Convert shiny_stat to the string format used in Java's hashCode: 'key:value' or None."""
    if shiny_stat is None:
        return None
    if isinstance(shiny_stat, str):
        return shiny_stat
    if isinstance(shiny_stat, dict):
        stat_type = shiny_stat.get("statType", {})
        key = stat_type.get("key", "") if isinstance(stat_type, dict) else str(stat_type)
        value = shiny_stat.get("value", "")
        return f"{key}:{value}"
    return None


def _compute_sorted_stats_list_hash(stats):
    """Compute Java's List.hashCode() for ItemStat list sorted by apiName."""
    if not stats:
        return 1  # Java empty List.hashCode()

    sorted_stats = sorted(stats, key=lambda s: s.get("apiName", ""))
    result = 1
    for stat in sorted_stats:
        # Mirrors ItemStat.hashCode() = Objects.hash(statType.getKey(), value)
        stat_hash = java_hash([stat.get("apiName"), stat.get("statRoll")])
        result = int32(31 * result + stat_hash)
    return result


def _compute_simple_item_hash(name, rarity, item_type, type_field, amount):
    """Mirrors SimpleItem.hashCode() = Objects.hash(rarityName, itemTypeName, ...)."""
    return java_hash([name, rarity, item_type, type_field, amount])


def _compute_gear_item_hash(base_hash, item_data):
    """Mirrors SimpleGearItem.hashCode()."""
    unidentified = item_data.get("unidentified", False)
    reroll_count = item_data.get("rerollCount", 0)
    shiny_str = _format_shiny_stat(item_data.get("shinyStat"))
    stats_list_hash = _compute_sorted_stats_list_hash(
        item_data.get("actualStatsWithPercentage") or []
    )
    return java_hash([base_hash, unidentified, reroll_count, shiny_str, stats_list_hash])


def compute_listing_hash(raw_item: dict) -> int:
    """
    Compute hash matching Java's TrademarketListing.hashCode() from the raw request JSON.

    raw_item is the JSON dict as sent by the mod, e.g.:
    {
      "item": { "name": ..., "rarity": ..., "itemType": ..., ... },
      "listingPrice": 1000,
      "amount": 1,
      "hash_code": ...,
      ...
    }
    """
    item_data = raw_item.get("item", {})
    listing_price = raw_item.get("listingPrice")
    listing_quantity = raw_item.get("amount")

    # SimpleItem base hash
    name = item_data.get("name")
    rarity = item_data.get("rarity")
    item_type = item_data.get("itemType")
    type_field = item_data.get("type")
    item_amount = item_data.get("amount", 1)

    base_hash = _compute_simple_item_hash(name, rarity, item_type, type_field, item_amount)

    # Subclass-specific hash
    if item_type == "GearItem":
        item_hash = _compute_gear_item_hash(base_hash, item_data)
    else:
        tier = item_data.get("tier")
        if tier is not None:
            item_hash = java_hash([base_hash, tier])
        else:
            item_hash = base_hash

    return java_hash([item_hash, listing_price, listing_quantity])
