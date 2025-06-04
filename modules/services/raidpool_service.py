import logging
from datetime import datetime
from typing import List, Optional, Any, Dict

from modules.config import Config
from modules.models.collection_request import CollectionRequest
from modules.models.collection_types import Collection
from modules.repositories.market_repo import get_trade_market_item_listings, get_price_history, get_historic_average, \
    get_all_items_ranking, get_trademarket_item_price
from modules.utils.queue_worker import enqueue
from modules.utils.time_validation import is_time_valid
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
        print(is_time_valid(Collection.GAMBIT, collection_time))
        if not collection_time or not is_time_valid(Collection.GAMBIT, collection_time):
            logging.warning(f"Item at index {idx} has invalid timestamp: {collection_time}; skipping")
            return

        valid_items.append(gambit)

    if valid_items:
        enqueue(CollectionRequest(type=Collection.GAMBIT, items=valid_items))
