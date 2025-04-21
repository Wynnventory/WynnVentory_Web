import base64
import secrets
import hashlib
from datetime import datetime, timezone

from modules.db import get_collection
from modules.models.collection_types import Collection

# #######################
# # API PARAMS
# #######################
OWNER = "name"
DESCRIPTION = "description"
SCOPES = [
    "read:lootpool",
    # "write:lootpool",
    "read:raidpool",
    # "write:raidpool",
    "read:market",
    # "write:market",
    # "read:market_archive",
    # "write:market_archive"
]

coll = get_collection(Collection.API_KEYS)


def generate_and_store_key(owner: str, description: str, scopes: list[str]) -> str:
    raw_token = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    coll.insert_one({
        "key_hash": key_hash,
        "owner": owner,
        "description": description,
        "scopes": scopes,
        "created_at": datetime.now(timezone.utc),
        "revoked": False
    })
    return raw_token


def obfuscate_key(raw_key: str) -> str:
    mask = 0x5A
    b = raw_key.encode("utf-8")
    ob = bytes(byte ^ mask for byte in b)
    return base64.b64encode(ob).decode("utf-8")


if __name__ == "__main__":
    token = generate_and_store_key(OWNER, DESCRIPTION, SCOPES)
    print("\n=== NEW API KEY ===")
    print(f"Token:      {token}")
    print(f"Obfuscated: {obfuscate_key(token)}")
    print("===================\n")
