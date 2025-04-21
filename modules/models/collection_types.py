from enum import Enum
from modules.repositories.market_repo import MarketRepository
from modules.repositories.lootpool_repo import LootpoolRepository
from modules.repositories.raidpool_repo import RaidpoolRepository
from modules.repositories.usage_repo import UsageRepository


class Collection(Enum):
    MARKET = ("trademarket", MarketRepository())
    LOOT = ("lootpool", LootpoolRepository())
    RAID = ("raidpool", RaidpoolRepository())
    MARKET_ARCHIVE = ("trademarket_archive", MarketRepository())
    API_KEYS = ("api_keys", UsageRepository())
    API_USAGE = ("api_usage", UsageRepository())

    def __init__(self, collection_name: str, repo):
        self.collection_name = collection_name
        self.repo = repo