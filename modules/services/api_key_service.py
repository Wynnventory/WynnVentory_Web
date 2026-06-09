import hashlib
import re
import secrets
from datetime import datetime, timezone

from modules.db import get_collection
from modules.models.collection_types import Collection

# Read-only scopes a user may grant themselves from the website.
# Write scopes (write:*) stay manual-only and must never be added here.
SELF_SERVICE_SCOPES = [
    "read:market",
    "read:market_archive",
    "read:lootpool",
    "read:raidpool",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Loose, good-enough email shape check (no DNS / deliverability)."""
    return bool(email) and bool(_EMAIL_RE.match(email))


def generate_and_store_key(
    owner: str,
    description: str,
    scopes: list[str],
    email: str | None = None,
) -> str:
    """Mint a token, store its SHA-256 hash in api_keys, return the raw token.

    Single source of truth for both the manual script and the web route.
    The api_keys collection lives in the admin DB (see modules/db.get_collection).
    """
    raw_token = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    doc = {
        "key_hash": key_hash,
        "owner": owner,
        "description": description,
        "scopes": scopes,
        "created_at": datetime.now(timezone.utc),
        "revoked": False,
    }
    if email:
        doc["email"] = email

    get_collection(Collection.API_KEYS).insert_one(doc)
    return raw_token
