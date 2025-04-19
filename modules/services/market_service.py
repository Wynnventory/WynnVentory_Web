from typing import List, Optional, Any

from modules.config import Config
from modules.models.collection_types import Collection
from modules.repositories.market_repo import MarketRepository
from modules.utils.queue_worker import enqueue
from modules.utils.version import compare_versions


def _format_item_for_db(item: dict) -> dict:
    item_data = item.get('item', {})
    return {
        "name": item_data.get('name'),
        "rarity": item_data.get('rarity'),
        "item_type": item_data.get('item_type'),
        "type": item_data.get('type'),
        "tier": item_data.get('tier'),
        "unidentified": item_data.get('unidentified'),
        "shiny_stat": item_data.get('shinyStat'),
        "amount": item.get('amount'),
        "listing_price": item.get('listingPrice'),
        "player_name": item.get('playerName'),
        "mod_version": item.get('modVersion'),
        "hash_code": item.get('hash_code'),
    }


def save_items(raw_items):
    """
    raw_items: list of dicts coming from the Flask controller
    """
    if not raw_items:
        raise ValueError("No items provided")

    for item in raw_items:
        mod_version = item.get('modVersion')

        if not mod_version or not compare_versions(mod_version, Config.MIN_SUPPORTED_VERSION):
            raise ValueError(f"Item at index has unsupported mod version: {mod_version}")

        formatted = _format_item_for_db(item)
        enqueue(Collection.MARKET, formatted)


class MarketService:
    """
    Service layer for trade market operations: formatting, delegating to repository,
    and any additional business logic (e.g., enrichment).
    """

    def __init__(self):
        self.repo = MarketRepository()

    def get_item(self, item_name: str) -> list[dict[str, Any]]:
        """
        Retrieve market item info by name.
        """
        return self.repo.get_trade_market_item(item_name)

    def get_price(
            self,
            item_name: str,
            shiny: bool = False,
            tier: Optional[int] = None
    ) -> dict:
        """
        Retrieve price statistics for a market item.
        """
        return self.repo.get_trade_market_item_price(item_name, shiny, tier)

    def get_history(
            self,
            item_name: str,
            shiny: bool = False,
            days: int = 14,
            tier: Optional[int] = None
    ) -> List[dict]:
        """
        Retrieve historical price data for a market item over a specified window.
        """
        return self.repo.get_price_history(item_name, shiny, days, tier)

    def get_latest_history(
            self,
            item_name: str,
            shiny: bool = False,
            tier: Optional[int] = None
    ) -> dict:
        """
        Retrieve aggregated statistics from the most recent price history documents.
        """
        return self.repo.get_latest_price_history(item_name, shiny, tier)

    def get_ranking(self) -> List[dict]:
        """
        Retrieve a ranking of items based on archived price data.
        """
        return self.repo.get_all_items_ranking()
