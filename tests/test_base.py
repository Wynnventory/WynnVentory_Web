import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class BaseTestCase(unittest.TestCase):
    """Base test case class with common setup and teardown functionality."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Initialize empty lists to track patches
        self.patches = []
        self.mocks = {}

    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        for patch_obj in self.patches:
            patch_obj.stop()

    def create_patch(self, target, name=None, **kwargs):
        """
        Create a patch and start it.

        Args:
            target (str): The target to patch
            name (str, optional): The name to use for the mock in self.mocks. Defaults to the last part of target.
            **kwargs: Additional arguments to pass to patch

        Returns:
            MagicMock: The mock object
        """
        if name is None:
            name = target.split('.')[-1]

        patch_obj = patch(target, **kwargs)
        mock_obj = patch_obj.start()

        # Store the patch and mock
        self.patches.append(patch_obj)
        self.mocks[name] = mock_obj

        return mock_obj

    def setup_datetime_mock(self, current_time=None, module_path=None):
        """
        Set up a mock for datetime.

        Args:
            current_time (datetime, optional): The current time to use. Defaults to now with UTC timezone.
            module_path (str, optional): The module path to patch. If None, patches datetime.datetime.

        Returns:
            MagicMock: The datetime mock
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        target = f'{module_path}.datetime' if module_path else 'datetime.datetime'
        mock_datetime = self.create_patch(target)
        mock_datetime.now.return_value = current_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        return mock_datetime

    def setup_time_validation_mocks(self, current_time=None, week_tuple=None, gambit_day_tuple=None):
        """
        Set up common mocks for time validation tests.

        Args:
            current_time (datetime, optional): The current time to use. Defaults to now with UTC timezone.
            week_tuple (tuple, optional): A tuple of (year, week) to return from get_lootpool_week_for_timestamp.
            gambit_day_tuple (tuple, optional): A tuple of (previous_reset, next_reset) to return from get_current_gambit_day.

        Returns:
            dict: A dictionary of mock objects
        """
        mocks = {}

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Mock datetime
        mocks['datetime'] = self.setup_datetime_mock(current_time, 'modules.utils.time_validation')

        # Mock get_lootpool_week_for_timestamp if week_tuple is provided
        if week_tuple:
            mocks['get_week'] = self.create_patch('modules.utils.time_validation.get_lootpool_week_for_timestamp')
            mocks['get_week'].return_value = week_tuple

        # Mock get_current_gambit_day if gambit_day_tuple is provided
        if gambit_day_tuple:
            mocks['get_gambit_day'] = self.create_patch('modules.utils.time_validation.get_current_gambit_day')
            mocks['get_gambit_day'].return_value = gambit_day_tuple

        return mocks

    def setup_collection_mock(self, module_path):
        """
        Set up a mock for get_collection.

        Args:
            module_path (str): The module path to patch

        Returns:
            MagicMock: The collection mock
        """
        mock_get_collection = self.create_patch(f'{module_path}.get_collection')
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        self.mocks['collection'] = mock_collection

        return mock_collection
