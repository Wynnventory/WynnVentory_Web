import logging
from typing import List, Dict

from modules.config import Config
from modules.models.collection_request import CollectionRequest
from modules.models.collection_types import Collection
from modules.repositories import raidpool_repo
from modules.utils.queue_worker import enqueue
from modules.utils.time_validation import is_time_valid, get_current_gambit_day
from modules.utils.version import compare_versions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

# Get module-specific logger
logger = logging.getLogger(__name__)


def save_gambits(gambits: List[Dict]):
    if not gambits:
        raise ValueError("No gambits provided")

    valid_items = []

    for idx, gambit in enumerate(gambits):
        mod_version = gambit.get("modVersion")
        if not mod_version or not compare_versions(mod_version, Config.MIN_SUPPORTED_VERSION):
            logging.warning(f"Gambit at index {idx} has unsupported mod version: {mod_version}")
            continue

        collection_time = gambit.get("timestamp")
        if not collection_time or not is_time_valid(Collection.GAMBIT, collection_time):
            logging.warning(f"Item at index {idx} has invalid timestamp: {collection_time}; skipping")
            return

        valid_items.append(gambit)

    if valid_items:
        enqueue(CollectionRequest(type=Collection.GAMBIT, items=valid_items))


def get_current_gambits() -> dict:
    _, next_reset = get_current_gambit_day()

    return get_specific_gambits(year=next_reset.year, month=next_reset.month, day=next_reset.day)


def get_specific_gambits(year: int, month: int, day: int) -> dict:
    return raidpool_repo.fetch_gambits(year, month, day)
