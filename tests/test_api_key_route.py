import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.routes.web.web import web_bp
from modules.services.api_key_service import SELF_SERVICE_SCOPES


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

    def test_get_renders_form(self):
        resp = self.client.get("/developer/api-key")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("Generate an API Key", body)
        # Access is shown as a static read-only summary, not selectable scopes.
        self.assertIn("read-only access to all Wynnventory data", body)
        self.assertNotIn('name="scopes"', body)

    @patch("modules.routes.web.web.generate_and_store_key", return_value="TEST-TOKEN-123")
    def test_post_success_grants_all_read_scopes(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "discord": "alice#4321",
            "email": "alice@example.com",
            "description": "my app",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("TEST-TOKEN-123", resp.get_data(as_text=True))
        mock_gen.assert_called_once_with(
            "alice", "my app", SELF_SERVICE_SCOPES,
            email="alice@example.com", discord="alice#4321",
        )

    @patch("modules.routes.web.web.generate_and_store_key", return_value="TEST-TOKEN-123")
    def test_post_succeeds_without_optional_email(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "discord": "alice#4321",
            "description": "my app",
        })
        self.assertEqual(resp.status_code, 200)
        mock_gen.assert_called_once_with(
            "alice", "my app", SELF_SERVICE_SCOPES,
            email=None, discord="alice#4321",
        )

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_missing_name_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "",
            "discord": "alice#4321",
            "description": "my app",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("project or application name", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_missing_discord_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "description": "my app",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Discord username", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_invalid_email_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "discord": "alice#4321",
            "email": "not-an-email",
            "description": "my app",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("valid email", resp.get_data(as_text=True))
        mock_gen.assert_not_called()

    @patch("modules.routes.web.web.generate_and_store_key", return_value="X")
    def test_post_missing_description_is_rejected(self, mock_gen):
        resp = self.client.post("/developer/api-key", data={
            "owner": "alice",
            "discord": "alice#4321",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("intended use", resp.get_data(as_text=True))
        mock_gen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
