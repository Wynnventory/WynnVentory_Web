import hashlib
from functools import wraps

from flask import request, jsonify, g
from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.utils.queue_worker import enqueue


def require_api_key():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Api-Key "):
        token = auth.split(" ", 1)[1].strip()
    else:
        token = request.headers.get("X-API-Key")

    if not token:
        return jsonify({"error": "Missing API key"}), 401

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    key_doc = get_collection(Collection.API_KEYS).find_one({"key_hash": token_hash, "revoked": False},
                            {"owner": 1, "scopes": 1})
    if not key_doc:
        return jsonify({"error": "Invalid or revoked API key"}), 403

    # stash owner and scopes
    g.api_key_hash = token_hash
    g.owner = key_doc["owner"]
    g.scopes = key_doc.get("scopes", [])
    return None


def require_scope(scope):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if scope not in g.scopes:
                return jsonify({"error": "Forbidden, missing scope"}), 403

            return f(*args, **kwargs)

        return wrapped

    return decorator


def record_api_usage(response):
    if hasattr(g, "owner"):
        enqueue(
            Collection.API_USAGE,
            {
                "owner": g.owner,
                "key_hash": g.api_key_hash
            }
        )
    return response
