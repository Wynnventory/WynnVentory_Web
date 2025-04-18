from modules.models.collection_types import Collection
from modules.repositories.raidpool_repo import RaidpoolRepository
from modules.services.base_pool_service import BasePoolService


class RaidpoolService(BasePoolService):
    def __init__(self):
        super().__init__(repo=RaidpoolRepository(),
                            collection_type=Collection.RAID)