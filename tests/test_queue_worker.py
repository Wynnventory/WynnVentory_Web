import unittest
import sys
import os
import logging
from unittest.mock import patch, MagicMock, call
import time
from queue import Queue

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.utils import queue_worker
from modules.models.collection_types import Collection

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestQueueWorker(unittest.TestCase):
    """Test cases for the queue_worker module."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Reset the queue and create a new worker thread for each test
        self.original_queue = queue_worker._request_queue
        self.original_worker_thread = queue_worker._worker_thread

        # Create a patch for the logger to capture log messages
        self.logger_patch = patch('modules.utils.queue_worker.logger')
        self.mock_logger = self.logger_patch.start()

    def tearDown(self):
        """Clean up after each test."""
        # Restore the original queue and worker thread
        queue_worker._request_queue = self.original_queue
        queue_worker._worker_thread = self.original_worker_thread

        # Stop the logger patch
        self.logger_patch.stop()

    @patch('modules.repositories.market_repo.save')
    def test_enqueue_basic(self, mock_save):
        """Test basic enqueue functionality."""
        # Create a test item
        test_item = {"id": "test1", "data": "test_data"}

        # Enqueue the item
        queue_worker.enqueue(Collection.MARKET, test_item)

        # Verify the item was logged
        self.mock_logger.debug.assert_called_with(
            f"Enqueued item for {Collection.MARKET.name}, queue size: {queue_worker._request_queue.qsize()}"
        )

        # Wait a short time for the worker thread to process the item
        time.sleep(0.1)

        # Verify the item was processed and saved
        mock_save.assert_called_once_with(test_item)

    @patch('modules.repositories.market_repo.save')
    @patch('modules.repositories.lootpool_repo.save')
    @patch('modules.repositories.raidpool_repo.save')
    def test_multiple_collection_types(self, mock_raid_save, mock_loot_save, mock_market_save):
        """Test enqueueing items for different collection types."""
        # Create test items for different collection types
        market_item = {"id": "market1", "data": "market_data"}
        loot_item = {"id": "loot1", "data": "loot_data"}
        raid_item = {"id": "raid1", "data": "raid_data"}

        # Enqueue the items
        queue_worker.enqueue(Collection.MARKET, market_item)
        queue_worker.enqueue(Collection.LOOT, loot_item)
        queue_worker.enqueue(Collection.RAID, raid_item)

        # Wait for the worker thread to process the items
        time.sleep(0.3)

        # Verify the items were processed and saved to the correct repositories
        mock_market_save.assert_called_once_with(market_item)
        mock_loot_save.assert_called_once_with(loot_item)
        mock_raid_save.assert_called_once_with(raid_item)

    @patch('modules.repositories.market_repo.save', side_effect=Exception("Test exception"))
    def test_error_handling(self, mock_save):
        """Test error handling during item processing."""
        # Create a test item
        test_item = {"id": "error_test", "data": "error_data"}

        # Enqueue the item
        queue_worker.enqueue(Collection.MARKET, test_item)

        # Wait for the worker thread to process the item
        time.sleep(0.1)

        # Verify the error was logged
        self.mock_logger.error.assert_called_with(
            f"Error processing {Collection.MARKET} item: Test exception"
        )

        # Verify the worker continued running despite the error
        self.assertTrue(queue_worker._worker_thread.is_alive())

    def test_shutdown_workers(self):
        """Test the shutdown_workers function."""
        # Create a mock worker thread and usage repo
        mock_thread = MagicMock()
        mock_usage_repo = MagicMock()

        # Configure the mock thread to simulate exiting when join is called
        mock_thread.is_alive.return_value = False

        # Save original objects
        original_usage_repo = queue_worker._usage_repo
        original_thread = queue_worker._worker_thread

        # Replace with mocks
        queue_worker._worker_thread = mock_thread
        queue_worker._usage_repo = mock_usage_repo

        try:
            # Call shutdown_workers
            result = queue_worker.shutdown_workers()

            # Verify the shutdown signal was added to the queue
            self.assertEqual(queue_worker._request_queue.get(), (None, None))

            # Verify the worker thread was joined
            mock_thread.join.assert_called_once()

            # Verify the in-memory buffers were flushed
            mock_usage_repo.flush_all.assert_called_once()

            # Verify the result is True (successful shutdown)
            self.assertTrue(result)
        finally:
            # Restore original objects
            queue_worker._usage_repo = original_usage_repo
            queue_worker._worker_thread = original_thread

    @patch('modules.repositories.market_repo.save')
    def test_large_volume(self, mock_save):
        """Test handling a large volume of items."""
        # Create a large number of test items
        num_items = 100
        test_items = [{"id": f"test{i}", "data": f"data{i}"} for i in range(num_items)]

        # Enqueue all items
        for item in test_items:
            queue_worker.enqueue(Collection.MARKET, item)

        # Wait for the worker thread to process all items
        # This might take some time, so we'll wait for the queue to be empty
        max_wait = 5  # Maximum wait time in seconds
        start_time = time.time()
        while not queue_worker._request_queue.empty() and time.time() - start_time < max_wait:
            time.sleep(0.1)

        # Verify all items were processed
        self.assertEqual(mock_save.call_count, num_items)

        # Verify the calls were made with the correct items
        calls = [call(item) for item in test_items]
        mock_save.assert_has_calls(calls, any_order=True)

    def test_unknown_collection_type(self):
        """Test handling an unknown collection type."""
        # Create a test item with an unknown collection type
        test_item = {"id": "unknown_test", "data": "unknown_data"}

        # Create a mock collection type that's not handled
        class MockCollection:
            name = "UNKNOWN"
            def __repr__(self):
                return "MockCollection.UNKNOWN"

        mock_collection = MockCollection()

        # Enqueue the item
        queue_worker.enqueue(mock_collection, test_item)

        # Wait for the worker thread to process the item
        time.sleep(0.1)

        # Verify the error was logged
        self.mock_logger.error.assert_called_with(
            f"No repository configured for {mock_collection!r}"
        )


if __name__ == "__main__":
    unittest.main()
