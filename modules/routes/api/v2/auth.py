"""Authentication for the /api/v2 surface.

Differences from v1 (modules/auth.py):
- missing AND invalid keys both return 401 (v1 returns 403 for invalid);
- there are no public v2 endpoints — every route needs a valid key;
- the shared mod key is denied on all of v2 (it is pinned to the v1 paths);
- CORS preflight (OPTIONS) bypasses authentication.
"""
from functools import wraps

from flask import g, request

from modules import auth as v1_auth
from modules.routes.api.v2.errors import ApiError


def require_api_key_v2():
    if request.method == 'OPTIONS':
        return None

    token = v1_auth.extract_token()
    if not token:
        raise ApiError('missing_api_key', 'Missing API key', 401)

    token_hash, key_doc = v1_auth.lookup_key(token)
    if not key_doc:
        raise ApiError('invalid_api_key', 'Invalid or revoked API key', 401)

    g.api_key_hash = token_hash
    g.owner = key_doc['owner']
    g.scopes = key_doc.get('scopes', [])
    g.is_mod_key = (token_hash == v1_auth._MOD_KEY_HASH)

    if g.is_mod_key:
        raise ApiError('forbidden', 'The mod key cannot access /api/v2', 403)

    return None


def require_scope_v2(scope):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if scope not in g.scopes:
                raise ApiError('missing_scope',
                               f"API key lacks required scope '{scope}'", 403)
            return f(*args, **kwargs)

        return wrapped

    return decorator
