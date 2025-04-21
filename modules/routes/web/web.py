from datetime import datetime, timezone

from flask import Blueprint, render_template, jsonify

from modules.services.lootpool_service import LootpoolService
from modules.services.raidpool_service import RaidpoolService

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
    loot_data = jsonify(LootpoolService().get_current_lootpool()).get_json()
    loot_data = loot_data if isinstance(loot_data, list) else []

    now = datetime.now(timezone.utc)

    for item in loot_data:
        timestamp = datetime.strptime(item["timestamp"], '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
        time_diff = now - timestamp
        minutes = time_diff.total_seconds() // 60
        if minutes < 60:
            item["last_updated"] = f"Last updated {int(minutes)} minutes ago"
        else:
            hours = minutes // 60
            item["last_updated"] = f"Last updated {int(hours)} hour{'s' if hours > 1 else ''} ago"

    return render_template("lootpool/lootrun_lootpool.html", loot_data=loot_data)

@web_bp.route("/raid")
def raid_lootpool():
    loot_data = jsonify(RaidpoolService().get_current_lootpool()).get_json()
    loot_data = loot_data if isinstance(loot_data, list) else []

    now = datetime.now(timezone.utc)

    for item in loot_data:
        timestamp = datetime.strptime(item["timestamp"], '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
        time_diff = now - timestamp
        minutes = time_diff.total_seconds() // 60
        if minutes < 60:
            item["last_updated"] = f"Last updated {int(minutes)} minutes ago"
        else:
            hours = minutes // 60
            item["last_updated"] = f"Last updated {int(hours)} hour{'s' if hours > 1 else ''} ago"

    return render_template("lootpool/raid_lootpool.html", loot_data=loot_data)

@web_bp.route("/history/", defaults={'item_name': None})
@web_bp.route("/history/<item_name>")
@web_bp.route("/history/<item_name>/")
def history(item_name):
    return render_template("market/price_history.html", item_name=item_name)

@web_bp.route("/ranking")
def ranking():
    return render_template("market/price_ranking.html")