import requests

from modules.utils import map_local_icons


BASE_URL = "https://beta-api.wynncraft.com/v3/"
def get_item_database():
    url = f"{BASE_URL}item/database?fullResult"
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
    url = f"{BASE_URL}item/search?page={page}"
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
    url = f"{BASE_URL}item/search"
    try:
        response = requests.get(f"{url}/{item_name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None
    
def get_lootpool():
    url = "https://nori.fish/api/lootpool"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            for item, icon in data["Icon"].items():
                print(item)
                if not str(icon).startswith("http"):
                    data["Icon"][item] = map_local_icons(icon)
                if "Simulator" in item:
                    data["Icon"][item] = "icons/simulator.webp"
                elif "Insulator" in item:
                    data["Icon"][item] = "icons/insulator.webp"
            return data
        else:
            print("Unexpected data format received:", type(data))
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None