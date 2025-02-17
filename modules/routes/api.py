from flask import Blueprint, jsonify
from flask import request
import threading
from queue import Queue
import atexit

from modules import wynn_api
from modules.models import Weapon, Armour, Accessory, Item
from modules.models.item_types import WeaponType, ArmorType, AccessoryType
from modules import mongodb_connector
from modules import utils


api_bp = Blueprint('api', __name__)
request_queue = Queue()
SUPPORTED_VERSION = '0.8.9'

WHITELISTED_PLAYERS = ["Aruloci", "SiropBVST", "red_fire_storm"]

@api_bp.route("/api/aspect/<class_name>/<aspect_name>", methods=['GET'])
def get_aspect_stats(class_name, aspect_name):
    """ Retrieve aspect stats from the Wynn API by aspect class and name
    """
    aspect_data = wynn_api.get_aspect_by_name(class_name, aspect_name)
    return jsonify(aspect_data)

@api_bp.route("/api/item/<item_name>", methods=['GET'])
def get_item_stats(item_name):
    """ Retrieve item stats from the Wynn API by item name
    """
    item_data = wynn_api.quick_search_item(item_name)
    processed_data = process_item_data(item_data)
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
        if not data or len(data) <= 1:
            return {"message": "No items provided"}, 400

        items = data if isinstance(data, list) else [data]

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

    user = request.args.get('playername')
    if user not in WHITELISTED_PLAYERS:
        return jsonify({"message": "Unauthorized"}), 401

    env = request.args.get('env')
    if env == 'dev2':
        env = "dev"
    else:
        env = "prod"
    result = mongodb_connector.get_trade_market_item_price(item_name, env)
    return result


@api_bp.route("/api/lootpool/items", methods=['POST'])
def save_lootpool_items():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No items provided"}), 400

        env = request.args.get('env', 'prod')
        if env not in ['prod', 'dev', 'dev2']:
            return jsonify({"message": "Invalid environment specified. Only 'prod', 'dev' and 'dev2' are allowed."}), 400

        return save_pool(data, "lootpool", env)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/lootpool/<pool>/items/", methods=['GET'])
def get_lootpool_items(pool):
    """ Retrieve lootpool items
    """
    env = request.args.get('env', 'prod')
    if pool == "raidpool":
        result = mongodb_connector.get_raidpool_items(environment=env)
    else:
        result = mongodb_connector.get_lootpool_items(environment=env)

    return result

@api_bp.route("/api/lootpool/<pool>/", methods=['GET'])
def get_lootpool_items_raw(pool):
    """ Retrieve lootpool items
    """
    env = request.args.get('env', 'prod')
    if pool == "raidpool":
        result = mongodb_connector.get_raidpool_items_raw(environment=env)
    else:
        result = mongodb_connector.get_lootpool_items_raw(environment=env)

    return result

