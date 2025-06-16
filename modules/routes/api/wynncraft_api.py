import logging
import time
from functools import wraps
from typing import Dict, Any, Callable, Optional

import requests
import unicodedata

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


def api_request(func):
    """Decorator to handle API requests and error handling"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.Timeout:
            logging.error("Request timed out")
        except Exception as err:
            logging.error(f"Other error occurred: {err}")
        return None

    return wrapper


@cached(ttl=3600)  # Cache for 1 hour
@api_request
def get_item_database():
    url = f"{BASE_URL}/item/database?fullResult"
    # Add timeout to prevent hanging requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        return data
    else:
        logging.warning("Unexpected data format received: %s", type(data))
        return None


@cached(ttl=300)  # Cache for 5 minutes
@api_request
def search_items(payload, page=1):
    url = f"{BASE_URL}/item/search?page={page}"
    # Add timeout to prevent hanging requests
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


@cached(ttl=1800)  # Cache for 30 minutes
@api_request
def quick_search_item(item_name):
    url = f"{BASE_URL}/item/search"
    response = requests.get(f"{url}/{item_name}", timeout=10)

    if response.status_code != 200:
        return None

    data = response.json()
    normalized_target = clean_name(item_name)

    for key, obj in data.items():
        print(f"{normalized_target} -> {clean_name(key)}")
        if clean_name(key) == normalized_target:
            obj['item_name'] = key
            return obj

    return None  # No match found


@cached(ttl=1800)  # Cache for 30 minutes
@api_request
def get_aspect_by_name(class_name, aspect_name):
    url = f"{BASE_URL}/aspects/{class_name}"
    # Add timeout to prevent hanging requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if aspect_name in data:
        return data[aspect_name]

    logging.warning(f"Aspect not found: {aspect_name}")
    return None


def clean_name(name: str) -> str:
    """Normalize and remove all non-ASCII characters for accurate matching."""
    # Normalize to decomposed form (e.g., é → e + ́)
    name = unicodedata.normalize('NFKD', name)
    # Remove combining marks and non-ASCII characters
    cleaned = ''.join(
        c for c in name
        if not unicodedata.combining(c) and ord(c) < 128
    )
    return cleaned.strip().casefold()
