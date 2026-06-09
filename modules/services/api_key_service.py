import hashlib
import re
import secrets
from datetime import datetime, timezone

from modules.db import get_collection
from modules.models.collection_types import Collection

# Read-only scopes a user may grant themselves from the website, with the
# human-friendly label and description shown on the form. Write scopes (write:*)
# stay manual-only and must never be added here. SELF_SERVICE_SCOPES is derived
# from these keys so the allowlist and the UI can never drift apart.
# Descriptions intentionally omit "read" — the section is already labelled
# read-only and only read access is ever granted here.
SELF_SERVICE_SCOPE_DETAILS = {
    "read:market": {
        "label": "Live Trade Market",
        "description": "I need access to current trade market listings and live item prices.",
    },
    "read:market_archive": {
        "label": "Historic Trade Market Archive",
        "description": "I need access to historical market prices and long-term price trends.",
    },
    "read:lootpool": {
        "label": "Lootrun Rewards",
        "description": "I need access to current / historic lootrun rewards.",
    },
    "read:raidpool": {
        "label": "Raid Rewards",
        "description": "I need access to current / historic raid rewards and gambits.",
    },
}

SELF_SERVICE_SCOPES = list(SELF_SERVICE_SCOPE_DETAILS.keys())

# Intentionally loose: only checks for a basic local@domain.tld shape, no DNS
# or deliverability. Accepts edge cases like double-dots (e.g. "a@b..c"); that's
# acceptable for a non-critical sanity check at the API-key boundary.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str | None) -> bool:
    """Loose, good-enough email shape check (no DNS / deliverability)."""
    return bool(email) and bool(_EMAIL_RE.match(email))


def generate_and_store_key(
    owner: str,
    description: str,
    scopes: list[str],
    email: str | None = None,
    discord: str | None = None,
) -> str:
    """Mint a token, store its SHA-256 hash in api_keys, return the raw token.

    `owner` is the project/application name the key is for. Optional `email` and
    `discord` are contact details; each is stored only when provided.

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
    if discord:
        doc["discord"] = discord

    get_collection(Collection.API_KEYS).insert_one(doc)
    return raw_token
