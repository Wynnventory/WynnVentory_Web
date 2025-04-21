from modules.models.collection_types import Collection
from modules.services.base_pool_service import BasePoolService


class RaidpoolService(BasePoolService):
    def __init__(self):
        super().__init__(collection_type=Collection.RAID)
