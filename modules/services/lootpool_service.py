from modules.models.collection_types import Collection
from modules.repositories.lootpool_repo import LootpoolRepository
from modules.services.base_pool_service import BasePoolService


class LootpoolService(BasePoolService):
    def __init__(self):
        super().__init__(repo=LootpoolRepository(),
                         collection_type=Collection.LOOT)