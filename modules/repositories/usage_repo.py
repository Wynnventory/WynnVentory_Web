from threading import Lock
from typing import Dict, List, Any

from modules.db import get_collection
from modules.models.collection_types import Collection


class UsageRepository:
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self._buffer = {}
        self._owners = {}
        self._lock = Lock()

    def save(self, records: List[Dict[str, Any]]) -> None:
        """
        Process a list of records: update owner and buffer counts,
        flushing any key whose count reaches batch_size.
        """
        with self._lock:
            for record in records:
                key = record["key_hash"]
                owner = record["owner"]

                # Update owner mapping
                self._owners[key] = owner

                # Increment buffer count
                new_count = self._buffer.get(key, 0) + 1
                self._buffer[key] = new_count

                # Flush if we've reached the batch size
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
