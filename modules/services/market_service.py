import logging
from datetime import datetime
from typing import List, Optional, Any

from modules.config import Config
from modules.models.collection_request import CollectionRequest
from modules.models.collection_types import Collection
from modules.models.sort_options import SortOption
from modules.repositories.market_repo import get_trade_market_item_listings, get_price_history, get_historic_average, \
    get_all_items_ranking, get_trademarket_item_price
from modules.utils.queue_worker import enqueue
from modules.utils.version import compare_versions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

# Get module-specific logger
logger = logging.getLogger(__name__)


def _format_item_for_db(item: dict) -> dict:
    item_data = item.get('item', {})
    if not item_data:
        logger.warning(f"Item has no 'item' data: {item}")

    formatted_item = {
        "name": item_data.get('name'),
        "rarity": item_data.get('rarity'),
        "item_type": item_data.get('itemType'),
        "type": item_data.get('type'),
        "tier": item_data.get('tier'),
        "unidentified": item_data.get('unidentified'),
        "shiny_stat": item_data.get('shinyStat'),
        "overall_roll": item_data.get('overallRollPercentage'),
        "stat_rolls": item_data.get('actualStatsWithPercentage'),
        "reroll_count": item_data.get('rerollCount'),
        "amount": item.get('amount'),
        "listing_price": item.get('listingPrice'),
        "icon": item_data.get('icon'),
        "player_name": item.get('playerName'),
        "mod_version": item.get('modVersion'),
        "hash_code": item.get('hash_code'),
    }

    # Log any missing critical fields
    if not formatted_item["name"]:
        logger.warning(f"Item missing name: {item.get('hash_code', 'no_hash')}")
    if formatted_item["listing_price"] is None:
        logger.warning(f"Item missing listing price: {formatted_item['name'] or item.get('hash_code', 'no_hash')}")

    return formatted_item


def save_items(raw_items):
    """
    raw_items: list of dicts coming from the Flask controller
    """
    if not raw_items:
        logger.warning("No items provided to save_items")
        raise ValueError("No items provided")

    valid_items = []

    for index, item in enumerate(raw_items if isinstance(raw_items, list) else [raw_items]):
        mod_version = item.get('modVersion')
        if not mod_version or not compare_versions(mod_version, Config.MIN_SUPPORTED_VERSION):
            logger.warning(f"Item at index {index} has unsupported mod version: {mod_version}")
            continue

        try:
            formatted = _format_item_for_db(item)
            valid_items.append(formatted)
        except Exception as e:
            logger.error(f"Error formatting/enqueueing item {item}: {str(e)}", exc_info=True)
            raise

    if valid_items:
        enqueue(CollectionRequest(type=Collection.MARKET_LISTINGS, items=valid_items))
    else:
        logger.warning("No valid items found")


def get_historic_item_price(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None,
        start_date: datetime = None,
        end_date: datetime = None
) -> dict:
    """
    Retrieve aggregated statistics from the most recent price history documents.
    """
    return get_historic_average(item_name=item_name, shiny=shiny, tier=tier, start_date=start_date, end_date=end_date)


def get_history(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None,
        start_date: datetime = None,
        end_date: datetime = None
) -> List[dict]:
    """
    Retrieve historical price data for an item between start_date and end_date (inclusive).
    """
    return get_price_history(item_name, shiny, tier, start_date, end_date)


def get_price(
        item_name: str,
        shiny: bool = False,
        tier: Optional[int] = None
) -> dict:
    """
    Retrieve price statistics for a market item.
    """
    return get_trademarket_item_price(item_name=item_name, shiny=shiny, tier=tier)


def get_item_listings(
        item_name: Optional[str],
        shiny: Optional[bool] = None,
        unidentified: Optional[bool] = None,
        rarity: Optional[str] = None,
        tier: Optional[int] = None,
        item_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        sort_option: Optional[SortOption] = SortOption.TIMESTAMP_DESC,
        page: Optional[int] = 1,
        page_size: Optional[int] = 50
) -> dict[str, Any]:
    """
    Retrieve market item info by name.
    """
    return get_trade_market_item_listings(
        item_name=item_name,
        shiny=shiny,
        unidentified=unidentified,
        rarity=rarity,
        tier=tier,
        item_type=item_type,
        sub_type=sub_type,
        sort_option=sort_option,
        page=page,
        page_size=page_size)


def get_ranking(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
) -> List[dict]:
    """
    Retrieve a ranking of items based on archived price data.
    """
    return get_all_items_ranking(start_date=start_date, end_date=end_date)
