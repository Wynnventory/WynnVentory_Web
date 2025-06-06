import unittest
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, call

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.repositories.base_pool_repo import BasePoolRepo
from modules.models.collection_types import Collection


class TestBasePoolRepo(unittest.TestCase):
    """Test cases for the BasePoolRepo class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create a BasePoolRepo instance for testing
        self.repo = BasePoolRepo(Collection.LOOT)
        
        # Create a patch for the get_collection function
        self.get_collection_patch = patch('modules.repositories.base_pool_repo.get_collection')
        self.mock_get_collection = self.get_collection_patch.start()
        
        # Create a mock collection
        self.mock_collection = MagicMock()
        self.mock_get_collection.return_value = self.mock_collection
        
        # Create a patch for the get_lootpool_week_for_timestamp function
        self.get_week_patch = patch('modules.repositories.base_pool_repo.get_lootpool_week_for_timestamp')
        self.mock_get_week = self.get_week_patch.start()
        self.mock_get_week.return_value = (2025, 18)  # Example year and week
        
        # Set up a fixed current time for testing
        self.current_time = datetime(2025, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
        self.datetime_patch = patch('modules.repositories.base_pool_repo.datetime')
        self.mock_datetime = self.datetime_patch.start()
        self.mock_datetime.now.return_value = self.current_time
        self.mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        self.get_collection_patch.stop()
        self.get_week_patch.stop()
        self.datetime_patch.stop()

    def test_save_new_pool(self):
        """Test saving a new pool (no existing document)."""
        # Set up the mock collection to return None (no existing document)
        self.mock_collection.find_one.return_value = None
        
        # Create a test pool
        test_pool = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": "2025-05-05 12:00:00"
        }
        
        # Call the save method
        self.repo.save([test_pool])
        
        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {'region': 'US', 'week': 18, 'year': 2025}
        )
        
        # Verify the collection.insert_one was called with the correct document
        expected_doc = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": self.current_time,
            "week": 18,
            "year": 2025
        }
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)
        
        # Verify the collection.delete_one was not called
        self.mock_collection.delete_one.assert_not_called()

    def test_save_replace_more_items(self):
        """Test saving a pool with more items than the existing one."""
        # Set up the mock collection to return an existing document
        existing_doc = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}],
            "timestamp": self.current_time - timedelta(minutes=30),
            "week": 18,
            "year": 2025
        }
        self.mock_collection.find_one.return_value = existing_doc
        
        # Create a test pool with more items
        test_pool = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": "2025-05-05 12:00:00"
        }
        
        # Call the save method
        self.repo.save([test_pool])
        
        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {'region': 'US', 'week': 18, 'year': 2025}
        )
        
        # Verify the collection.delete_one was called with the correct filter
        self.mock_collection.delete_one.assert_called_once_with(
            {'region': 'US', 'week': 18, 'year': 2025}
        )
        
        # Verify the collection.insert_one was called with the correct document
        expected_doc = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": self.current_time,
            "week": 18,
            "year": 2025
        }
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)

    def test_save_replace_stale(self):
        """Test saving a pool when the existing one is stale (>1 hour old)."""
        # Set up the mock collection to return an existing document that's over 1 hour old
        existing_doc = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": self.current_time - timedelta(hours=2),
            "week": 18,
            "year": 2025
        }
        self.mock_collection.find_one.return_value = existing_doc
        
        # Create a test pool with the same number of items
        test_pool = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": "2025-05-05 12:00:00"
        }
        
        # Call the save method
        self.repo.save([test_pool])
        
        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {'region': 'US', 'week': 18, 'year': 2025}
        )
        
        # Verify the collection.delete_one was called with the correct filter
        self.mock_collection.delete_one.assert_called_once_with(
            {'region': 'US', 'week': 18, 'year': 2025}
        )
        
        # Verify the collection.insert_one was called with the correct document
        expected_doc = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": self.current_time,
            "week": 18,
            "year": 2025
        }
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)


    def test_save_skip_insertion(self):
        """Test skipping insertion when the existing document is newer and has more items."""
        # Set up the mock collection to return a recent existing document with more items
        existing_doc = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}, {"name": "Item3", "amount": 3}],
            "timestamp": self.current_time - timedelta(minutes=30),
            "week": 18,
            "year": 2025
        }
        self.mock_collection.find_one.return_value = existing_doc
        
        # Create a test pool with fewer items
        test_pool = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}],
            "timestamp": "2025-05-05 12:00:00"
        }
        
        # Call the save method
        self.repo.save([test_pool])
        
        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {'region': 'US', 'week': 18, 'year': 2025}
        )
        
        # Verify the collection.delete_one and insert_one were not called
        self.mock_collection.delete_one.assert_not_called()
        self.mock_collection.insert_one.assert_not_called()

    def test_save_multiple_pools(self):
        """Test saving multiple pools."""
        # Set up the mock collection to return None for all find_one calls
        self.mock_collection.find_one.return_value = None
        
        # Create test pools
        test_pools = [
            {
                "region": "US",
                "items": [{"name": "Item1", "amount": 1}],
                "timestamp": "2025-05-05 12:00:00"
            },
            {
                "region": "EU",
                "items": [{"name": "Item2", "amount": 2}],
                "timestamp": "2025-05-05 12:00:00"
            }
        ]
        
        # Call the save method
        self.repo.save(test_pools)
        
        # Verify the collection.find_one was called twice with the correct filters
        self.mock_collection.find_one.assert_has_calls([
            call({'region': 'US', 'week': 18, 'year': 2025}),
            call({'region': 'EU', 'week': 18, 'year': 2025})
        ])
        
        # Verify the collection.insert_one was called twice with the correct documents
        expected_docs = [
            {
                "region": "US",
                "items": [{"name": "Item1", "amount": 1}],
                "timestamp": self.current_time,
                "week": 18,
                "year": 2025
            },
            {
                "region": "EU",
                "items": [{"name": "Item2", "amount": 2}],
                "timestamp": self.current_time,
                "week": 18,
                "year": 2025
            }
        ]
        self.mock_collection.insert_one.assert_has_calls([
            call(expected_docs[0]),
            call(expected_docs[1])
        ])


if __name__ == "__main__":
    unittest.main()