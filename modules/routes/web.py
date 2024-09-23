from flask import Blueprint, render_template
from datetime import datetime, timezone

from modules import wynn_api
from modules.routes import api


web_bp = Blueprint('web', __name__)

@web_bp.route("/")
@web_bp.route("/index")
def index():
    return lootrun_lootpool()

@web_bp.route("/items")
def items():
    items = wynn_api.get_item_database()
    return render_template("items.html", items=items)

@web_bp.route("/item") # TODO: TEST ONLY
def item():
    items = wynn_api.search_item(query="Collapse")
    return render_template("single_item.html", items=items)

@web_bp.route("/lootrun")
def lootrun_lootpool():
    loot_data = api.get_lootpool_items("lootpool")[0].get_json()

    if not isinstance(loot_data, list):
        loot_data = []

    now = datetime.now(timezone.utc)
    
    # Calculate time difference
    for item in loot_data:
        timestamp = datetime.strptime(item["timestamp"], '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
        time_diff = now - timestamp
        minutes = time_diff.total_seconds() // 60
        if minutes < 60:
            item["last_updated"] = f"Last updated {int(minutes)} minutes ago"
        else:
            hours = minutes // 60
            item["last_updated"] = f"Last updated {int(hours)} hours ago"
    
    return render_template("lootrun_lootpool.html", loot_data=loot_data)

@web_bp.route("/raid")
def raid_lootpool():
    loot_data = api.get_lootpool_items("raidpool")[0].get_json()

    if not isinstance(loot_data, list):
        loot_data = []

    now = datetime.now(timezone.utc)

    # Calculate time difference
    for item in loot_data:
        timestamp = datetime.strptime(item["timestamp"], '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
        time_diff = now - timestamp
        minutes = time_diff.total_seconds() // 60
        if minutes < 60:
            item["last_updated"] = f"Last updated {int(minutes)} minutes ago"
        else:
            hours = minutes // 60
            item["last_updated"] = f"Last updated {int(hours)} hours ago"

    return render_template("raid_lootpool.html", loot_data=loot_data)

@web_bp.route("/players")
def players():
    return lootrun_lootpool()
