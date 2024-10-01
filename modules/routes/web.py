from flask import Blueprint, render_template, request, abort
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
    # items = wynn_api.get_item_database()
    return render_template("items.html")

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
            if hours == 1:
                item["last_updated"] = f"Last updated {int(hours)} hour ago"
            else:
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
            if hours == 1:
                item["last_updated"] = f"Last updated {int(hours)} hour ago"
            else:
                item["last_updated"] = f"Last updated {int(hours)} hours ago"

    return render_template("raid_lootpool.html", loot_data=loot_data)

@web_bp.route("/players")
def players():
    return lootrun_lootpool()

@web_bp.route("/history/", defaults={'item_name': None})
@web_bp.route("/history/<item_name>")
@web_bp.route("/history/<item_name>/")
def history(item_name):
    # List of allowed IP addresses
    allowed_ips = ["83.76.209.66", "127.0.0.1"]

    
    # Check if the app is behind a proxy and get the real client IP
    if request.headers.getlist("X-Forwarded-For"):
        # 'X-Forwarded-For' may have a list of IPs, we take the first one as the client IP
        user_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        # Use 'remote_addr' if there is no proxy
        user_ip = request.remote_addr

    print(f"Trying to access price history for {item_name} from {user_ip}")
    # Check if the user's IP is in the list of allowed IPs
    if user_ip not in allowed_ips:
        abort(404)  # Show 404 error if the IP is not allowed
    
    
    # Render the price history page if IP is allowed
    return render_template("price_history.html", item_name=item_name)