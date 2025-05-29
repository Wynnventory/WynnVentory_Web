from datetime import datetime, timezone

from flask import Blueprint, render_template, jsonify, request

from modules.models.collection_types import Collection
from modules.services import base_pool_service, market_service

web_bp = Blueprint(
    'web', __name__,
    template_folder='templates/',
    static_folder='static',
    static_url_path='/modules/routes/web/static'
)


@web_bp.route("/")
@web_bp.route("/index")
def index():
    return lootrun_lootpool()

@web_bp.route("/items")
def items():
    return render_template("items.html")

@web_bp.route("/lootrun")
def lootrun_lootpool():
    data = jsonify(base_pool_service.get_current_pools(Collection.LOOT)).get_json()
    pools = data if isinstance(data, list) else []
    pools = enrich_pools(pools, items_key="region_items")
    return render_template("lootpool/lootrun_lootpool.html", loot_data=pools)

@web_bp.route("/raid")
def raid_lootpool():
    data = jsonify(base_pool_service.get_current_pools(Collection.RAID)).get_json()
    pools = data if isinstance(data, list) else []
    pools = enrich_pools(pools, items_key="group_items")
    return render_template("lootpool/raid_lootpool.html", loot_data=pools)

@web_bp.route("/history/", defaults={'item_name': None})
@web_bp.route("/history/<item_name>")
@web_bp.route("/history/<item_name>/")
def history(item_name):
    return render_template("market/price_history.html", item_name=item_name)

@web_bp.route("/ranking")
def ranking():
    return render_template("market/price_ranking.html")


@web_bp.route('/listings', defaults={'item_name': None})
@web_bp.route('/listings/<item_name>')
def trademarket_listings(item_name):
    # keep same defaults & limits as your API
    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(1000, request.args.get('page_size', 50, type=int))

    # call your service layer (the same logic behind the API endpoint)
    result = market_service.get_item_listings(
        item_name=item_name,
        page=page,
        page_size=page_size,
    )
    # result is the dict: { count, items, page, page_size, total }
    result_items = enrich_listings(result.get('items', []))
    total = result.get('total', 0)

    return render_template(
        'market/listings.html',  # or 'trademarket/listings.html'
        items=result_items,
        item_name=item_name,
        page=page,
        page_size=page_size,
        total=total
    )


def format_last_updated(timestamp_str: str, now: datetime) -> str:
    ts = datetime.strptime(timestamp_str, '%a, %d %b %Y %H:%M:%S %Z') \
             .replace(tzinfo=timezone.utc)
    minutes = (now - ts).total_seconds() // 60
    if minutes < 60:
        return f"Last updated {int(minutes)} minutes ago"
    hours = minutes // 60
    return f"Last updated {int(hours)} hour{'s' if hours > 1 else ''} ago"

def build_icon_url(icon: dict) -> str | None:
    """
    icon is expected as {'format': 'armour'|'skins'|..., 'value': '<icon-name>'}
    Returns the correct CDN URL or None.
    """
    if not icon:
        return None

    fmt = icon.get("format")
    val = icon.get("value")
    if not (fmt and val):
        return None

    if fmt in ("armour", "legacy", "attribute"):
        return f"https://cdn.wynncraft.com/nextgen/itemguide/3.3/{val}.webp"
    if fmt == "skins":
        return f"https://mc-heads.net/head/{val}"
    if fmt == "aspect_attribute":
        return f"https://cdn.wynncraft.com/nextgen/abilities/2.1/aspects/{val}.png"

    return None

def enrich_listings(listings: list[dict]) -> list[dict]:
    for item in listings:
        item["icon_url"] = build_icon_url(item.get("icon"))

    return listings


def enrich_pools(raw_pools: list[dict], items_key: str) -> list[dict]:
    """
    Adds 'last_updated' and 'icon_url' to every item in each pool.
    items_key is 'region_items' for lootrun, 'group_items' for raid.
    """
    now = datetime.now(timezone.utc)
    for pool in raw_pools:
        pool["last_updated"] = format_last_updated(pool["timestamp"], now)
        for group in pool.get(items_key, []):
            for item in group.get("loot_items", []):
                item["icon_url"] = build_icon_url(item.get("icon"))
    return raw_pools