from threading import Lock
from modules.db import get_collection
from modules.models.collection_types import Collection


class UsageRepository:
    def __init__(self, batch_size: int = 2):
        self.coll = get_collection(Collection.API_USAGE)
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
        count = self._buffer.pop(key, 0)
        owner = self._owners.get(key)
        print(f"FLUSHING KEY → owner={owner!r}, count={count}, target={self.coll.database.name}.{self.coll.name}")
        if not (count and owner):
            print("  → nothing to do")
            return

        try:
            result = self.coll.update_one(
                {"key_hash": key},
                {"$inc": {"count": count}, "$setOnInsert": {"owner": owner}},
                upsert=True
            )
            print("  → raw_result:", result.raw_result)
        except Exception as e:
            print("  !!! write exception during flush:", repr(e))

    def flush_all(self):
        """Persist *all* leftover counts on shutdown."""
        print("I AM BEING FLUSHED")
        with self._lock:
            for key in list(self._buffer):
                self._flush_key(key)
