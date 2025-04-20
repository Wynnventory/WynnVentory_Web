import hashlib
from flask import request, jsonify, g
from modules.db import get_collection
from modules.models.collection_types import Collection
from modules.utils.queue_worker import enqueue


def require_api_key():
    auth = request.headers.get("Authorization", "")

    if auth.startswith("Api-Key "):
        token = auth.split(" ", 1)[1]
    else:
        # fallback to X-API-Key header
        token = request.headers.get("X-API-Key")

    if not token:
        return jsonify({"error": "Missing API key"}), 401

    # validate key
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    key = get_collection(Collection.API_KEYS).find_one({
        "key_hash": token_hash,
        "revoked": False
    })
    if not key:
        return jsonify({"error": "Invalid or revoked API key"}), 403

    g.api_key_hash = token_hash
    g.owner = key["owner"]

    return None


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
