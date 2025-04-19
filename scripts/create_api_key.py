import secrets
import hashlib
from datetime import datetime, timezone

from modules.db import get_collection
from modules.models.collection_types import Collection

# #######################
# # API PARAMS
# #######################
OWNER = "MagBot"

coll = get_collection(Collection.API_KEYS)


def generate_and_store_key(owner: str) -> str:
    raw_token = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    coll.insert_one({
        "key_hash": key_hash,
        "owner": owner,
        "created_at": datetime.now(timezone.utc),
        "revoked": False
    })
    return raw_token


if __name__ == "__main__":
    token = generate_and_store_key(OWNER)
    print("\n=== NEW API KEY ===")
    print(token)
    print("===================\n")
