import threading
from queue import Queue

from flask import Blueprint, jsonify
from flask import request

from modules import db
from modules import utils
from modules import wynn_api
from modules.models import Weapon, Armour, Accessory, Item
from modules.models.item_types import WeaponType, ArmorType, AccessoryType
from modules.models.collection_types import Collection

api_bp = Blueprint('api', __name__)
request_queue = Queue()
SUPPORTED_VERSION = '0.9.0'


@api_bp.route("/api/aspect/<class_name>/<aspect_name>", methods=['GET'])
@api_bp.route("/api/aspect/<class_name>/<aspect_name>/", methods=['GET'])
def get_aspect_stats(class_name, aspect_name):
    """ Retrieve aspect stats from the Wynn API by aspect class and name
    """
    aspect_data = wynn_api.get_aspect_by_name(class_name, aspect_name)
    return jsonify(aspect_data)


@api_bp.route("/api/item/<item_name>", methods=['GET'])
@api_bp.route("/api/item/<item_name>/", methods=['GET'])
def get_item_stats(item_name):
    """ Retrieve item stats from the Wynn API by item name
    """
    item_data = wynn_api.quick_search_item(item_name)
    processed_data = process_item_data(item_data)
    return jsonify(processed_data)


@api_bp.route("/api/items", methods=['POST'])
@api_bp.route("/api/items/", methods=['POST'])
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
@api_bp.route("/api/trademarket/items/", methods=['POST'])
def save_trade_market_items():
    """ Save items to the trademarket collection
    """
    try:
        data = request.get_json()

        if not data or len(data) < 1:
            return {"message": "No items provided"}, 400

        items = data if isinstance(data, list) else [data]

        for item in items:
            formatted_item = format_item_for_db(item)
            request_queue.put((Collection.MARKET, formatted_item))

        return jsonify({"message": "Items received successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/trademarket/item/<item_name>", methods=['GET'])
@api_bp.route("/api/trademarket/item/<item_name>/", methods=['GET'])
def get_market_item_info(item_name):
    """ Retrieve items from the trademarket collection by name
    """
    if not item_name:
        return jsonify({"message": "No item name provided"}), 400
    result = db.get_trade_market_item(item_name)
    return result


@api_bp.route("/api/trademarket/item/<item_name>/price", methods=['GET'])
@api_bp.route("/api/trademarket/item/<item_name>/price/", methods=['GET'])
def get_market_item_price_info(item_name):
    if not item_name:
        return jsonify({"message": "No item name provided"}), 400

    shiny_str = request.args.get('shiny', 'false')  # default to 'false'
    shiny = shiny_str.lower() == 'true'

    # Get tier from query parameters if provided.
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    result = db.get_trade_market_item_price(item_name, shiny, tier)
    return result


@api_bp.route("/api/lootpool/items", methods=['POST'])
@api_bp.route("/api/lootpool/items/", methods=['POST'])
def save_lootpool_items():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No items provided"}), 400

        return save_pool(data, "lootpool", )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/lootpool/<pool>/items", methods=['GET'])
@api_bp.route("/api/lootpool/<pool>/items/", methods=['GET'])
def get_lootpool_items(pool):
    """ Retrieve lootpool items
    """
    if pool == "raidpool":
        result = db.get_raidpool_items()
    elif pool == "lootpool":
        result = db.get_lootpool_items()
    else:
        return jsonify({"message": "No pool with this name exists"}), 404

    return result


@api_bp.route("/api/lootpool/<pool>", methods=['GET'])
@api_bp.route("/api/lootpool/<pool>/", methods=['GET'])
def get_lootpool_items_raw(pool):
    """ Retrieve lootpool items
    """
    if pool == "raidpool":
        result = db.get_raidpool_items_raw()
    elif pool == "lootpool":
        result = db.get_lootpool_items_raw()
    else:
        return jsonify({"message": "No pool with this name exists"}), 404

    return result


@api_bp.route("/api/raidpool/items", methods=['POST'])
@api_bp.route("/api/raidpool/items/", methods=['POST'])
def save_raidpool_items():
    """Save items to the raidpool collection."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No items provided"}), 400

        return save_pool(data, Collection.RAID)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def save_pool(data, pool_type):
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
            else:
                lootpoolItems = item.get('items')
                shinyCount = 0

                for lootpoolItem in lootpoolItems:
                    if lootpoolItem.get('shiny'):
                        shinyCount += 1

                if shinyCount <= 1:
                    request_queue.put((pool_type, item))
                else:
                    print(f"Lootpool contained too many shinies: {shinyCount}; DATA: {item}")

        return jsonify({"message": f"Items saved to {pool_type} collection successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/trademarket/history/<item_name>", methods=['GET'])
@api_bp.route("/api/trademarket/history/<item_name>/", methods=['GET'])
def get_market_history(item_name):
    """ Retrieve price history of an item from the trademarket archive collection """
    days = request.args.get('days', 14)

    shiny_str = request.args.get('shiny', 'false')  # default to 'false'
    shiny = shiny_str.lower() == 'true'

    # Get tier from query parameters if provided.
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    result = db.get_price_history(item_name, shiny, days, tier)

    return result


@api_bp.route("/api/trademarket/history/<item_name>/latest", methods=['GET'])
def get_latest_market_history(item_name):
    """ Retrieve price history of an item from the trademarket archive collection """
    shiny_str = request.args.get('shiny', 'false')  # default to 'false'
    shiny = shiny_str.lower() == 'true'

    # Get tier from query parameters if provided.
    tier_param = request.args.get('tier')
    tier = int(tier_param) if tier_param is not None else None

    result = db.get_latest_price_history(item_name, shiny, tier)

    return result


@api_bp.route("/api/trademarket/ranking", methods=['GET'])
@api_bp.route("/api/trademarket/ranking/", methods=['GET'])
def get_all_items_ranking():
    """
    Retrieve a ranking of items based on their archived price data.
    For example, you can rank them by average price.
    """
    ranking_data = db.get_all_items_ranking()

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
        "listing_price": item.get('listingPrice'),
        "amount": item.get('amount'),
        "item_type": item_data.get('item_type'),
        "type": item_data.get('type'),
        "rarity": item_data.get('rarity'),
        "unidentified": item_data.get('unidentified'),
        "shiny_stat": item_data.get('shinyStat'),
        "tier": item_data.get('tier'),
        "player_name": item.get('playerName'),
        "mod_version": item.get('modVersion'),
        "hash_code": item.get('hash_code')
    }

    return formatted_item


def process_queue():
    while True:
        request_type, item = request_queue.get()
        if item is None:
            request_queue.task_done()
            print("Worker has finished task")
            break
        try:
            if request_type == Collection.MARKET:
                db.save_trade_market_item(item)
            elif request_type == Collection.LOOT:
                db.save_lootpool_item(item)
            elif request_type == Collection.RAID:
                db.save_raidpool_item(item)
        except Exception as e:
            # Log the error so you can investigate it further.
            print(f"Error processing {request_type} item: {e}")
        finally:
            request_queue.task_done()


def shutdown_worker():
    """ Shutdown the worker thread
    """
    request_queue.put(None)
    worker_thread.join()
    print("Shutting down worker thread")


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


worker_thread = threading.Thread(target=process_queue)
worker_thread.daemon = True
worker_thread.start()
print("Worker thread started")
