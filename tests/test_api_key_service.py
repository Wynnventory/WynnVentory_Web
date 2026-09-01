import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_base import BaseTestCase

from modules.services import api_key_service


class TestSelfServiceScopes(BaseTestCase):
    def test_only_read_scopes_are_self_serviceable(self):
        # No write scope may ever appear in the self-service allowlist.
        self.assertTrue(all(s.startswith("read:") for s in api_key_service.SELF_SERVICE_SCOPES))
        # Deliberate change-detector: any scope added/removed must force a
        # conscious update here so the self-service allowlist can't drift silently.
        self.assertEqual(
            set(api_key_service.SELF_SERVICE_SCOPES),
            {"read:market", "read:market_archive", "read:lootpool", "read:raidpool"},
        )


class TestIsValidEmail(BaseTestCase):
    def test_accepts_normal_address(self):
        self.assertTrue(api_key_service.is_valid_email("dev@example.com"))

    def test_rejects_blank(self):
        self.assertFalse(api_key_service.is_valid_email(""))
        self.assertFalse(api_key_service.is_valid_email(None))

    def test_rejects_missing_at_or_domain(self):
        self.assertFalse(api_key_service.is_valid_email("notanemail"))
        self.assertFalse(api_key_service.is_valid_email("foo@bar"))


class TestGenerateAndStoreKey(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.mock_collection = self.setup_collection_mock('modules.services.api_key_service')

    def test_returns_token_whose_hash_is_stored(self):
        token = api_key_service.generate_and_store_key(
            "alice", "my app", ["read:market"], email="alice@example.com"
        )
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        self.mock_collection.insert_one.assert_called_once()
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["key_hash"], hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(doc["owner"], "alice")
        self.assertEqual(doc["description"], "my app")
        self.assertEqual(doc["scopes"], ["read:market"])
        self.assertEqual(doc["revoked"], False)
        self.assertIn("created_at", doc)

    def test_email_included_when_provided(self):
        api_key_service.generate_and_store_key("bob", "d", ["read:market"], email="bob@example.com")
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["email"], "bob@example.com")

    def test_email_omitted_when_not_provided(self):
        api_key_service.generate_and_store_key("bob", "d", ["read:market"])
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertNotIn("email", doc)

    def test_discord_included_when_provided(self):
        api_key_service.generate_and_store_key("bob", "d", ["read:market"], discord="bob#1234")
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(doc["discord"], "bob#1234")

    def test_discord_omitted_when_not_provided(self):
        api_key_service.generate_and_store_key("bob", "d", ["read:market"])
        doc = self.mock_collection.insert_one.call_args[0][0]
        self.assertNotIn("discord", doc)


if __name__ == "__main__":
    unittest.main()
