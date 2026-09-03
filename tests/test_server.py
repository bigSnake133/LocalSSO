"""Safe unit tests that use a temporary vault and never access a user vault."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server  # noqa: E402


class ServerUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_vault = server.VAULT_PATH
        server.VAULT_PATH = Path(self.temp_dir.name) / "synthetic-vault.json"

    def tearDown(self) -> None:
        server.VAULT_PATH = self.previous_vault
        self.temp_dir.cleanup()

    def test_default_groups_are_created_for_an_empty_synthetic_vault(self) -> None:
        vault = {"version": 1, "apps": []}
        groups = server.ensure_groups(vault)
        self.assertEqual({group["id"] for group in groups}, {"work", "personal", "uncategorized"})

    def test_public_app_returns_a_username_but_keeps_the_password_masked(self) -> None:
        app = {
            "id": "example-application",
            "name": "Example Application",
            "url": "https://example.com/login",
            "credential": {"username": "not-read-by-this-test", "password": "not-read-by-this-test"},
        }
        with patch.object(server, "unprotect", return_value="example.user") as unprotect:
            public = server.public_app(app)
        self.assertTrue(public["hasUsername"])
        self.assertTrue(public["hasPassword"])
        self.assertEqual(public["username"], "example.user")
        self.assertEqual(public["passwordMasked"], "********")
        unprotect.assert_called_once_with("not-read-by-this-test")

    def test_build_app_rejects_a_non_http_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "URL"):
            server.build_app(
                {"name": "Example", "url": "file:///private/path", "groupId": "uncategorized"},
                None,
                {"uncategorized"},
            )

    def test_public_app_preserves_a_custom_login_flow(self) -> None:
        app = {
            "id": "example-application",
            "name": "Example Application",
            "url": "https://example.com/login",
            "credential": {"username": "protected-user", "password": "protected-password"},
            "login": {"preLoginSelector": "button", "preLoginText": "HTML5", "autoSubmit": False},
        }
        with patch.object(server, "unprotect", return_value="example.user"):
            public = server.public_app(app)
        self.assertEqual(public["login"]["preLoginSelector"], "button")
        self.assertEqual(public["login"]["preLoginText"], "HTML5")
        self.assertFalse(public["login"]["autoSubmit"])


if __name__ == "__main__":
    unittest.main()
