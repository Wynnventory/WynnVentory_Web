import os
import sys
import unittest

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.utils.version import compare_versions, VersionPart


class TestVersionComparison(unittest.TestCase):
    """Test cases for the compare_versions function."""

    def test_basic_version_comparison(self):
        """Test basic version comparisons."""
        # Equal versions
        self.assertTrue(compare_versions("1.0", "1.0"))
        self.assertTrue(compare_versions("2.3.4", "2.3.4"))

        # Greater versions
        self.assertTrue(compare_versions("2.0", "1.0"))
        self.assertTrue(compare_versions("1.1", "1.0"))
        self.assertTrue(compare_versions("1.0.1", "1.0.0"))

        # Lesser versions
        self.assertFalse(compare_versions("1.0", "2.0"))
        self.assertFalse(compare_versions("1.0", "1.1"))
        self.assertFalse(compare_versions("1.0.0", "1.0.1"))

    def test_different_segment_counts(self):
        """Test versions with different segment counts."""
        # Equal with different segment counts
        self.assertTrue(compare_versions("1.0", "1.0.0"))
        self.assertTrue(compare_versions("1.0.0.0", "1.0"))

        # Greater with different segment counts
        self.assertTrue(compare_versions("1.1", "1.0.0"))
        self.assertTrue(compare_versions("2", "1.9.9"))

        # Lesser with different segment counts
        self.assertFalse(compare_versions("1.0", "1.0.1"))
        self.assertFalse(compare_versions("1.9.9", "2"))

    def test_versions_with_trailing_letters(self):
        """Test versions with trailing letters."""
        # Alphabetical order for same numeric part
        self.assertTrue(compare_versions("1.0b", "1.0a"))
        self.assertFalse(compare_versions("1.0a", "1.0b"))

        # Numeric part takes precedence
        self.assertTrue(compare_versions("1.1a", "1.0z"))
        self.assertFalse(compare_versions("1.0z", "1.1a"))

        # Empty suffix (final release) > any non-dev suffix
        self.assertTrue(compare_versions("1.0", "1.0beta"))
        self.assertFalse(compare_versions("1.0alpha", "1.0"))

    def test_versions_with_dev_suffix(self):
        """Test versions with 'dev' suffixes."""
        # Dev suffix ranks highest
        self.assertTrue(compare_versions("1.0.0-dev", "1.0.0"))
        self.assertTrue(compare_versions("1.0dev", "1.0"))
        self.assertTrue(compare_versions("1.0-DEV", "1.0"))
        self.assertTrue(compare_versions("1.0dev1", "1.0"))

        # Dev suffix ranks highest within the same numeric part, but not across different numeric parts
        self.assertFalse(compare_versions("1.0-dev", "1.1"))

        # Compare different dev versions
        self.assertTrue(compare_versions("1.0-dev2", "1.0-dev1"))
        self.assertFalse(compare_versions("1.0-dev1", "1.0-dev2"))

    def test_edge_cases(self):
        """Test edge cases."""
        # Empty strings
        self.assertTrue(compare_versions("", ""))

        # No numeric part
        self.assertTrue(compare_versions("beta", "alpha"))
        self.assertFalse(compare_versions("alpha", "beta"))

        # Mixed formats
        self.assertTrue(compare_versions("1.0.0-dev", "1.0.0.0"))
        self.assertTrue(compare_versions("1.0.0", "1.0.0-beta"))

        # Very large version numbers
        self.assertTrue(compare_versions("999.999.999", "999.999.998"))
        self.assertFalse(compare_versions("999.999.998", "999.999.999"))


class TestVersionPart(unittest.TestCase):
    """Test cases for the VersionPart class."""

    def test_version_part_initialization(self):
        """Test VersionPart initialization."""
        # Numeric part with empty suffix
        vp = VersionPart("123")
        self.assertEqual(vp.num, 123)
        self.assertEqual(vp.suffix, "")

        # Numeric part with suffix
        vp = VersionPart("123abc")
        self.assertEqual(vp.num, 123)
        self.assertEqual(vp.suffix, "abc")

        # No numeric part
        vp = VersionPart("abc")
        self.assertEqual(vp.num, 0)
        self.assertEqual(vp.suffix, "abc")

    def test_version_part_comparison(self):
        """Test VersionPart comparison."""
        # Equal parts
        self.assertEqual(VersionPart("123"), VersionPart("123"))
        self.assertEqual(VersionPart("123abc"), VersionPart("123abc"))

        # Different numeric parts
        self.assertLess(VersionPart("123"), VersionPart("124"))
        self.assertGreater(VersionPart("124"), VersionPart("123"))

        # Same numeric part, different suffixes
        self.assertLess(VersionPart("123a"), VersionPart("123b"))
        self.assertGreater(VersionPart("123b"), VersionPart("123a"))

        # Dev suffix comparison
        self.assertGreater(VersionPart("123dev"), VersionPart("123"))
        self.assertGreater(VersionPart("123-dev"), VersionPart("123"))
        self.assertLess(VersionPart("123"), VersionPart("123dev"))

        # Empty suffix vs non-dev suffix
        self.assertGreater(VersionPart("123"), VersionPart("123beta"))
        self.assertLess(VersionPart("123alpha"), VersionPart("123"))


if __name__ == "__main__":
    unittest.main()
