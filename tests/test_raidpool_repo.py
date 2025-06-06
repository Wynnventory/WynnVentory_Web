import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.repositories.raidpool_repo import save, save_gambits


class TestRaidpoolRepo(unittest.TestCase):
    """Test cases for the raidpool_repo module."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create a patch for the get_collection function
        self.get_collection_patch = patch('modules.repositories.raidpool_repo.get_collection')
        self.mock_get_collection = self.get_collection_patch.start()

        # Create a mock collection
        self.mock_collection = MagicMock()
        self.mock_get_collection.return_value = self.mock_collection

        # Create a patch for the _repo.save method
        self.repo_save_patch = patch('modules.repositories.raidpool_repo._repo.save')
        self.mock_repo_save = self.repo_save_patch.start()

        # Create a patch for the get_current_gambit_day function
        self.get_gambit_day_patch = patch('modules.repositories.raidpool_repo.get_current_gambit_day')
        self.mock_get_gambit_day = self.get_gambit_day_patch.start()

        # Set up fixed reset times for testing with timezone awareness
        self.previous_reset = datetime(2025, 5, 7, 17, 0, 0, tzinfo=timezone.utc)
        self.next_reset = datetime(2025, 5, 8, 17, 0, 0, tzinfo=timezone.utc)
        self.mock_get_gambit_day.return_value = (self.previous_reset, self.next_reset)

        # Set up a fixed current time for testing
        self.current_time = datetime(2025, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        self.datetime_patch = patch('modules.repositories.raidpool_repo.datetime')
        self.mock_datetime = self.datetime_patch.start()
        self.mock_datetime.now.return_value = self.current_time
        self.mock_datetime.strptime.return_value = self.current_time

    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        self.get_collection_patch.stop()
        self.repo_save_patch.stop()
        self.get_gambit_day_patch.stop()
        self.datetime_patch.stop()

    def test_save(self):
        """Test the save function."""
        # Create a test pool
        test_pool = {
            "region": "US",
            "items": [{"name": "Item1", "amount": 1}],
            "timestamp": "2025-05-08 12:00:00"
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
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit1",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data1"
            },
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit2",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data2"
            }
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {"year": self.next_reset.year, "month": self.next_reset.month, "day": self.next_reset.day}
        )

        # Verify the collection.insert_one was called with the correct document
        expected_doc = {
            "playerName": "Player1",
            "modVersion": "1.0.0",
            "timestamp": self.current_time,
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": [
                {
                    "name": "Gambit1",
                    "timestamp": "2025-05-08 12:00:00",
                    "data": "test_data1"
                },
                {
                    "name": "Gambit2",
                    "timestamp": "2025-05-08 12:00:00",
                    "data": "test_data2"
                }
            ]
        }
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)

        # Verify the collection.delete_one was not called
        self.mock_collection.delete_one.assert_not_called()

    def test_save_gambits_replace_more(self):
        """Test replacing existing gambits when the new ones have more items."""
        # Set up the mock collection to return an existing document
        existing_doc = {
            "playerName": "Player1",
            "modVersion": "1.0.0",
            "timestamp": self.current_time - timedelta(minutes=30),
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": [
                {
                    "name": "Gambit1",
                    "timestamp": "2025-05-08 11:30:00",
                    "data": "test_data1"
                }
            ]
        }
        self.mock_collection.find_one.return_value = existing_doc

        # Create test gambits with more items
        test_gambits = [
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit1",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data1"
            },
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit2",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data2"
            }
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {"year": self.next_reset.year, "month": self.next_reset.month, "day": self.next_reset.day}
        )

        # Verify the collection.delete_one was called with the correct filter
        self.mock_collection.delete_one.assert_called_once_with(
            {"year": self.next_reset.year, "month": self.next_reset.month, "day": self.next_reset.day}
        )

        # Verify the collection.insert_one was called with the correct document
        expected_doc = {
            "playerName": "Player1",
            "modVersion": "1.0.0",
            "timestamp": self.current_time,
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": [
                {
                    "name": "Gambit1",
                    "timestamp": "2025-05-08 12:00:00",
                    "data": "test_data1"
                },
                {
                    "name": "Gambit2",
                    "timestamp": "2025-05-08 12:00:00",
                    "data": "test_data2"
                }
            ]
        }
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)

    def test_save_gambits_replace_stale(self):
        """Test replacing existing gambits when they are stale (>1 hour old)."""
        # Set up the mock collection to return an existing document that's over 1 hour old
        existing_doc = {
            "playerName": "Player1",
            "modVersion": "1.0.0",
            "timestamp": self.current_time - timedelta(hours=2),
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": [
                {
                    "name": "Gambit1",
                    "timestamp": "2025-05-08 10:00:00",
                    "data": "test_data1"
                },
                {
                    "name": "Gambit2",
                    "timestamp": "2025-05-08 10:00:00",
                    "data": "test_data2"
                }
            ]
        }
        self.mock_collection.find_one.return_value = existing_doc

        # Create test gambits with the same number of items
        test_gambits = [
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit1",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data1_updated"
            },
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit2",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data2_updated"
            }
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {"year": self.next_reset.year, "month": self.next_reset.month, "day": self.next_reset.day}
        )

        # Verify the collection.delete_one was called with the correct filter
        self.mock_collection.delete_one.assert_called_once_with(
            {"year": self.next_reset.year, "month": self.next_reset.month, "day": self.next_reset.day}
        )

        # Verify the collection.insert_one was called with the correct document
        expected_doc = {
            "playerName": "Player1",
            "modVersion": "1.0.0",
            "timestamp": self.current_time,
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": [
                {
                    "name": "Gambit1",
                    "timestamp": "2025-05-08 12:00:00",
                    "data": "test_data1_updated"
                },
                {
                    "name": "Gambit2",
                    "timestamp": "2025-05-08 12:00:00",
                    "data": "test_data2_updated"
                }
            ]
        }
        self.mock_collection.insert_one.assert_called_once_with(expected_doc)

    def test_save_gambits_skip_insertion(self):
        """Test skipping insertion when the existing document is newer and has more items."""
        # Set up the mock collection to return a recent existing document with more items
        existing_doc = {
            "playerName": "Player1",
            "modVersion": "1.0.0",
            "timestamp": self.current_time - timedelta(minutes=30),
            "year": self.next_reset.year,
            "month": self.next_reset.month,
            "day": self.next_reset.day,
            "gambits": [
                {
                    "name": "Gambit1",
                    "timestamp": "2025-05-08 11:30:00",
                    "data": "test_data1"
                },
                {
                    "name": "Gambit2",
                    "timestamp": "2025-05-08 11:30:00",
                    "data": "test_data2"
                },
                {
                    "name": "Gambit3",
                    "timestamp": "2025-05-08 11:30:00",
                    "data": "test_data3"
                }
            ]
        }
        self.mock_collection.find_one.return_value = existing_doc

        # Create test gambits with fewer items
        test_gambits = [
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit1",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data1_updated"
            },
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit2",
                "timestamp": "2025-05-08 12:00:00",
                "data": "test_data2_updated"
            }
        ]

        # Call the save_gambits function
        save_gambits(test_gambits)

        # Verify the collection.find_one was called with the correct filter
        self.mock_collection.find_one.assert_called_once_with(
            {"year": self.next_reset.year, "month": self.next_reset.month, "day": self.next_reset.day}
        )

        # Verify the collection.delete_one and insert_one were not called
        self.mock_collection.delete_one.assert_not_called()
        self.mock_collection.insert_one.assert_not_called()

    def test_save_gambits_invalid_time(self):
        """Test that gambits with an invalid timestamp are not saved."""
        # Create a completely new test with a different approach

        # Create test gambits with a timestamp outside the current gambit day
        test_gambits = [
            {
                "playerName": "Player1",
                "modVersion": "1.0.0",
                "name": "Gambit1",
                "timestamp": "2025-05-06 12:00:00",  # Before the previous reset
                "data": "test_data1"
            }
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

                    # Verify the collection.find_one was called with the correct filter
                    mock_collection.find_one.assert_called_once_with(
                        {"year": next_reset.year, "month": next_reset.month, "day": next_reset.day}
                    )

                    # Verify the collection.insert_one was not called
                    mock_collection.insert_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
