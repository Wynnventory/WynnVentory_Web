from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from modules.config import Config
from modules.models.collection_types import Collection


def get_client(db: str = "current") -> MongoClient:
    """
    Returns a MongoClient pointed at:
     - the current ENVIRONMENT db (if db="current")
     - the admin db              (if db="admin")
    """
    if db == "admin":
        uri = Config.ADMIN_URI
    else:
        uri = Config.get_current_uri()

    return MongoClient(
        uri,
        server_api=ServerApi("1"),
        tls=True,
        tlsAllowInvalidCertificates=True
    )

def get_collection(collection: Collection):
    client = get_client("admin" if collection is Collection.API_KEYS else "current")
    db     = client.get_default_database()
    return db[collection._value_]