import requests

from modules.utils import map_local_icons


BASE_URL = "https://api.wynncraft.com/v3"
def get_item_database():
    url = f"{BASE_URL}/item/database?fullResult"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        else:
            print("Unexpected data format received:", type(data))
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None
    

def search_item(payload, page=1):
    url = f"{BASE_URL}/item/search?page={page}"
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None
    
def quick_search_item(item_name):
    # url = f"{BASE_URL}item/search"
    url = f"{BASE_URL}/item/search"
    try:
        response = requests.get(f"{url}/{item_name}")
        response.raise_for_status()
        data = response.json()
        
        if item_name in data:
            return data[item_name]
        
        # If no match is found, return None or an appropriate message
        print(f"Item not found: {item_name}")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None
    
def get_lootpool():
    # url = "https://nori.fish/api/lootpool"
    # try:
    #     response = requests.get(url)
    #     response.raise_for_status()
    #     data = response.json()
    #     if isinstance(data, dict):
    #         for item, icon in data["Icon"].items():
    #             print(item)
    #             if not str(icon).startswith("http"):
    #                 data["Icon"][item] = map_local_icons(icon)
    #             if "Simulator" in item:
    #                 data["Icon"][item] = "icons/simulator.webp"
    #             elif "Insulator" in item:
    #                 data["Icon"][item] = "icons/insulator.webp"
    #         return data
        # else:
        #     print("Unexpected data format received:", type(data))
        #     return None
    # except requests.exceptions.HTTPError as http_err:
    #     print(f"HTTP error occurred: {http_err}")
    # except Exception as err:
    #     print(f"Other error occurred: {err}")
    loot_items = {
        "Loot": {
            "SE": {
                "Shiny": {
                    "Item": "Crusade Sabatons",
                    "Tracker": "Lootruns completed"
                },
                "Mythic": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Fabled": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Legendary": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Rare": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Unique": ["Immolation", "Lament", "Archangel", "Guardian"],
            },
            "Molten Heights": {
                "Shiny": {
                    "Item": "Crusade Sabatons",
                    "Tracker": "Lootruns completed"
                },
                "Mythic": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Fabled": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Legendary": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Rare": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Unique": ["Immolation", "Lament", "Archangel", "Guardian"],
            },
            "Sky": {
                "Shiny": {
                    "Item": "Crusade Sabatons",
                    "Tracker": "Lootruns completed"
                },
                "Mythic": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Fabled": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Legendary": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Rare": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Unique": ["Immolation", "Lament", "Archangel", "Guardian"],
            },
            "COTL": {
                "Shiny": {
                    "Item": "Crusade Sabatons",
                    "Tracker": "Lootruns completed"
                },
                "Mythic": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Fabled": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Legendary": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Rare": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Unique": ["Immolation", "Lament", "Archangel", "Guardian"],
            },
            "Corkus": {
                "Shiny": {
                    "Item": "Crusade Sabatons",
                    "Tracker": "Lootruns completed"
                },
                "Mythic": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Fabled": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Legendary": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Rare": ["Immolation", "Lament", "Archangel", "Guardian"],
                "Unique": ["Immolation", "Lament", "Archangel", "Guardian"],
            },
        },
        "Icon": {
            "Crusade Sabatons": "https://cdn.wynncraft.com/nextgen/itemguide/3.3/diamond_boots.webp",
            "Immolation": "https://cdn.wynncraft.com/nextgen/itemguide/3.3/relik.fire3.webp",
            "Lament": "https://cdn.wynncraft.com/nextgen/itemguide/3.3/wand.water3.webp",
            "Archangel": "https://cdn.wynncraft.com/nextgen/itemguide/3.3/spear.air3.webp",
            "Guardian": "https://cdn.wynncraft.com/nextgen/itemguide/3.3/spear.fire3.webp",

        }
    }
    for item, icon in loot_items["Icon"].items():
        if not str(icon).startswith("http"):
            loot_items["Icon"][item] = map_local_icons(icon)
    return loot_items