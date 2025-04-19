from enum import Enum

class Collection(Enum):
    MARKET = "trademarket_items"
    LOOT = "lootpool_items"
    RAID = "raidpool_items"
    MARKET_ARCHIVE = "trademarket_items_archive"
    API_KEYS = "api_keys"