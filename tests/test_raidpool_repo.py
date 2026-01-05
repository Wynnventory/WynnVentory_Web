import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from modules.repositories.raidpool_repo import save, save_gambits
from tests.test_base import BaseTestCase


class TestRaidpoolRepo(BaseTestCase):
    """Test cases for the raidpool_repo module."""

    def setUp(self):
        """Set up test fixtures before each test."""
        super().setUp()

        # Set up fixed reset times for testing with timezone awareness
        self.previous_reset = datetime(2025, 5, 7, 17, 0, 0, tzinfo=timezone.utc)
        self.next_reset = datetime(2025, 5, 8, 17, 0, 0, tzinfo=timezone.utc)

        # Set up a fixed current time for testing
        self.current_time = datetime(2025, 5, 8, 12, 0, 0, tzinfo=timezone.utc)

        # Create mocks
        self.mock_collection = self.setup_collection_mock('modules.repositories.raidpool_repo')
        self.mock_repo_save = self.create_patch('modules.repositories.raidpool_repo._repo.save')

        self.mock_get_gambit_day = self.create_patch('modules.repositories.raidpool_repo.get_current_gambit_day')
        self.mock_get_gambit_day.return_value = (self.previous_reset, self.next_reset)

        self.mock_datetime = self.setup_datetime_mock(self.current_time, 'modules.repositories.raidpool_repo')
        self.mock_datetime.strptime.return_value = self.current_time

    def create_test_gambit(self, name="Gambit1", timestamp="2025-05-08T12:00:00Z", data="test_data1",
                           player_name="Player1", mod_version="1.0.0"):
        """Create a test gambit with the given parameters."""
        return {
            "playerName": player_name,
            "modVersion": mod_version,
            "name": name,
            "timestamp": timestamp,
            "data": data
        }

    def create_gambit_entry(self, name="Gambit1", timestamp="2025-05-08T12:00:00Z", data="test_data1"):
        """Create a gambit entry for the gambits array."""
        return {
            "name": name,
            "timestamp": timestamp,
            "data": data
        }

    def create_existing_doc(self, gambits=None, timestamp_delta=None, player_name="Player1", mod_version="1.0.0"):
        """Create an existing document with the given parameters."""
        if gambits is None:
            gambits = [
                self.create_gambit_entry("Gambit1", "2025-05-08T11:30:00Z", "test_data1")
            ]

        timestamp = self.current_time
        if timestamp_delta:
            timestamp = self.current_time - timestamp_delta

        return {
            "playerName": player_name,
            "modVersion": mod_version,
            "timestamp": timestamp,
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": gambits
        }

    def create_expected_doc(self, gambits=None, player_name="Player1", mod_version="1.0.0"):
        """Create an expected document with the given parameters."""
        if gambits is None:
            gambits = [
                self.create_gambit_entry("Gambit1", "2025-05-08T12:00:00Z", "test_data1"),
                self.create_gambit_entry("Gambit2", "2025-05-08T12:00:00Z", "test_data2")
            ]

        return {
            "playerName": player_name,
            "modVersion": mod_version,
            "timestamp": self.current_time,
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": gambits
        }

    def create_filter(self):
        """Create a filter for database operations."""
        return {
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day
        }

    def verify_find_one(self):
        """Verify that find_one was called with the correct filter."""
        self.mock_collection.find_one.assert_called_once_with(self.create_filter())

    def verify_delete_one(self):
        """Verify that delete_one was called with the correct filter."""
        self.mock_collection.delete_one.assert_called_once_with(self.create_filter())

    def verify_insert_one(self, expected_doc):
        """Verify that insert_one was called with the correct document."""
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)

    def test_save(self):
        """Test the save function."""
        # Create a test pool
        test_pool = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}],
            "timestamp": "2025-05-08T12:00:00Z"
        }

        # Call the save function
        save(test_pool)

        # Verify _repo.save was called with the correct argument
        self.mock_repo_save.assert_called_once_with(test_pool)

    def test_save_gambits_new(self):
        """Test saving new gambits (no existing document)."""
        # Set up the mock collection to return None (no existing document)
        self.mock_collection.find_one.return_value = None

        # Create test gambits
        test_gambits = [
            self.create_test_gambit("Gambit1", data="test_data1"),
            self.create_test_gambit("Gambit2", data="test_data2")
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify database operations
        self.verify_find_one()
        self.verify_insert_one(self.create_expected_doc())
        self.mock_collection.delete_one.assert_not_called()

    def test_save_gambits_replace_more(self):
        """Test replacing existing gambits when the new ones have more items."""
        # Set up the mock collection to return an existing document with fewer items
        existing_gambits = [self.create_gambit_entry("Gambit1", "2025-05-08 11:30:00", "test_data1")]
        self.mock_collection.find_one.return_value = self.create_existing_doc(
            gambits=existing_gambits,
            timestamp_delta=timedelta(minutes=30)
        )

        # Create test gambits with more items
        test_gambits = [
            self.create_test_gambit("Gambit1", data="test_data1"),
            self.create_test_gambit("Gambit2", data="test_data2")
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify database operations
        self.verify_find_one()
        self.verify_delete_one()
        self.verify_insert_one(self.create_expected_doc())

    def test_save_gambits_replace_stale(self):
        """Test replacing existing gambits when they are stale (>1 hour old)."""
        # Set up the mock collection to return an existing document that's over 1 hour old
        existing_gambits = [
            self.create_gambit_entry("Gambit1", "2025-05-08 10:00:00", "test_data1"),
            self.create_gambit_entry("Gambit2", "2025-05-08 10:00:00", "test_data2")
        ]
        self.mock_collection.find_one.return_value = self.create_existing_doc(
            gambits=existing_gambits,
            timestamp_delta=timedelta(hours=2)
        )

        # Create test gambits with the same number of items but updated data
        test_gambits = [
            self.create_test_gambit("Gambit1", data="test_data1_updated"),
            self.create_test_gambit("Gambit2", data="test_data2_updated")
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify database operations
        self.verify_find_one()
        self.verify_delete_one()

        # Create expected document with updated gambits
        expected_gambits = [
            self.create_gambit_entry("Gambit1", data="test_data1_updated"),
            self.create_gambit_entry("Gambit2", data="test_data2_updated")
        ]
        self.verify_insert_one(self.create_expected_doc(gambits=expected_gambits))

    def test_save_gambits_skip_insertion(self):
        """Test skipping insertion when the existing document is newer and has more items."""
        # Set up the mock collection to return a recent existing document with more items
        existing_gambits = [
            self.create_gambit_entry("Gambit1", "2025-05-08 11:30:00", "test_data1"),
            self.create_gambit_entry("Gambit2", "2025-05-08 11:30:00", "test_data2"),
            self.create_gambit_entry("Gambit3", "2025-05-08 11:30:00", "test_data3")
        ]
        self.mock_collection.find_one.return_value = self.create_existing_doc(
            gambits=existing_gambits,
            timestamp_delta=timedelta(minutes=30)
        )

        # Create test gambits with fewer items
        test_gambits = [
            self.create_test_gambit("Gambit1", data="test_data1_updated"),
            self.create_test_gambit("Gambit2", data="test_data2_updated")
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify database operations
        self.verify_find_one()
        self.mock_collection.delete_one.assert_not_called()
        self.mock_collection.insert_one.assert_not_called()

    def test_save_gambits_invalid_time(self):
        """Test that gambits with an invalid timestamp are not saved."""
        # Create test gambits with a timestamp outside the current gambit day
        test_gambits = [
            self.create_test_gambit("Gambit1", timestamp="2025-05-06T12:00:00Z", data="test_data1")
            # Before the previous reset
        ]

        # Create a patch for the get_collection function
        with patch('modules.repositories.raidpool_repo.get_collection') as mock_get_collection:
            # Create a mock collection
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection

            # Create a patch for the get_current_gambit_day function
            with patch('modules.repositories.raidpool_repo.get_current_gambit_day') as mock_get_gambit_day:
                # Set up fixed reset times for testing
                previous_reset = datetime(2025, 5, 7, 17, 0, 0, tzinfo=timezone.utc)
                next_reset = datetime(2025, 5, 8, 17, 0, 0, tzinfo=timezone.utc)
                mock_get_gambit_day.return_value = (previous_reset, next_reset)

                # Create a patch for the datetime.strptime function
                with patch('modules.repositories.raidpool_repo.datetime') as mock_datetime:
                    # Mock the datetime.strptime to return a time before the previous reset
                    invalid_time = datetime(2025, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
                    mock_datetime.strptime.return_value = invalid_time
                    mock_datetime.now.return_value = datetime(2025, 5, 8, 12, 0, 0, tzinfo=timezone.utc)

                    # Call the save_gambits function
                    save_gambits(test_gambits)

                    # Verify that find_one was NOT called because the timestamp was invalid
                    # and the function returned early.
                    mock_collection.find_one.assert_not_called()

                    # Verify the collection.insert_one was not called
                    mock_collection.insert_one.assert_not_called()

    def test_save_gambits_mixed_timestamps(self):
        """Test saving gambits where some have invalid timestamps."""
        # Set up the mock collection to return None (no existing document)
        self.mock_collection.find_one.return_value = None

        # Create test gambits: 3 valid, 1 old (from last raid week)
        valid_ts = "2025-05-08T12:00:00Z"
        old_ts = "2025-05-01T12:00:00Z"  # Last raid week (before May 2nd reset)

        test_gambits = [
            self.create_test_gambit("Gambit1", timestamp=valid_ts),
            self.create_test_gambit("Gambit2", timestamp=valid_ts),
            self.create_test_gambit("Gambit3", timestamp=old_ts),
            self.create_test_gambit("Gambit4", timestamp=valid_ts)
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify database operations
        self.verify_find_one()

        # The expected document should only contain the 3 valid gambits
        expected_gambits = [
            self.create_gambit_entry("Gambit1", valid_ts),
            self.create_gambit_entry("Gambit2", valid_ts),
            self.create_gambit_entry("Gambit4", valid_ts)
        ]
        self.verify_insert_one(self.create_expected_doc(gambits=expected_gambits))


if __name__ == "__main__":
    unittest.main()
