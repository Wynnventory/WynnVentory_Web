from datetime import datetime, timezone

from flask import Blueprint, render_template, jsonify, request

from modules.models.collection_types import Collection
from modules.models.sort_options import SortOption
from modules.repositories.market_repo import TIERED_TYPES
from modules.services import base_pool_service, market_service, raidpool_service

SUBTYPE_OPTIONS = {
    "GearItem": [
        ("BOW", "Bow"),
        ("DAGGER", "Dagger"),
        ("WAND", "Wand"),
        ("SPEAR", "Spear"),
        ("RELIK", "Relik"),
        ("HELMET", "Helmet"),
        ("CHESTPLATE", "Chestplate"),
        ("LEGGINGS", "Leggings"),
        ("BOOTS", "Boots"),
        ("NECKLACE", "Necklace"),
        ("RING", "Ring"),
        ("BRACELET", "Bracelet"),
    ],
    "PowderItem": [
        ("WaterPowder", "Water"),
        ("FirePowder", "Fire"),
        ("ThunderPowder", "Thunder"),
        ("AirPowder", "Air"),
        ("EarthPowder", "Earth")
    ],
    "RuneItem": [
        ("UthRune", "Uth"),
        ("AzRune", "Az"),
        ("NiiRune", "Nii"),
        ("TolRune", "Tol")
    ]
}

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
    raid_data = jsonify(base_pool_service.get_current_pools(Collection.RAID)).get_json()
    pools = raid_data if isinstance(raid_data, list) else []
    pools = enrich_pools(pools, items_key="group_items")

    gambit_data = raidpool_service.get_current_gambits()
    gambits = gambit_data.get("gambits") or []

    return render_template("lootpool/raid_lootpool.html", loot_data=pools, gambit_data=gambits)


@web_bp.route("/history/", defaults={'item_name': None})
@web_bp.route("/history/<item_name>")
@web_bp.route("/history/<item_name>/")
def history(item_name):
    return render_template("market/price_history.html", item_name=item_name)


@web_bp.route("/ranking")
def ranking():
    return render_template("market/price_ranking.html")


@web_bp.route("/emerald_calculator")
def emerald_calculator():
    return render_template("emerald_calculator.html")


@web_bp.route('/listings', defaults={'item_name': None})
@web_bp.route('/listings/<item_name>')
def trademarket_listings(item_name):
    # 1) Pagination params
    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(50, request.args.get('page_size', 25, type=int))

    # 2) Read the "search" field — but only use it if non‐empty
    raw_search = request.args.get('search', type=str)
    if raw_search:
        query_name = raw_search.strip()
    else:
        query_name = item_name  # could be None, or a URL param

    rarity = request.args.get('rarity', type=str)
    if rarity == "":
        rarity = None

    filter_type = request.args.get('itemType', type=str)
    if filter_type == "":
        filter_type = None

    filter_sub_type = request.args.get('subType', type=str)
    if filter_sub_type == "":
        filter_sub_type = None

    sort_str = request.args.get("sort", SortOption.TIMESTAMP_DESC.value)
    try:
        sort = SortOption(sort_str)
    except ValueError:
        sort = SortOption.TIMESTAMP_DESC

    # Define a simple mapping from lowercase strings to booleans:
    _bool_map = {"true": True, "false": False}

    # SHINY:
    raw_shiny = request.args.get("shiny", "").lower()
    shiny = _bool_map.get(raw_shiny)  # → True if "true", False if "false", else None

    # UNIDENTIFIED:
    raw_unid = request.args.get("unidentified", "").lower()
    unidentified = _bool_map.get(raw_unid)  # → True if "true", False if "false", else None

    # tier + type + name resolved as before…
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param and tier_param.isdigit() else None

    # If the user typed in “search”, use that as the item_name;
    # otherwise fall back to the URL param.

    # 3) Call the same service behind your API
    result = market_service.get_item_listings(
        item_name=query_name,
        item_type=filter_type,
        sub_type=filter_sub_type,
        shiny=shiny,
        unidentified=unidentified,
        rarity=rarity,
        tier=tier,
        sort_option=sort,
        page=page,
        page_size=page_size
    )

    # 4) Enrich & unpack
    result_items = enrich_listings(result.get('items', []))
    total = result.get('total', 0)

    # 5) Render, passing everything back for pagination & form population
    return render_template(
        'market/listings.html',
        items=result_items,
        item_name=query_name,
        shiny=shiny,
        unidentified=unidentified,
        rarity=rarity,
        tier=tier,
        page=page,
        page_size=page_size,
        total=total,
        # (your template reads search and itemType via request.args,
        #  but you can also pass them explicitly if you like)
        itemType=filter_type,
        subType=filter_sub_type,
        sort=sort,
        SORT_OPTIONS=list(SortOption),
        TIERED_TYPES=TIERED_TYPES,
        SUBTYPE_OPTIONS=SUBTYPE_OPTIONS,
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
    if fmt == "skin":
        return f"https://mc-heads.net/head/{val}"
    if fmt == "aspect_attribute":
        return f"https://cdn.wynncraft.com/nextgen/abilities/2.1/aspects/{val}.png"

    return None


def enrich_listings(listings: list[dict]) -> list[dict]:
    for item in listings:
        item["icon_url"] = build_icon_url(item.get("icon"))
        name: str = item.get("name")
        shiny: bool = (item.get("shiny_stat") is not None)
        tier: int | None = None

        raw_tier = item.get("tier")
        if raw_tier is not None:
            try:
                tier: int = int(raw_tier)
            except (ValueError, TypeError):
                raise TypeError(f"Expected 'tier' to be int‐castable, but got {raw_tier!r}")

        item["price_averages"] = market_service.get_price(item_name=name, shiny=shiny, tier=tier)

        fixed_stats = []  # statRange.fixed == True   → always-same value
        rolled_stats = []  # statRange.fixed == False  → can roll

        for roll in item.get("stat_rolls") or []:
            (fixed_stats if roll["statRange"]["fixed"] else rolled_stats).append(roll)

        item["fixed_identifications"] = fixed_stats
        item["rolled_identifications"] = rolled_stats

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
