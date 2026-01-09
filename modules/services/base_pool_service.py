import logging
from typing import Any, Dict, List, Union, Optional

from modules.config import Config
from modules.models.collection_request import CollectionRequest
from modules.models.collection_types import Collection
from modules.repositories import lootpool_repo, raidpool_repo
from modules.utils.queue_worker import enqueue
from modules.utils.time_validation import is_time_valid
from modules.utils.version import compare_versions


def save(collection_type: Collection, raw_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
    """
    Accepts either a single item dict or a list of them,
    validates each, and enqueues for persistence.
    Raises ValueError on fatal errors.
    """
    regions = raw_data if isinstance(raw_data, list) else [raw_data]
    if not regions:
        raise ValueError("No regions provided")

    valid_regions = []

    for idx, region in enumerate(regions):
        mod_version = region.get('modVersion')
        if not mod_version or not compare_versions(mod_version, Config.MIN_SUPPORTED_VERSION):
            raise ValueError(f"Region at index {idx} has unsupported mod version: {mod_version}")

        loot_items = region.get('items', [])
        shiny_count = sum(1 for entry in loot_items if entry.get('shiny'))
        if shiny_count > 1:
            logging.warning(f"Lootpool contains too many shinies ({shiny_count}) at index {idx}; skipping")
            continue

        # New AspectItem Mythic check
        mythic_aspect_count = sum(1 for entry in loot_items if entry.get('itemType') == 'AspectItem' and entry.get('rarity') == 'Mythic')
        if mythic_aspect_count > 3:
            logging.warning(f"Lootpool contains too many Mythic AspectItems ({mythic_aspect_count}) at index {idx}; skipping")
            continue

        valid_loot_items = []

        for idx, item in enumerate(loot_items):
            collection_time = item.get('timestamp')
            if not collection_time or not is_time_valid(collection_type, collection_time):
                logging.warning(f"Item at index {idx} has invalid timestamp: {collection_time}; skipping")
                continue

            item.pop("playerName", None)
            item.pop("modVersion", None)
            item.pop("timestamp", None)

            valid_loot_items.append(item)

        if not valid_loot_items:
            logging.warning(f"No valid items found in region {region.get('name', 'no_name')}; skipping")
            continue

        region['items'] = valid_loot_items
        valid_regions.append(region)

    # Enqueue all valid items at once
    if valid_regions:
        enqueue(CollectionRequest(type=collection_type, items=valid_regions))


def get_current_pools(collection_type: Collection) -> List[Dict[str, Any]]:
    if collection_type == Collection.LOOT:
        return lootpool_repo.fetch_lootpool()
    elif collection_type == Collection.RAID:
        return raidpool_repo.fetch_raidpool()

    return []


def get_pools(
        collection_type: Collection,
        page: Optional[int] = 1,
        page_size: Optional[int] = 50,
        skip: Optional[int] = 0
) -> dict[str, Any] | list[dict[str, Any]]:
    if collection_type == Collection.LOOT:
        return lootpool_repo.fetch_lootpools(page=page, page_size=page_size, skip=skip)
    elif collection_type == Collection.RAID:
        return raidpool_repo.fetch_raidpools(page=page, page_size=page_size, skip=skip)

    return []


def get_specific_pool(collection_type: Collection, year: int, week: int) -> Dict:
    if collection_type == Collection.LOOT:
        return lootpool_repo.fetch_lootpools(year, week)
    elif collection_type == Collection.RAID:
        return raidpool_repo.fetch_raidpools(year, week)

    return {}
