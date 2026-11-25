"""MongoDB connections for standalone exercises that reset or restore sample data."""
import os
from uuid import uuid4

from pymongo import MongoClient

from backend.config.connection import banner

_client = None


def get_client():
    global _client
    if _client is None:
        uri = os.getenv("MONGO_LABS_URI")
        if not uri:
            raise RuntimeError("Set MONGO_LABS_URI to a disposable MongoDB lab server.")
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000, timeoutMS=30000)
    return _client


def get_db(name):
    return get_client()[name]


def reset_collection(database, name):
    # Each run owns its fixture collection and can safely rerun after an interruption.
    return get_db(database)[f"{name}_{uuid4().hex}"]
