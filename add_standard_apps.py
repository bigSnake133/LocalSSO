"""Add a generic example application without storing plaintext secrets in source."""

from __future__ import annotations

import getpass
import json
from pathlib import Path

from crypto_dpapi import protect


ROOT = Path(__file__).resolve().parent
VAULT_PATH = ROOT / "vault.json"
USER_SELECTOR = "input[autocomplete='username'], input[name='username'], input[name='userName'], input[name='email'], input[type='email'], input[type='text']"
PASSWORD_SELECTOR = "input[type='password']"
SUBMIT_SELECTOR = "button[type='submit'], input[type='submit'], button.login, button[class*='login']"

APP_TEMPLATES = [
    {
        "id": "example-application",
        "name": "示例应用",
        "url": "https://example.com/login",
        "icon": "globe",
        "needs_username": True,
        "login": {"usernameSelector": USER_SELECTOR, "passwordSelector": PASSWORD_SELECTOR, "submitSelector": SUBMIT_SELECTOR, "autoSubmit": True},
    },
]


def load_vault() -> dict:
    return json.loads(VAULT_PATH.read_text(encoding="utf-8")) if VAULT_PATH.exists() else {"version": 1, "apps": []}


def main() -> None:
    vault = load_vault()
    updated = []
    for template in APP_TEMPLATES:
        app = dict(template)
        if app.pop("direct", False):
            updated.append(app)
            continue
        username = input(f"{app['name']} account: ").strip() if app.pop("needs_username") else ""
        password = getpass.getpass(f"{app['name']} password (not displayed): ")
        if not password or (app["login"]["usernameSelector"] and not username):
            raise ValueError(f"{app['name']} requires the requested login value.")
        app["credential"] = {"username": protect(username), "password": protect(password)}
        updated.append(app)

    new_ids = {app["id"] for app in updated}
    vault["apps"] = [app for app in vault["apps"] if app["id"] not in new_ids] + updated
    VAULT_PATH.write_text(json.dumps(vault, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(updated)} app definitions to {VAULT_PATH}.")


if __name__ == "__main__":
    main()
