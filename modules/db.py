from pymongo.mongo_client import MongoClient
from pymongo.server_api    import ServerApi
import logging

from modules.config import Config
from modules.models.collection_types import Collection as Coll

logger = logging.getLogger(__name__)

def get_client(role: str = "current") -> MongoClient:
    if role == "admin":
        uri = Config.ADMIN_URI
    else:
        uri = Config.get_current_uri()
    logger.debug(f"[get_client] role={role} → URI={uri}")
    return MongoClient(uri, server_api=ServerApi("1"), tls=True, tlsAllowInvalidCertificates=True)

def get_collection(collection: Coll):
    # decide which client to use
    role = "admin" if collection in (Coll.API_KEYS, Coll.API_USAGE) else "current"
    client = get_client(role)
    # get_default_database() honors the DB in the URI string
    db = client.get_default_database()
    logger.debug(f"[get_collection] collection={collection.value} → using DB={db.name}")
    return db[collection._value_]
