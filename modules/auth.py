import hashlib
from functools import wraps

from flask import request, jsonify, g

from modules.config import Config
from modules.db import get_collection
from modules.models.collection_request import CollectionRequest
from modules.models.collection_types import Collection
from modules.utils.queue_worker import enqueue

# This should already be the SHA-256 hash of your baked-in mod key:
_MOD_KEY_HASH = Config.MOD_API_KEY

# Public endpoints (no key required)
_public_endpoints = set()
# Whitelist of view-function names the mod key may call
_mod_allowed_endpoints = set()

def public_endpoint(f):
    """Mark a view as public (skip auth entirely)."""
    _public_endpoints.add(f.__name__)
    return f

def mod_allowed(f):
    """Mark this view as allowed for the mod key."""
    _mod_allowed_endpoints.add(f.__name__)
    return f

def require_api_key():
    """
    1) Skip if this is @public_endpoint
    2) Extract & hash token, look it up in DB
    3) Stash g.owner, g.scopes
    4) Flag g.is_mod_key
    5) If it *is* the mod key, enforce default-deny on everything
       except what's in _mod_allowed_endpoints
    """
    # 1) public?
    if request.endpoint and '.' in request.endpoint:
        _, ep = request.endpoint.split('.', 1)
        if ep in _public_endpoints:
            return None

    # 2) pull the raw key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Api-Key "):
        token = auth.split(None, 1)[1].strip()
    else:
        token = request.headers.get("X-API-Key", "")

    if not token:
        return jsonify({"error": "Missing API key"}), 401

    # 2b) hash & look up
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    key_doc = get_collection(Collection.API_KEYS).find_one(
        {"key_hash": token_hash, "revoked": False},
        {"owner": 1, "scopes": 1}
    )
    if not key_doc:
        return jsonify({"error": "Invalid or revoked API key"}), 403

    # 3) stash
    g.api_key_hash = token_hash
    g.owner       = key_doc["owner"]
    g.scopes      = key_doc.get("scopes", [])

    # 4) is mod key?
    g.is_mod_key = (token_hash == _MOD_KEY_HASH)

    # 5) default-deny for mod
    if g.is_mod_key:
        # request.endpoint is like "market_bp.get_item_price"
        if request.endpoint and '.' in request.endpoint:
            _, ep = request.endpoint.split('.', 1)
        else:
            ep = request.endpoint or ""
        if ep not in _mod_allowed_endpoints:
            return jsonify({
                "error": "Forbidden, mod key not allowed on this endpoint"
            }), 403

    return None

def require_scope(scope):
    """
    Pure scope checker.  No mod logic here.
    """
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
        enqueue(CollectionRequest(
            type=Collection.API_USAGE,
            items=[{"owner": g.owner, "key_hash": g.api_key_hash}]
        ))
    return response
