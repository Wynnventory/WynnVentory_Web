from typing import List, Any
from .collection_types import Collection

class CollectionRequest:
    """
    A class representing a collection of items to be processed by the queue worker.

    Attributes:
        type (Collection): The type of collection (MARKET, LOOT, RAID, etc.)
        items (List[Any]): A list of items to be processed
    """

    def __init__(self, type: Collection, items: List[Any]):
        """
        Initialize a new CollectionRequest.

        Args:
            type (Collection): The type of collection (MARKET, LOOT, RAID, etc.)
            items (List[Any]): A list of items to be processed
        """
        self.type = type
        self.items = items

    def to_dict(self) -> dict:
        """
        Convert the CollectionRequest to a dictionary.

        Returns:
            dict: A dictionary representation of the CollectionRequest
        """
        return {
            "type": self.type.value if isinstance(self.type, Collection) else self.type,
            "items": self.items
        }

    @staticmethod
    def from_dict(data: dict) -> 'CollectionRequest':
        """
        Create a CollectionRequest from a dictionary.

        Args:
            data (dict): A dictionary containing 'type' and 'items' keys

        Returns:
            CollectionRequest: A new CollectionRequest instance
        """
        type_value = data.get('type')
        # Convert string to Collection enum if it's a string
        if isinstance(type_value, str):
            for collection_type in Collection:
                if collection_type.value == type_value:
                    type_value = collection_type
                    break

        return CollectionRequest(
            type=type_value,
            items=data.get('items', [])
        )
