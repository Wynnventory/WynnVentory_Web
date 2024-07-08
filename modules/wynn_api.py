import requests

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