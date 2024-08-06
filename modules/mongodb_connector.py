from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://Test1234:Test1234@wynnventory.9axarep.mongodb.net/?retryWrites=true&w=majority&appName=wynnventory"

# Create a new client and connect to the server with SSL settings
client = MongoClient(uri, server_api=ServerApi('1'), tls=True, tlsAllowInvalidCertificates=True)
db = client["wynnventory"]

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print("Could not connect to MongoDB!", e)

# Save items to the trademarket collection
def save_trade_market_items(items):
    collection = db["trademarket_TEST"]
    for item in items.values():
        item['timestamp'] = datetime.utcnow()
        collection.insert_one(item)
    return {"message": "Items saved successfully"}, 200