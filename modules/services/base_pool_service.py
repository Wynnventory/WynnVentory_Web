import logging
from typing import Any, Dict, List, Union

from modules.config import Config
from modules.models.collection_types import Collection
from modules.repositories import lootpool_repo, raidpool_repo
from modules.utils.queue_worker import enqueue
from modules.utils.time_validation import is_time_valid
from modules.utils.version import compare_versions


class BasePoolService:
    """
    A common service for handling lootpool/raidpool saving logic:
     - Version validation
     - Timestamp validation
     - Shiny count restriction
     - Enqueue for background processing
    """

    def __init__(
            self,
            collection_type: Collection,
    ) -> None:
        self.collection_type = collection_type
        self.supported_version = Config.MIN_SUPPORTED_VERSION

    def save(
            self,
            raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> None:
        """
        Accepts either a single item dict or a list of them,
        validates each, and enqueues for persistence.
        Raises ValueError on fatal errors.
        """
        items = raw_data if isinstance(raw_data, list) else [raw_data]
        if not items:
            raise ValueError("No items provided")

        for idx, item in enumerate(items):
            mod_version = item.get('modVersion')
            if not mod_version or not compare_versions(mod_version, self.supported_version):
                raise ValueError(f"Item at index {idx} has unsupported mod version: {mod_version}")

            collection_time = item.get('collectionTime')
            if not collection_time or not is_time_valid(self.collection_type, collection_time):
                logging.warning(f"Item at index {idx} has invalid collectionTime: {collection_time}; skipping")
                continue

            loot_items = item.get('items', [])
            shiny_count = sum(1 for entry in loot_items if entry.get('shiny'))
            if shiny_count > 1:
                logging.warning(
                    f"Lootpool contains too many shinies ({shiny_count}) at index {idx}; skipping"
                )
                continue

            # All checks passed -> enqueue for DB save
            enqueue(self.collection_type, item)

    def get_current_pools(self) -> List[Dict[str, Any]]:
        if self.collection_type == Collection.LOOT:
            return lootpool_repo.fetch_lootpool()
        elif self.collection_type == Collection.RAID:
            return raidpool_repo.fetch_raidpool()

        return []

    def get_current_pools_raw(self) -> List[dict]:
        if self.collection_type == Collection.LOOT:
            return lootpool_repo.fetch_lootpool_raw()
        elif self.collection_type == Collection.RAID:
            return raidpool_repo.fetch_raidpool_raw()

        return []
