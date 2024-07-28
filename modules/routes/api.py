from flask import Blueprint, jsonify

from modules import wynn_api
from modules.models import Weapon, Armor, Accessory
from modules.models.item_types import WeaponType, ArmorType, AccessoryType


api_bp = Blueprint('api', __name__)

@api_bp.route("/api/item/<item_name>", methods=['GET'])
def get_item_stats(item_name):
    item_data = wynn_api.quick_search_item(item_name)
    processed_data = process_item_data(item_data.get(item_name))
    return jsonify(processed_data)

def process_item_data(item_data):
    item_subtype = item_data.get('type', item_data.get('accessoryType', 'Unknown Subtype'))

    if item_subtype in [wt.value for wt in WeaponType]:
        item = Weapon.from_dict(item_data)
    elif item_subtype in [at.value for at in ArmorType]:
        item = Armor.from_dict(item_data)
    elif item_subtype in [act.value for act in AccessoryType]:
        item = Accessory.from_dict(item_data)
    else:
        raise ValueError(f"Unsupported item subtype: {item_subtype}")

    return item.to_dict()