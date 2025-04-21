from typing import Dict

from modules.models.accessory import Accessory
from modules.models.armour import Armour
from modules.models.item import Item
from modules.models.item_types import WeaponType, ArmorType, AccessoryType
from modules.models.weapon import Weapon
from modules.routes.api import wynncraft_api
from modules.schemas.item_search import ItemSearchRequest


def _process(data):
    """Process item data from the Wynncraft API and store it in the appropriate model class."""
    item_type = data.get('type', 'Unknown Type')
    item_subtype = data.get('weaponType',
                            data.get('armourType',
                                     data.get('accessoryType',
                                              data.get('tome', 'Unknown Subtype'))))

    if item_type == 'weapon':
        if item_subtype in [wt.value for wt in WeaponType]:
            item = Weapon.from_dict(data)
        else:
            raise ValueError(f"Unsupported weapon subtype: {item_subtype}")
    elif item_type == 'armour':
        if item_subtype in [at.value for at in ArmorType]:
            item = Armour.from_dict(data)
        else:
            raise ValueError(f"Unsupported armor subtype: {item_subtype}")
    elif item_type == 'accessory':
        if item_subtype in [act.value for act in AccessoryType]:
            item = Accessory.from_dict(data)
        else:
            raise ValueError(f"Unsupported accessory subtype: {item_subtype}")
    elif item_type == 'tome':
        item = Item.from_dict(data, 'tome')
    else:
        raise ValueError(f"Unsupported item type: {item_type}")

    return item.to_dict()


def search_items(req: ItemSearchRequest) -> Dict:
    criteria = {
        k: v
        for k, v in req.dict().items()
        if not (
                v is None
                or (isinstance(v, (list, tuple)) and len(v) == 0)
                or (k == "levelRange" and v == (0, 110)
                or (k == "page"))
        )
    }

    print(criteria)
    api_resp = wynncraft_api.search_items(criteria, req.page)
    print(api_resp)
    if not api_resp:
        return {"items": [], "next_page": None}

    raw_items = api_resp.get("results", {}).values()
    processed = [_process(i) for i in raw_items]
    return {
        "items": processed,
        "next_page": api_resp["controller"]["links"].get("next")
    }


def fetch_item(name: str) -> dict:
    raw = wynncraft_api.quick_search_item(name)
    return _process(raw)
