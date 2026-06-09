import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.routes.web.web import web_bp


def make_test_app():
    # web_bp carries its own template_folder, so registering it is enough to
    # render developer/api_key.html and the shared base template.
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(web_bp)
    return app


class TestApiKeyRoute(unittest.TestCase):
    def setUp(self):
        self.app = make_test_app()
        self.client = self.app.test_client()

    def test_get_renders_form_with_scopes(self):
        resp = self.client.get("/developer/api-key")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("read:market", body)
        self.assertIn("Generate an API Key", body)

    @patch("modules.routes.web.web.generate_and_store_key", return_value="TEST-TOKEN-123")
    def test_post_success_shows_token(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
            "description": "my app",
            "scopes": ["read:market", "read:lootpool"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("TEST-TOKEN-123", resp.get_data(as_text=True))
        mock_gen.assert_called_once_with(
            "alice", "my app", ["read:market", "read:lootpool"],
            email="alice@example.com", discord=None,
        )

    @patch("modules.routes.web.web.generate_and_store_key", return_value="TEST-TOKEN-123")
    def test_post_passes_discord_when_provided(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
            "discord": "alice#4321",
            "description": "my app",
            "scopes": ["read:market"],
        })
        self.assertEqual(resp.status_code, 200)
        mock_gen.assert_called_once_with(
            "alice", "my app", ["read:market"],
            email="alice@example.com", discord="alice#4321",
        )

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_missing_name_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "",
            "email": "alice@example.com",
            "scopes": ["read:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("project or application name", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_invalid_email_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "not-an-email",
            "scopes": ["read:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("valid email", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_write_scope_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
            "scopes": ["write:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Invalid scope", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_no_scopes_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("at least one scope", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_mixed_valid_and_write_scope_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "email": "alice@example.com",
            "scopes": ["read:market", "write:market"],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Invalid scope", resp.get_data(as_text=True))
        mock_gen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
