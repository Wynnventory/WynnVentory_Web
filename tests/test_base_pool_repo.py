import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import call

from modules.models.collection_types import Collection
from modules.repositories.base_pool_repo import BasePoolRepo
from tests.test_base import BaseTestCase


class TestBasePoolRepo(BaseTestCase):
    """Test cases for the BasePoolRepo class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Create a BasePoolRepo instance for testing
        self.repo = BasePoolRepo(Collection.LOOT)

        # Set up a fixed current time for testing
        self.current_time = datetime(2025, 5, 5, 12, 0, 0, tzinfo=timezone.utc)

        # Create mocks
        self.mock_collection = self.setup_collection_mock('modules.repositories.base_pool_repo')
        self.mock_get_week = self.create_patch('modules.repositories.base_pool_repo.get_lootpool_week_for_timestamp')
        self.mock_get_week.return_value = (2025, 18)  # Example year and week

        self.mock_datetime = self.setup_datetime_mock(self.current_time, 'modules.repositories.base_pool_repo')

    def create_test_pool(self, region="US", items=None, timestamp=None):
        """Create a test pool with the given parameters."""
        if items is None:
            items = [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}]
        if timestamp is None:
            timestamp = "2025-05-05T12:00:00Z"

        return {
            "region": region,
            "items": items,
            "timestamp": timestamp
        }

    def create_existing_doc(self, region="US", items=None, timestamp_delta=None, week=18, year=2025):
        """Create an existing document with the given parameters."""
        if items is None:
            items = [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}]

        timestamp = self.current_time
        if timestamp_delta:
            timestamp = self.current_time - timestamp_delta

        return {
            "region": region,
            "items": items,
            "timestamp": timestamp,
            "week": week,
            "year": year
        }

    def create_expected_doc(self, region="US", items=None, week=18, year=2025):
        """Create an expected document with the given parameters."""
        if items is None:
            items = [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2}]

        return {
            "region": region,
            "items": items,
            "timestamp": self.current_time,
            "week": week,
            "year": year
        }

    def create_filter(self, region="US", week=18, year=2025):
        """Create a filter for database operations."""
        return {'region': region, 'week': week, 'year': year}

    def verify_find_one(self, region="US", week=18, year=2025):
        """Verify that find_one was called with the correct filter."""
        self.mock_collection.find_one.assert_called_once_with(
            self.create_filter(region, week, year)
        )

    def verify_delete_one(self, region="US", week=18, year=2025):
        """Verify that delete_one was called with the correct filter."""
        self.mock_collection.delete_one.assert_called_once_with(
            self.create_filter(region, week, year)
        )

    def verify_insert_one(self, expected_doc):
        """Verify that insert_one was called with the correct document."""
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)

    def test_save_new_pool(self):
        """Test saving a new pool (no existing document)."""
        # Set up the mock collection to return None (no existing document)
        self.mock_collection.find_one.return_value = None

        # Create a test pool and save it
        test_pool = self.create_test_pool()
        self.repo.save([test_pool])

        # Verify database operations
        self.verify_find_one()
        self.verify_insert_one(self.create_expected_doc())
        self.mock_collection.delete_one.assert_not_called()

    def test_save_replace_more_items(self):
        """Test saving a pool with more items than the existing one."""
        # Set up the mock collection to return an existing document with fewer items
        existing_items = [{"name": "Item1", "amount": 1}]
        self.mock_collection.find_one.return_value = self.create_existing_doc(
            items=existing_items,
            timestamp_delta=timedelta(minutes=30)
        )

        # Create a test pool with more items and save it
        test_pool = self.create_test_pool()
        self.repo.save([test_pool])

        # Verify database operations
        self.verify_find_one()
        self.verify_delete_one()
        self.verify_insert_one(self.create_expected_doc())

    def test_save_replace_stale(self):
        """Test saving a pool when the existing one is stale (>1 hour old)."""
        # Set up the mock collection to return an existing document that's over 1 hour old
        self.mock_collection.find_one.return_value = self.create_existing_doc(
            timestamp_delta=timedelta(hours=2)
        )

        # Create a test pool with the same number of items and save it
        test_pool = self.create_test_pool()
        self.repo.save([test_pool])

        # Verify database operations
        self.verify_find_one()
        self.verify_delete_one()
        self.verify_insert_one(self.create_expected_doc())

    def test_save_skip_insertion(self):
        """Test skipping insertion when the existing document is newer and has more items."""
        # Set up the mock collection to return a recent existing document with more items
        existing_items = [{"name": "Item1", "amount": 1}, {"name": "Item2", "amount": 2},
                          {"name": "Item3", "amount": 3}]
        self.mock_collection.find_one.return_value = self.create_existing_doc(
            items=existing_items,
            timestamp_delta=timedelta(minutes=30)
        )

        # Create a test pool with fewer items and save it
        test_pool = self.create_test_pool()
        self.repo.save([test_pool])

        # Verify database operations
        self.verify_find_one()
        self.mock_collection.delete_one.assert_not_called()
        self.mock_collection.insert_one.assert_not_called()

    def test_save_multiple_pools(self):
        """Test saving multiple pools."""
        # Set up the mock collection to return None for all find_one calls
        self.mock_collection.find_one.return_value = None

        # Create test pools with different regions and items
        us_items = [{"name": "Item1", "amount": 1}]
        eu_items = [{"name": "Item2", "amount": 2}]

        test_pools = [
            self.create_test_pool(region="US", items=us_items),
            self.create_test_pool(region="EU", items=eu_items)
        ]

        # Call the save method
        self.repo.save(test_pools)

        # Verify the collection.find_one was called twice with the correct filters
        self.mock_collection.find_one.assert_has_calls([
            call(self.create_filter(region="US")),
            call(self.create_filter(region="EU"))
        ])

        # Verify the collection.insert_one was called twice with the correct documents
        expected_docs = [
            self.create_expected_doc(region="US", items=us_items),
            self.create_expected_doc(region="EU", items=eu_items)
        ]

        self.mock_collection.insert_one.assert_has_calls([
            call(expected_docs[0]),
            call(expected_docs[1])
        ])


if __name__ == "__main__":
    unittest.main()
