import hashlib
from functools import wraps

from flask import current_app, request, jsonify, g

from modules.config import Config
from modules.db import get_collection
from modules.models.collection_request import CollectionRequest
from modules.models.collection_types import Collection
from modules.utils.queue_worker import enqueue

# This should already be the SHA-256 hash of your baked-in mod key:
_MOD_KEY_HASH = Config.MOD_API_KEY


def public_endpoint(f):
    """Mark a view as public (skip auth entirely)."""
    f._wv_public = True
    return f


def mod_allowed(f):
    """Mark this view as allowed for the mod key."""
    f._wv_mod_allowed = True
    return f


def _current_view():
    """Resolve the registered view function for the current request, if any."""
    if not request.endpoint:
        return None
    return current_app.view_functions.get(request.endpoint)


def extract_token():
    """Pull the raw API key from the Authorization or X-API-Key header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Api-Key "):
        return auth.split(None, 1)[1].strip()
    return request.headers.get("X-API-Key", "")


def lookup_key(token):
    """Hash a raw token and return its key document, or None."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    key_doc = get_collection(Collection.API_KEYS).find_one(
        {"key_hash": token_hash, "revoked": False},
        {"owner": 1, "scopes": 1}
    )
    return token_hash, key_doc


def require_api_key():
    """
    1) Skip if this is @public_endpoint
    2) Extract & hash token, look it up in DB
    3) Stash g.owner, g.scopes
    4) Flag g.is_mod_key
    5) If it *is* the mod key, enforce default-deny on everything
       not marked @mod_allowed
    """
    view = _current_view()

    # 1) public?
    if view is not None and getattr(view, "_wv_public", False):
        return None

    # 2) pull the raw key
    token = extract_token()
    if not token:
        return jsonify({"error": "Missing API key"}), 401

    # 2b) hash & look up
    token_hash, key_doc = lookup_key(token)
    if not key_doc:
        return jsonify({"error": "Invalid or revoked API key"}), 403

    # 3) stash
    g.api_key_hash = token_hash
    g.owner = key_doc["owner"]
    g.scopes = key_doc.get("scopes", [])

    # 4) is mod key?
    g.is_mod_key = (token_hash == _MOD_KEY_HASH)

    # 5) default-deny for mod
    if g.is_mod_key:
        if view is None or not getattr(view, "_wv_mod_allowed", False):
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
