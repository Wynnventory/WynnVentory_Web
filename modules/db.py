import logging

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from modules.config import Config
from modules.models.collection_types import Collection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_client():
    uri = Config.get_current_uri()
    return MongoClient(uri, server_api=ServerApi('1'), tls=True, tlsAllowInvalidCertificates=True)

def get_collection(collection: Collection):
    client = get_client()
    db = client["wynnventory" if Config.ENVIRONMENT == "prod" else "wynnventory_DEV"]
    
    if not isinstance(collection, Collection):
        return None
        
    return db[collection.value]
