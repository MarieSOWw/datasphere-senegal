import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "banking_senegal")

COLLECTION_BANKING = "banques_senegal"
COLLECTION_ASSURANCE = "assurance_data"
COLLECTION_ENERGIE = "energie_data"
COLLECTION_SANTE = "sante_data"
DEFAULT_COLLECTION = COLLECTION_BANKING


def get_collection(collection_name: str = DEFAULT_COLLECTION):
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    db = client[DB_NAME]
    return db[collection_name], client


def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    return client[DB_NAME], client


def ping():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False