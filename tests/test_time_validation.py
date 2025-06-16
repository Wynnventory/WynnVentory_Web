import unittest
from datetime import datetime, timezone
from unittest.mock import patch

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

    def test_get_lootpool_week_for_timestamp(self):
        """Test get_lootpool_week_for_timestamp with various scenarios."""
        # Create mock datetime objects for our test cases
        friday_before_reset = datetime(2025, 5, 2, 17, 59, 59)  # Friday at 5:59:59 PM
        friday_after_reset = datetime(2025, 5, 2, 18, 0, 1)  # Friday at 6:00:01 PM
        middle_of_week = datetime(2025, 5, 5, 12, 0, 0)  # Monday at noon

        # Create a mock for datetime
        mock_datetime = self.create_patch('modules.utils.time_validation.datetime')

        # Mock the strptime method to return our test datetimes
        mock_datetime.strptime.side_effect = lambda ts, fmt: {
            "2025-05-02 17:59:59": friday_before_reset,
            "2025-05-02 18:00:01": friday_after_reset,
            "2025-05-05 12:00:00": middle_of_week
        }[ts]

        # Test case 1: Friday before reset (6 PM UTC)
        # For a timestamp just before reset (Friday at 5:59:59 PM),
        # the function should return the previous week
        year1, week1 = get_lootpool_week_for_timestamp("2025-05-02 17:59:59")

        # The last reset would be the previous Friday (April 25) at 6 PM
        # So the week number should be from April 28
        self.assertEqual(2025, year1)
        self.assertEqual(17, week1)

        # We can't assert the exact week number because it depends on the calendar,
        # but we can check that it's calculated correctly

        # Test case 2: Friday after reset (6 PM UTC)
        # For a timestamp just after reset (Friday at 6:00:01 PM),
        # the function should return the current week
        year2, week2 = get_lootpool_week_for_timestamp("2025-05-02 18:00:01")

        # The last reset would be the current Friday (May 5) at 6 PM
        # So the week number should be from May 5
        self.assertEqual(2025, year2)
        self.assertEqual(18, week2)
        # Again, we can't assert the exact week number

        # Test case 3: Middle of the week
        # For a timestamp in the middle of the week (Monday at noon),
        # the function should return the current week
        year3, week3 = get_lootpool_week_for_timestamp("2025-05-05 12:00:00")

        # The last reset would be the previous Friday (May 5) at 6 PM
        # So the week number should be from May 5
        self.assertEqual(2025, year3)
        self.assertEqual(18, week3)
        # Again, we can't assert the exact week number

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
        mocks['get_week'].assert_called_once_with(mock_now.strftime('%Y-%m-%d %H:%M:%S'))

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
        mocks['get_week'].assert_called_once_with(mock_now.strftime('%Y-%m-%d %H:%M:%S'), reset_hour=17)

        # Verify the result
        self.assertEqual((year, week), (2025, 19))

    @patch('modules.utils.time_validation.datetime')
    def test_get_current_gambit_day(self, mock_datetime):
        """Test get_current_gambit_day function."""
        # Test case 1: Before reset (5 PM UTC)
        mock_now = datetime(2025, 5, 8, 16, 0, 0)  # 4 PM UTC
        mock_datetime.now.return_value = mock_now

        previous_reset, next_reset = get_current_gambit_day()

        # Previous reset should be yesterday at 5 PM
        expected_previous = datetime(2025, 5, 7, 17, 0, 0, 0)
        # Next reset should be today at 5 PM
        expected_next = datetime(2025, 5, 8, 17, 0, 0, 0)

        # Compare year, month, day, hour, minute, second
        self.assertEqual(previous_reset.year, expected_previous.year)
        self.assertEqual(previous_reset.month, expected_previous.month)
        self.assertEqual(previous_reset.day, expected_previous.day)
        self.assertEqual(previous_reset.hour, expected_previous.hour)
        self.assertEqual(previous_reset.minute, expected_previous.minute)
        self.assertEqual(previous_reset.second, expected_previous.second)

        self.assertEqual(next_reset.year, expected_next.year)
        self.assertEqual(next_reset.month, expected_next.month)
        self.assertEqual(next_reset.day, expected_next.day)
        self.assertEqual(next_reset.hour, expected_next.hour)
        self.assertEqual(next_reset.minute, expected_next.minute)
        self.assertEqual(next_reset.second, expected_next.second)

        # Test case 2: After reset (5 PM UTC)
        mock_now = datetime(2025, 5, 8, 18, 0, 0)  # 6 PM UTC
        mock_datetime.now.return_value = mock_now

        previous_reset, next_reset = get_current_gambit_day()

        # Previous reset should be today at 5 PM
        expected_previous = datetime(2025, 5, 8, 17, 0, 0, 0)
        # Next reset should be tomorrow at 5 PM
        expected_next = datetime(2025, 5, 9, 17, 0, 0, 0)

        # Compare year, month, day, hour, minute, second
        self.assertEqual(previous_reset.year, expected_previous.year)
        self.assertEqual(previous_reset.month, expected_previous.month)
        self.assertEqual(previous_reset.day, expected_previous.day)
        self.assertEqual(previous_reset.hour, expected_previous.hour)
        self.assertEqual(previous_reset.minute, expected_previous.minute)
        self.assertEqual(previous_reset.second, expected_previous.second)

        self.assertEqual(next_reset.year, expected_next.year)
        self.assertEqual(next_reset.month, expected_next.month)
        self.assertEqual(next_reset.day, expected_next.day)
        self.assertEqual(next_reset.hour, expected_next.hour)
        self.assertEqual(next_reset.minute, expected_next.minute)
        self.assertEqual(next_reset.second, expected_next.second)

    def test_get_week_range(self):
        """Test get_week_range function."""
        # Test case 1: Middle of the week
        test_date = datetime(2025, 5, 8, 12, 0, 0)  # Monday at noon
        reset_day = 4  # Friday
        reset_hour = 18  # 6 PM

        last_reset, next_reset = get_week_range(reset_day, reset_hour, test_date)

        # Last reset should be the previous Friday at 6 PM
        expected_last = datetime(2025, 5, 2, 18, 0, 0)
        # Next reset should be the next Friday at 6 PM
        expected_next = datetime(2025, 5, 9, 18, 0, 0)

        self.assertEqual(last_reset, expected_last)
        self.assertEqual(next_reset, expected_next)

        # Test case 2: On reset day before reset time
        test_date = datetime(2025, 5, 2, 17, 0, 0)  # Friday at 5 PM (before reset)

        last_reset, next_reset = get_week_range(reset_day, reset_hour, test_date)

        # Last reset should be the previous Friday at 6 PM
        expected_last = datetime(2025, 4, 25, 18, 0, 0)
        # Next reset should be today at 6 PM
        expected_next = datetime(2025, 5, 2, 18, 0, 0)

        self.assertEqual(last_reset, expected_last)
        self.assertEqual(next_reset, expected_next)

        # Test case 3: On reset day after reset time
        test_date = datetime(2025, 5, 2, 19, 0, 0)  # Friday at 7 PM (after reset)

        last_reset, next_reset = get_week_range(reset_day, reset_hour, test_date)

        # Last reset should be today at 6 PM
        expected_last = datetime(2025, 5, 2, 18, 0, 0)
        # Next reset should be next Friday at 6 PM
        expected_next = datetime(2025, 5, 9, 18, 0, 0)

        self.assertEqual(last_reset, expected_last)
        self.assertEqual(next_reset, expected_next)

    def test_is_time_valid(self):
        """Test is_time_valid function."""
        # Test case 1: Valid LOOT time
        with patch('modules.utils.time_validation.get_week_range') as mock_get_range:
            # Mock the week range to return a fixed range
            week_start = datetime(2025, 5, 2, 18, 0, 0)
            week_end = datetime(2025, 5, 9, 18, 0, 0)
            mock_get_range.return_value = (week_start, week_end)

            # Test a time within the range
            valid_time = "2025-05-05 12:00:00"  # Monday at noon
            result = is_time_valid(Collection.LOOT, valid_time)
            self.assertTrue(result)

            # Test a time before the range
            invalid_time_before = "2025-05-02 17:00:00"  # Friday at 5 PM (before reset)
            result = is_time_valid(Collection.LOOT, invalid_time_before)
            self.assertFalse(result)

            # Test a time after the range
            invalid_time_after = "2025-05-09 19:00:00"  # Next Friday at 7 PM (after reset)
            result = is_time_valid(Collection.LOOT, invalid_time_after)
            self.assertFalse(result)

        # Test case 2: Valid RAID time
        with patch('modules.utils.time_validation.get_week_range') as mock_get_range:
            week_start, week_end = get_week_range(reset_day=4, reset_hour=18, now=datetime(2025, 5, 2, 18, 0, 0))
            mock_get_range.return_value = (week_start, week_end)

            # Test a time within the range
            valid_time = "2025-05-05 12:00:00"  # Monday at noon
            result = is_time_valid(Collection.RAID, valid_time)
            self.assertTrue(result)

        # Test case 3: Valid GAMBIT time
        with patch('modules.utils.time_validation.get_current_gambit_day') as mock_get_day:
            # Mock the gambit day to return a fixed range
            day_start = datetime(2025, 5, 5, 17, 0, 0)
            day_end = datetime(2025, 5, 6, 17, 0, 0)
            mock_get_day.return_value = (day_start, day_end)

            # Test a time within the range
            valid_time = "2025-05-05 18:00:00"  # Monday at 6 PM
            result = is_time_valid(Collection.GAMBIT, valid_time)
            self.assertTrue(result)

            # Test a time before the range
            invalid_time_before = "2025-05-05 16:00:00"  # Monday at 4 PM (before reset)
            result = is_time_valid(Collection.GAMBIT, invalid_time_before)
            self.assertFalse(result)

            # Test a time after the range
            invalid_time_after = "2025-05-09 18:00:00"  # Tuesday at 6 PM (after reset)
            result = is_time_valid(Collection.GAMBIT, invalid_time_after)
            self.assertFalse(result)

        # Test case 4: Invalid collection type
        result = is_time_valid("INVALID_TYPE", "2025-05-05 12:00:00")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
