"""Safe unit tests that use a temporary vault and never access a user vault."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


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

    def test_public_app_does_not_decrypt_or_return_a_username(self) -> None:
        app = {
            "id": "example-application",
            "name": "Example Application",
            "url": "https://example.com/login",
            "credential": {"username": "not-read-by-this-test", "password": "not-read-by-this-test"},
        }
        public = server.public_app(app)
        self.assertTrue(public["hasUsername"])
        self.assertTrue(public["hasPassword"])
        self.assertNotIn("username", public)
        self.assertEqual(public["passwordMasked"], "********")

    def test_build_app_rejects_a_non_http_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "URL"):
            server.build_app(
                {"name": "Example", "url": "file:///private/path", "groupId": "uncategorized"},
                None,
                {"uncategorized"},
            )


if __name__ == "__main__":
    unittest.main()
