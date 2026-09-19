"""Authentication for the /api/v2 surface.

Differences from v1 (modules/auth.py):
- missing AND invalid keys both return 401 (v1 returns 403 for invalid);
- there are no public v2 endpoints — every route needs a valid key;
- the shared mod key is accepted only on views marked @mod_allowed (the four
  reads the game mod performs) and denied everywhere else on v2;
- the website's own pages carry a signed session cookie instead of a key; it
  is accepted only on views marked @site_allowed (the four reads the site's
  JavaScript performs — v1's formerly public surface) and denied elsewhere;
- CORS preflight (OPTIONS) bypasses authentication.
"""
from functools import wraps

from flask import g, request, session

from modules import auth as v1_auth
from modules.routes.api.v2.errors import ApiError


SITE_OWNER = 'website'
SITE_SCOPES = ['read:market']


def site_allowed(f):
    """Mark this view as callable with the website's session instead of a key."""
    f._wv_site_allowed = True
    return f


def _authenticate_site_session():
    view = v1_auth._current_view()
    if view is None or not getattr(view, '_wv_site_allowed', False):
        raise ApiError('forbidden',
                       'The website session is not allowed on this endpoint', 403)
    g.api_key_hash = SITE_OWNER
    g.owner = SITE_OWNER
    g.scopes = list(SITE_SCOPES)
    g.is_mod_key = False


def require_api_key_v2():
    if request.method == 'OPTIONS':
        return None

    token = v1_auth.extract_token()
    if not token:
        if session.get('site'):
            _authenticate_site_session()
            return None
        raise ApiError('missing_api_key', 'Missing API key', 401)

    token_hash, key_doc = v1_auth.lookup_key(token)
    if not key_doc:
        raise ApiError('invalid_api_key', 'Invalid or revoked API key', 401)

    g.api_key_hash = token_hash
    g.owner = key_doc['owner']
    g.scopes = key_doc.get('scopes', [])
    g.is_mod_key = (token_hash == v1_auth._MOD_KEY_HASH)

    if g.is_mod_key:
        view = v1_auth._current_view()
        if view is None or not getattr(view, '_wv_mod_allowed', False):
            raise ApiError('forbidden',
                           'The mod key is not allowed on this endpoint', 403)

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
