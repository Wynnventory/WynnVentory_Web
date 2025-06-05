from enum import Enum

class Collection(Enum):
    MARKET_LISTINGS = "trademarket_listings"
    MARKET_AVERAGES = "trademarket_averages"
    MARKET_ARCHIVE = "trademarket_archive"
    LOOT = "lootpool"
    RAID = "raidpool"
    GAMBIT = "gambit"
    API_KEYS = "api_keys"
    API_USAGE = "api_usage"