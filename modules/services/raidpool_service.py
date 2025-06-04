import logging
from datetime import datetime
from typing import List, Optional, Any

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


def save_gambits(gambit_day: dict):
    mod_version = gambit_day.get("modVersion")
    if not mod_version or not compare_versions(mod_version, Config.MIN_SUPPORTED_VERSION):
        logger.warning(f"Gambits were not saved due to an unsupported mod version: {mod_version}")
        return

    collection_time = gambit_day.get("collectionTime")
    print(is_time_valid(Collection.GAMBIT, collection_time))
    if not collection_time or not is_time_valid(Collection.GAMBIT, collection_time):
        logging.warning(f"Gambits have invalid collectionTime: {collection_time}")
        return

    enqueue(CollectionRequest(type=Collection.GAMBIT, items=[gambit_day]))