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
def save_trade_market_item(item):
    collection = db["trademarket_TEST"]
    
    # Extract relevant fields to check for duplicates (excluding timestamp)
    item_check = {
        "name": item.get("name"),
        "level": item.get("level"),
        "rarity": item.get("rarity"),
        "powder_slots": item.get("powder_slots"),
        "rerolls": item.get("rerolls"),
        # "required_class": item.get("required_class"),
        "unidentified": item.get("unidentified"),
        "shiny_stat": item.get("shiny_stat"),
        # "perfect": item.get("perfect"),
        # "defective": item.get("defective"),
        "amount": item.get("amount"),
        "overall_percentage": item.get("overall_percentage"),
        "listing_price": item.get("listing_price"),
        "actual_stats_with_percentage": item.get("actual_stats_with_percentage")
    }

    # Check for duplicate items
    duplicate_item = collection.find_one(item_check)

    if duplicate_item:
        return {"message": "Duplicate item found, skipping insertion"}, 200
    
    # Insert the new item if no duplicate is found
    item['timestamp'] = datetime.utcnow()
    collection.insert_one(item)
    return {"message": "Item saved successfully"}, 200