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
    
def get_aspect_by_name(class_name, aspect_name):
    url = f"{BASE_URL}/aspects/{class_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if aspect_name in data:
            return data[aspect_name]
        
        print(f"Aspect not found: {aspect_name}")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None