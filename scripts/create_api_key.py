import base64

from modules.services.api_key_service import generate_and_store_key

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
    "read:market_archive",
    # "write:market_archive"
]


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
