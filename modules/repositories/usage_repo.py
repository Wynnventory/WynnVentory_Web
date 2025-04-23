from threading import Lock
from modules.db import get_collection
from modules.models.collection_types import Collection


class UsageRepository:
    def __init__(self, batch_size: int = 2):
        self.batch_size = batch_size
        self._buffer = {}
        self._owners = {}
        self._lock = Lock()

    def save(self, record: dict):
        key = record["key_hash"]
        owner = record["owner"]
        with self._lock:
            self._owners[key] = owner
            new_count = self._buffer.get(key, 0) + 1
            self._buffer[key] = new_count
            if new_count >= self.batch_size:
                self._flush_key(key)

    def _flush_key(self, key: str):
        """
        Pop the buffered count & owner, then upsert into Mongo.
        """
        count = self._buffer.pop(key, 0)
        owner = self._owners.get(key)
        if count and owner:
            get_collection(Collection.API_USAGE).update_one(
                {"key_hash": key},
                {
                    "$inc": {"count": count},
                    "$setOnInsert": {"owner": owner}
                },
                upsert=True
            )

    def flush_all(self):
        """Persist *all* leftover counts on shutdown."""
        with self._lock:
            for key in list(self._buffer):
                self._flush_key(key)