@api_bp.route("/api/raidpool/items", methods=['POST'])
def save_raidpool_items():
    """Save items to the raidpool collection."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No items provided"}), 400

        env = request.args.get('env', 'prod')
        if env not in ['prod', 'dev', 'dev2']:
            return jsonify({"message": "Invalid environment specified. Only 'prod', 'dev' and 'dev2' are allowed."}), 400

        return save_pool(data, "raidpool", env)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def save_pool(data, pool_type, env):
    try:
        if not data:
            return jsonify({"message": "No items provided"}), 400

        # Normalize data into a list.
        items = data if isinstance(data, list) else [data]

        # Validate modVersion and collectionTime for every item in one loop.
        for idx, item in enumerate(items):
            mod_version = item.get('modVersion')
            if not mod_version or not compare_versions(mod_version, SUPPORTED_VERSION):
                print(f"Item at index {idx} has unsupported mod version: {mod_version}")
                return jsonify({"message": f"Only mod version {SUPPORTED_VERSION} is supported for all items."}), 400

            collection_time = item.get('collectionTime')
            if not collection_time or not utils.is_time_valid(pool_type, collection_time):
                print(f"Item at index {idx} has an invalid collectionTime: {collection_time}")
                return jsonify({"message": "One or more items have an invalid timestamp."}), 400

        if env not in ['prod', 'dev', 'dev2']:
            return jsonify({"message": "Invalid environment specified. Only 'prod', 'dev' and 'dev2' are allowed."}), 400

        print(f"Saving {len(items)} {pool_type} items to {env} collection")
        for item in items:
            request_queue.put((pool_type, item, env))

        return jsonify({"message": f"Items saved to {env} {pool_type} collection successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/api/trademarket/<item_name>/history/", methods=['GET'])
def get_market_history(item_name):
    """ Retrieve price history of an item from the trademarket archive collection
    """
    env = request.args.get('env', 'prod')
    result = mongodb_connector.get_price_history(item_name, env)

    return result

@api_bp.route("/api/trademarket/ranking/", methods=['GET'])
def get_all_items_ranking():
    """
    Retrieve a ranking of items based on their archived price data.
    For example, you can rank them by average price.
    """
    env = request.args.get('env', 'prod')
    ranking_data = mongodb_connector.get_all_items_ranking(env)

    # ranking_data should already be in a JSON-serializable format.
    return ranking_data

def process_item_data(item_data):
    """Process item data from the Wynn API and store it in the appropriate model class."""
    item_type = item_data.get('type', 'Unknown Type')
    item_subtype = item_data.get('weaponType',
                                 item_data.get('armourType',
                                               item_data.get('accessoryType',
                                                             item_data.get('tome',
                                                             'Unknown Subtype'))))

    if item_type == 'weapon':
        if item_subtype in [wt.value for wt in WeaponType]:
            item = Weapon.from_dict(item_data)
        else:
            raise ValueError(f"Unsupported weapon subtype: {item_subtype}")
    elif item_type == 'armour':
        if item_subtype in [at.value for at in ArmorType]:
            item = Armour.from_dict(item_data)
        else:
            raise ValueError(f"Unsupported armor subtype: {item_subtype}")
    elif item_type == 'accessory':
        if item_subtype in [act.value for act in AccessoryType]:
            item = Accessory.from_dict(item_data)
        else:
            raise ValueError(f"Unsupported accessory subtype: {item_subtype}")
    elif item_type == 'tome':
        item = Item.from_dict(item_data, 'tome')
    else:
        raise ValueError(f"Unsupported item type: {item_type}")

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
        "mod_version": item.get('modVersion'),
        "actual_stats_with_percentage": [
            {
                "value": stat.get('value'),
                "actual_roll_percentage": stat.get('actualRollPercentage'),
                "stat_name": stat.get('statName'),
                # "range": stat.get('range', {})
            } for stat in item_data.get('actualStatsWithPercentage', [])
        ]
    }
    return formatted_item


def process_queue():
    while True:
        request_type, item, env = request_queue.get()
        if item is None:
            request_queue.task_done()
            print(f"Worker has finished task")
            break
        try:
            if request_type == 'trademarket':
                mongodb_connector.save_trade_market_item(item, env)
            elif request_type == 'lootpool':
                mongodb_connector.save_lootpool_item(item, env)
            elif request_type == 'raidpool':
                mongodb_connector.save_raidpool_item(item, env)
        except Exception as e:
            # Log the error so you can investigate it further.
            print(f"Error processing {request_type} item: {e}")
        finally:
            request_queue.task_done()

def shutdown_workers():
    for _ in worker_threads:
        request_queue.put((None, None, None))
    for t in worker_threads:
        t.join()

def compare_versions(version_a: str, version_b: str) -> bool:
    if version_a.lower().find("dev") != -1:
        return True
    
    # Split the versions by dot and convert each part to an integer
    parts_a = list(map(int, version_a.split('.')))
    parts_b = list(map(int, version_b.split('.')))

    # Compare each part: major, minor, patch
    for a, b in zip(parts_a, parts_b):
        if a > b:
            return True
        elif a < b:
            return False
    return True


NUM_WORKERS = 4
worker_threads = []
for _ in range(NUM_WORKERS):
    print(f"Starting worker thread {_ + 1}")
    t = threading.Thread(target=process_queue, daemon=True)
    t.start()
    worker_threads.append(t)

