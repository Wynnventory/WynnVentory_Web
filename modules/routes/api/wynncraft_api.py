import requests
import time
from functools import wraps
from typing import Dict, Any, Callable, Optional


BASE_URL = "https://api.wynncraft.com/v3"

# Simple in-memory cache with TTL
class Cache:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            if entry['expiry'] > time.time():
                return entry['data']
            else:
                # Remove expired entry
                del self.cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store value in cache with TTL in seconds (default 5 minutes)"""
        self.cache[key] = {
            'data': value,
            'expiry': time.time() + ttl
        }

    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()

# Initialize cache
_cache = Cache()

def cached(ttl: int = 300):
    """Decorator to cache function results with TTL in seconds"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check if result is in cache
            cached_result = _cache.get(key)
            if cached_result is not None:
                return cached_result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            if result is not None:  # Only cache successful results
                _cache.set(key, result, ttl)

            return result
        return wrapper
    return decorator
@cached(ttl=3600)  # Cache for 1 hour
def get_item_database():
    url = f"{BASE_URL}/item/database?fullResult"
    try:
        # Add timeout to prevent hanging requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        else:
            print("Unexpected data format received:", type(data))
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None


@cached(ttl=300)  # Cache for 5 minutes
def search_items(payload, page=1):
    url = f"{BASE_URL}/item/search?page={page}"
    try:
        # Add timeout to prevent hanging requests
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None

@cached(ttl=1800)  # Cache for 30 minutes
def quick_search_item(item_name):
    url = f"{BASE_URL}/item/search"
    try:
        # Add timeout to prevent hanging requests
        response = requests.get(f"{url}/{item_name}", timeout=10)
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
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None

@cached(ttl=1800)  # Cache for 30 minutes
def get_aspect_by_name(class_name, aspect_name):
    url = f"{BASE_URL}/aspects/{class_name}"
    try:
        # Add timeout to prevent hanging requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if aspect_name in data:
            return data[aspect_name]

        print(f"Aspect not found: {aspect_name}")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.Timeout:
        print("Request timed out")
        return None
    except Exception as err:
        print(f"Other error occurred: {err}")
        return None
