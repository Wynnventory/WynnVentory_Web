from typing import Dict

from modules.models.accessory import Accessory
from modules.models.armour import Armour
from modules.models.item import Item
from modules.models.item_types import WeaponType, ArmorType, AccessoryType
from modules.models.weapon import Weapon
from modules.routes.api import wynncraft_api
from modules.schemas.item_search import ItemSearchRequest


# Wynncraft v3 gives every item a single `subType`; the model classes were
# written against the legacy per-family field names.
_LEGACY_SUBTYPE_FIELD = {
    'weapon': 'weaponType',
    'armour': 'armourType',
    'accessory': 'accessoryType',
    'tome': 'tomeType',
}


def _normalize(data):
    """Map the current Wynncraft v3 item schema onto the legacy field names
    the model classes read.

    Current payloads carry `displayName`/`internalName`, `tier`, and
    `subType`; the models expect `item_name`, `rarity`, and
    `weaponType`/`armourType`/`accessoryType`. Legacy-shaped payloads pass
    through untouched.
    """
    normalized = dict(data)
    if 'item_name' not in normalized:
        name = normalized.get('displayName') or normalized.get('internalName')
        if name:
            normalized['item_name'] = name
    if 'rarity' not in normalized and 'tier' in normalized:
        normalized['rarity'] = normalized['tier']
    legacy_field = _LEGACY_SUBTYPE_FIELD.get(normalized.get('type'))
    if legacy_field and legacy_field not in normalized \
            and 'subType' in normalized:
        normalized[legacy_field] = normalized['subType']
    return normalized


def _process(data):
    """
    Process item data from the Wynncraft API and store it in the appropriate model class.

    Args:
        data (dict): The raw item data from the Wynncraft API

    Returns:
        dict: The processed item data as a dictionary

    Raises:
        ValueError: If the item type or subtype is not supported
    """
    if not data:
        return None

    data = _normalize(data)
    item_type = data.get('type', 'Unknown Type')
    item_subtype = data.get('weaponType',
                            data.get('armourType',
                                     data.get('accessoryType',
                                              data.get('tome', 'Unknown Subtype'))))

    # Map item types to their respective classes and enum types
    type_mapping = {
        'weapon': (Weapon, WeaponType),
        'armour': (Armour, ArmorType),
        'accessory': (Accessory, AccessoryType),
        'tome': (Item, None)
    }

    if item_type not in type_mapping:
        raise ValueError(f"Unsupported item type: {item_type}")

    item_class, enum_type = type_mapping[item_type]

    if item_type == 'tome':
        item = item_class.from_dict(data, 'tome')
    elif item_subtype in [et.value for et in enum_type] if enum_type else []:
        item = item_class.from_dict(data)
    else:
        raise ValueError(f"Unsupported {item_type} subtype: {item_subtype}")

    return item.to_dict()


def _extract_result_items(api_resp):
    """Return search-result items as a list.

    Wynncraft v3 returns `results` as an array of item objects; older
    revisions used a name-keyed map. Accept both.
    """
    raw_items = api_resp.get("results") or []
    if isinstance(raw_items, dict):
        for name, info in raw_items.items():
            info["item_name"] = name
        raw_items = list(raw_items.values())
    return raw_items


def search_items(req: ItemSearchRequest) -> Dict:
    """Search for items based on the provided criteria."""
    # Skip empty values, default level range, and pagination parameter
    criteria = {}
    for k, v in req.dict().items():
        # Skip None values
        if v is None:
            continue
        # Skip empty lists/tuples
        if isinstance(v, (list, tuple)) and len(v) == 0:
            continue
        # Skip default level range
        if k == "levelRange" and v == (0, 110):
            continue
        # Skip page parameter (handled separately)
        if k == "page":
            continue
        # Add valid criteria
        criteria[k] = v

    api_resp = wynncraft_api.search_items(criteria, req.page)
    if not api_resp:
        return {"items": [], "next_page": None}

    processed = [_process(i) for i in _extract_result_items(api_resp)]
    return {
        "items": processed,
        "next_page": api_resp["controller"].get("next")
    }


def fetch_item(name: str) -> dict:
    """
    Fetch a single item by name from the Wynncraft API.

    Args:
        name (str): The name of the item to fetch

    Returns:
        dict: The processed item data as a dictionary
    """
    return _process(wynncraft_api.quick_search_item(name))
