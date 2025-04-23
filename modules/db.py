from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from modules.config import Config
from modules.models.collection_types import Collection

# Global client instances for connection pooling
_admin_client = None
_current_client = None

def get_client(db: str = "current") -> MongoClient:
    """
    Returns a MongoClient pointed at:
     - the current ENVIRONMENT db (if db="current")
     - the admin db              (if db="admin")

    Uses connection pooling to reuse existing connections.
    """
    global _admin_client, _current_client

    if db == "admin":
        if _admin_client is None:
            _admin_client = MongoClient(
                Config.ADMIN_URI,
                server_api=ServerApi("1"),
                tls=True,
                tlsAllowInvalidCertificates=True,
                maxPoolSize=50  # Adjust based on expected concurrent connections
            )
        return _admin_client
    else:
        if _current_client is None:
            _current_client = MongoClient(
                Config.get_current_uri(),
                server_api=ServerApi("1"),
                tls=True,
                tlsAllowInvalidCertificates=True,
                maxPoolSize=50  # Adjust based on expected concurrent connections
            )
        return _current_client


def get_collection(collection: Collection):
    client = get_client("admin" if collection in (Collection.API_KEYS, Collection.API_USAGE) else "current")
    db = client.get_default_database()
    return db[collection._value_]
