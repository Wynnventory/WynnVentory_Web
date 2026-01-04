import unittest
from datetime import datetime, timezone

from modules.models.collection_types import Collection
from modules.utils.time_validation import (
    get_lootpool_week,
    get_lootpool_week_for_timestamp,
    get_raidpool_week,
    get_current_gambit_day,
    get_week_range,
    is_time_valid
)
from tests.test_base import BaseTestCase


class TestTimeValidation(BaseTestCase):
    """Test cases for the time_validation module."""

    def assert_datetime_equal(self, actual, expected):
        """Assert that two datetime objects are equal by comparing their components."""
        self.assertEqual(actual.year, expected.year)
        self.assertEqual(actual.month, expected.month)
        self.assertEqual(actual.day, expected.day)
        self.assertEqual(actual.hour, expected.hour)
        self.assertEqual(actual.minute, expected.minute)
        self.assertEqual(actual.second, expected.second)

    def verify_time_validity(self, collection_type, valid_time, invalid_time_before=None, invalid_time_after=None):
        """Verify time validity for a given collection type and time values."""
        # Test a time within the range
        result = is_time_valid(collection_type, valid_time)
        self.assertTrue(result)

        # Test a time before the range if provided
        if invalid_time_before:
            result = is_time_valid(collection_type, invalid_time_before)
            self.assertFalse(result)

        # Test a time after the range if provided
        if invalid_time_after:
            result = is_time_valid(collection_type, invalid_time_after)
            self.assertFalse(result)

    def test_get_lootpool_week_for_timestamp(self):
        """Test get_lootpool_week_for_timestamp with various scenarios."""
        # Create mock datetime objects for our test cases
        friday_before_reset = datetime(2025, 5, 2, 17, 59, 59, tzinfo=timezone.utc)  # Friday at 5:59:59 PM UTC
        friday_after_reset = datetime(2025, 5, 2, 18, 0, 1, tzinfo=timezone.utc)  # Friday at 6:00:01 PM UTC
        middle_of_week = datetime(2025, 5, 5, 12, 0, 0, tzinfo=timezone.utc)  # Monday at noon UTC

        # Test case 1: Friday before reset (6 PM UTC)
        # For a timestamp just before reset (Friday at 5:59:59 PM),
        # the function should return the previous week
        year1, week1 = get_lootpool_week_for_timestamp("2025-05-02T17:59:59Z")

        # The last reset would be the previous Friday (April 25) at 6 PM
        # So the week number should be from April 28
        self.assertEqual(2025, year1)
        self.assertEqual(17, week1)

        # Test case 2: Friday after reset (6 PM UTC)
        # For a timestamp just after reset (Friday at 6:00:01 PM),
        # the function should return the current week
        year2, week2 = get_lootpool_week_for_timestamp("2025-05-02T18:00:01Z")

        # The last reset would be the current Friday (May 2) at 6 PM
        self.assertEqual(2025, year2)
        self.assertEqual(18, week2)

        # Test case 3: Middle of the week
        # For a timestamp in the middle of the week (Monday at noon),
        # the function should return the current week
        year3, week3 = get_lootpool_week_for_timestamp("2025-05-05T12:00:00Z")

        # The last reset would be the current Friday (May 2) at 6 PM
        self.assertEqual(2025, year3)
        self.assertEqual(18, week3)

        # We can verify that the week numbers are consistent
        self.assertEqual(week2, week3)  # Both should be the same week
        self.assertNotEqual(week1, week2)  # These should be different weeks

    def test_get_lootpool_week(self):
        """Test get_lootpool_week function."""
        # Set up a fixed date and mocks
        mock_now = datetime(2025, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        mocks = self.setup_time_validation_mocks(
            current_time=mock_now,
            week_tuple=(2025, 19)  # Example week number
        )

        # Call the function
        year, week = get_lootpool_week()

        # Verify the function was called with the correct timestamp
        mocks['get_week'].assert_called_once_with(mock_now)

        # Verify the result
        self.assertEqual((year, week), (2025, 19))

    def test_get_raidpool_week(self):
        """Test get_raidpool_week function."""
        # Set up a fixed date and mocks
        mock_now = datetime(2025, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        mocks = self.setup_time_validation_mocks(
            current_time=mock_now,
            week_tuple=(2025, 19)  # Example week number
        )

        # Call the function
        year, week = get_raidpool_week()

        # Verify the function was called with the correct timestamp and reset hour
        mocks['get_week'].assert_called_once_with(mock_now, reset_hour=17)

        # Verify the result
        self.assertEqual((year, week), (2025, 19))

    def test_get_current_gambit_day(self):
        """Test get_current_gambit_day function."""
        # Test case 1: Before reset (5 PM UTC)
        mock_now = datetime(2025, 5, 8, 16, 0, 0, tzinfo=timezone.utc)  # 4 PM UTC
        mock_datetime = self.setup_datetime_mock(mock_now, 'modules.utils.time_validation')

        previous_reset, next_reset = get_current_gambit_day()

        # Previous reset should be yesterday at 5 PM
        expected_previous = datetime(2025, 5, 7, 17, 0, 0, 0, tzinfo=timezone.utc)
        # Next reset should be today at 5 PM
        expected_next = datetime(2025, 5, 8, 17, 0, 0, 0, tzinfo=timezone.utc)

        # Compare datetime objects
        self.assert_datetime_equal(previous_reset, expected_previous)
        self.assert_datetime_equal(next_reset, expected_next)

        # Test case 2: After reset (5 PM UTC)
        mock_now = datetime(2025, 5, 8, 18, 0, 0, tzinfo=timezone.utc)  # 6 PM UTC
        mock_datetime.now.return_value = mock_now

        previous_reset, next_reset = get_current_gambit_day()

        # Previous reset should be today at 5 PM
        expected_previous = datetime(2025, 5, 8, 17, 0, 0, 0, tzinfo=timezone.utc)
        # Next reset should be tomorrow at 5 PM
        expected_next = datetime(2025, 5, 9, 17, 0, 0, 0, tzinfo=timezone.utc)

        # Compare datetime objects
        self.assert_datetime_equal(previous_reset, expected_previous)
        self.assert_datetime_equal(next_reset, expected_next)

    def test_get_week_range(self):
        """Test get_week_range function."""
        # Test case 1: Middle of the week
        test_date = datetime(2025, 5, 8, 12, 0, 0, tzinfo=timezone.utc)  # Monday at noon
        reset_day = 4  # Friday
        reset_hour = 18  # 6 PM

        last_reset, next_reset = get_week_range(reset_day, reset_hour, test_date)

        # Last reset should be the previous Friday at 6 PM
        expected_last = datetime(2025, 5, 2, 18, 0, 0, tzinfo=timezone.utc)
        # Next reset should be the next Friday at 6 PM
        expected_next = datetime(2025, 5, 9, 18, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(last_reset, expected_last)
        self.assertEqual(next_reset, expected_next)

        # Test case 2: On reset day before reset time
        test_date = datetime(2025, 5, 2, 17, 0, 0, tzinfo=timezone.utc)  # Friday at 5 PM (before reset)

        last_reset, next_reset = get_week_range(reset_day, reset_hour, test_date)

        # Last reset should be the previous Friday at 6 PM
        expected_last = datetime(2025, 4, 25, 18, 0, 0, tzinfo=timezone.utc)
        # Next reset should be today at 6 PM
        expected_next = datetime(2025, 5, 2, 18, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(last_reset, expected_last)
        self.assertEqual(next_reset, expected_next)

        # Test case 3: On reset day after reset time
        test_date = datetime(2025, 5, 2, 19, 0, 0, tzinfo=timezone.utc)  # Friday at 7 PM (after reset)

        last_reset, next_reset = get_week_range(reset_day, reset_hour, test_date)

        # Last reset should be today at 6 PM
        expected_last = datetime(2025, 5, 2, 18, 0, 0, tzinfo=timezone.utc)
        # Next reset should be next Friday at 6 PM
        expected_next = datetime(2025, 5, 9, 18, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(last_reset, expected_last)
        self.assertEqual(next_reset, expected_next)

    def test_is_time_valid(self):
        """Test is_time_valid function."""
        # Test case 1: Valid LOOT time
        mock_get_range = self.create_patch('modules.utils.time_validation.get_week_range')
        # Mock the week range to return a fixed range
        week_start = datetime(2025, 5, 2, 18, 0, 0, tzinfo=timezone.utc)
        week_end = datetime(2025, 5, 9, 18, 0, 0, tzinfo=timezone.utc)
        mock_get_range.return_value = (week_start, week_end)

        # Verify LOOT time validity
        self.verify_time_validity(
            Collection.LOOT,
            valid_time="2025-05-05T12:00:00Z",  # Monday at noon
            invalid_time_before="2025-05-02T17:00:00Z",  # Friday at 5 PM (before reset)
            invalid_time_after="2025-05-09T19:00:00Z"  # Next Friday at 7 PM (after reset)
        )

        # Test case 2: Valid RAID time
        # Reset the mock for get_week_range
        mock_get_range.reset_mock()
        week_start, week_end = get_week_range(reset_day=4, reset_hour=18, now=datetime(2025, 5, 2, 18, 0, 0, tzinfo=timezone.utc))
        mock_get_range.return_value = (week_start, week_end)

        # Verify RAID time validity
        self.verify_time_validity(
            Collection.RAID,
            valid_time="2025-05-05T12:00:00Z"  # Monday at noon
        )

        # Test case 3: Valid GAMBIT time
        mock_get_day = self.create_patch('modules.utils.time_validation.get_current_gambit_day')
        # Mock the gambit day to return a fixed range
        day_start = datetime(2025, 5, 5, 17, 0, 0, tzinfo=timezone.utc)
        day_end = datetime(2025, 5, 6, 17, 0, 0, tzinfo=timezone.utc)
        mock_get_day.return_value = (day_start, day_end)

        # Verify GAMBIT time validity
        self.verify_time_validity(
            Collection.GAMBIT,
            valid_time="2025-05-05T18:00:00Z",  # Monday at 6 PM
            invalid_time_before="2025-05-05T16:00:00Z",  # Monday at 4 PM (before reset)
            invalid_time_after="2025-05-09T18:00:00Z"  # Tuesday at 6 PM (after reset)
        )

        # Test case 4: Invalid collection type
        result = is_time_valid("INVALID_TYPE", "2025-05-05T12:00:00Z")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
