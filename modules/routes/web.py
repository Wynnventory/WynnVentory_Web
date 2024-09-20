from flask import Blueprint, render_template
from datetime import datetime

from modules import wynn_api
from modules.routes import api


web_bp = Blueprint('web', __name__)

@web_bp.route("/")
@web_bp.route("/index")
def index():
    return lootpool()

@web_bp.route("/items")
def items():
    items = wynn_api.get_item_database()
    return render_template("items.html", items=items)

@web_bp.route("/item") # TODO: TEST ONLY
def item():
    items = wynn_api.search_item(query="Collapse")
    return render_template("single_item.html", items=items)

@web_bp.route("/lootpool")
def lootpool():
    loot_data = api.get_lootpool_items()[0].get_json()
    
    now = datetime.utcnow()
    
    # Calculate time difference
    for item in loot_data:
        timestamp = datetime.strptime(item["timestamp"], '%a, %d %b %Y %H:%M:%S %Z')
        time_diff = now - timestamp
        minutes = time_diff.total_seconds() // 60
        if minutes < 60:
            item["last_updated"] = f"Last updated {int(minutes)} minutes ago"
        else:
            hours = minutes // 60
            if hours == 1:
                item["last_updated"] = f"Last updated 1 hour ago"
            else:
                item["last_updated"] = f"Last updated {int(hours)} hours ago"
    
    return render_template("lootpool.html", loot_data=loot_data)

@web_bp.route("/players")
def players():
    return lootpool()