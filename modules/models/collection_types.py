from enum import Enum

class Collection(Enum):
    MARKET = "trademarket"
    LOOT = "lootpool"
    RAID = "raidpool"
    MARKET_ARCHIVE = "trademarket_archive"
    API_KEYS = "api_keys"
    API_USAGE = "api_usage"