from flask import Blueprint, jsonify
from flask import request
import threading
from queue import Queue
import atexit

from modules import wynn_api
from modules.models import Weapon, Armor, Accessory, Item
from modules.models.item_types import WeaponType, ArmorType, AccessoryType
from modules import mongodb_connector


api_bp = Blueprint('api', __name__)
request_queue = Queue()


@api_bp.route("/api/item/<item_name>", methods=['GET'])
def get_item_stats(item_name):
    """ Retrieve item stats from the Wynn API by item name
    """
    item_data = wynn_api.quick_search_item(item_name)
    processed_data = process_item_data(item_data.get(item_name))
    return jsonify(processed_data)


@api_bp.route("/api/items", methods=['POST'])
def get_items():
    """ Search items on the Wynn API based on the provided query parameters
    """
    payload = request.json
    query = payload.get('query', '')
    item_type = payload.get('type', [])
    tier = payload.get('tier', [])
    attack_speed = payload.get('attackSpeed', [])
    level_range = payload.get('levelRange', [0, 110])
    professions = payload.get('professions', [])
    identifications = payload.get('identifications', [])
    major_ids = payload.get('majorIds', [])
    page = payload.get('page', 1)

    payload = {
        "query": query if query else None,
        "type": item_type if item_type else None,
        "tier": tier if tier else None,
        "attackSpeed": attack_speed if attack_speed else None,
        "levelRange": level_range if level_range != [0, 110] else None,
        "professions": professions if professions else None,
        "identifications": identifications if identifications else None,
        "majorIds": major_ids if major_ids else None
    }

    # Remove keys with None values
    payload = {k: v for k, v in payload.items() if v is not None}

    items_response = wynn_api.search_item(payload, page)

    if items_response is None:
        return jsonify([])

    items_data = items_response.get("results", {})
    processed_items = [process_item_data(item_data)
                       for item_data in items_data.values()]

    return jsonify({
        "items": processed_items,
        "next_page": items_response["controller"]["links"]["next"]
    })


@api_bp.route("/api/trademarket/items", methods=['POST'])
def save_trade_market_items():
    """ Save items to the trademarket collection
    """
    try:
        data = request.get_json()
        if not data:
            return {"message": "No items provided"}, 400

        items = data if isinstance(data, list) else [data]
        print(f"Received {len(items)} items to save to the database")

        env = request.args.get('env')
        if not env or env == 'dev':
            for item in items:
                formatted_item = format_item_for_db(item)
                request_queue.put(("trademarket", formatted_item, "prod"))

            return jsonify({"message": "Items received successfully"}), 200
        elif env == 'dev2':
            for item in items:
                formatted_item = format_item_for_db(item)
                request_queue.put(("trademarket", formatted_item, "dev"))

            return jsonify({"message": "Items saved to dev collection"}), 200
        else:
            return jsonify({"message": "Invalid environment specified. Only dev is allowed."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/trademarket/item/<item_name>", methods=['GET'])
def get_market_item_info(item_name):
    """ Retrieve items from the trademarket collection by name
    """
    if not item_name:
        return jsonify({"message": "No item name provided"}), 400
    result = mongodb_connector.get_trade_market_item(item_name)
    return result


@api_bp.route("/api/trademarket/item/<item_name>/price", methods=['GET'])
def get_market_item_price_info(item_name):
    """ Retrieve price information of items from the trademarket collection by name
    """
    if not item_name:
        return jsonify({"message": "No item name provided"}), 400
    result = mongodb_connector.get_trade_market_item_price(item_name)
    return result


@api_bp.route("/api/lootpool/items", methods=['POST'])
def save_lootpool_items():
    """ Save items to the lootpool collection
    """
    try:
        data = request.get_json()
        if not data:
            return {"message": "No items provided"}, 400

        items = data if isinstance(data, list) else [data]

        env = request.args.get('env')
        if not env or env == 'dev':
            for item in items:
                request_queue.put(("lootpool", item, "prod"))

            return jsonify({"message": "Items received successfully"}), 200
        elif env == 'dev2':
            for item in items:
                request_queue.put(("lootpool", item, "dev"))

            return jsonify({"message": "Items saved to dev collection"}), 200
        else:
            return jsonify({"message": "Invalid environment specified. Only dev is allowed."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/lootpool/items/", methods=['GET'])
def get_lootpool_items():
    """ Retrieve lootpool items
    """
    env = request.args.get('env', 'prod')
    result = mongodb_connector.get_lootpool_items(environment=env)
    return result


def process_item_data(item_data):
    """ Process item data from the Wynn API
    """
    item_subtype = item_data.get('type', item_data.get(
        'accessoryType', 'Unknown Subtype'))

    if item_subtype in [wt.value for wt in WeaponType]:
        item = Weapon.from_dict(item_data)
    elif item_subtype in [at.value for at in ArmorType]:
        item = Armor.from_dict(item_data)
    elif item_subtype in [act.value for act in AccessoryType]:
        item = Accessory.from_dict(item_data)
    else:
        raise ValueError(f"Unsupported item subtype: {item_subtype}")
    return item.to_dict()


def format_item_for_db(item):
    """ Format item data for database insertion
    """
    item_data = item.get('item', {})
    formatted_item = {
        "name": item_data.get('name'),
        "level": item_data.get('level'),
        "rarity": item_data.get('rarity'),
        "powder_slots": item_data.get('powderSlots'),
        "rerolls": item_data.get('rerollCount'),
        # "required_class": item_data.get('requiredClass'),
        "unidentified": item_data.get('unidentified'),
        "shiny_stat": item_data.get('shinyStat'),
        # "perfect": item_data.get('perfect'),
        # "defective": item_data.get('defective'),
        "amount": item.get('amount'),
        "overall_percentage": item_data.get('overallPercentage'),
        "listing_price": item.get('listingPrice'),
        "player_name": item.get('playerName'),
        "actual_stats_with_percentage": [
            {
                "value": stat.get('value'),
                "actual_roll_percentage": stat.get('actualRollPercentage'),
                "stat_name": stat.get('statName'),
                "range": stat.get('range', {})
            } for stat in item_data.get('actualStatsWithPercentage', [])
        ]
    }
    return formatted_item


def process_queue():
    """ Process the queue of items to save to the database
    """
    while True:
        request, item, env = request_queue.get()
        if item is None:
            break
        if request == 'trademarket':
            mongodb_connector.save_trade_market_item(item, env)
        elif request == 'lootpool':
            mongodb_connector.save_lootpool_item(item, env)
        request_queue.task_done()


def shutdown_worker():
    """ Shutdown the worker thread
    """
    request_queue.put(None)
    worker_thread.join()


# Start a worker thread to process the queue
worker_thread = threading.Thread(target=process_queue)
worker_thread.daemon = True
worker_thread.start()

atexit.register(shutdown_worker)
