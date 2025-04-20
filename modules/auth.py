import hashlib
from flask import request, jsonify
from modules.db import get_collection
from modules.models.collection_types import Collection


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

    return None
