# shared/db.py
import os
from pymongo import MongoClient
import mongomock
from dotenv import load_dotenv

load_dotenv()
print("USE_MOCK_DB =", os.getenv("USE_MOCK_DB"))
print("MONGO_URI =", os.getenv("MONGO_URI"))

DB_NAME = os.getenv("DB_NAME", "water_quality_data")
COLL_NAME = os.getenv("COLL_NAME", "asv_1")
USE_MOCK = os.getenv("USE_MOCK_DB", "True").lower() == "true"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

_client = None

def _client_instance():
    global _client
    if _client is None:
        if USE_MOCK:
            print("Using mongomock (in-memory database)...")
            _client = mongomock.MongoClient()
        else:
            print(f"Connecting to MongoDB at {MONGO_URI}...")
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command("ping")  # force connection
    return _client

def get_collection():
    db = _client_instance()[DB_NAME]
    coll = db[COLL_NAME]
    coll.create_index("timestamp")
    return coll
