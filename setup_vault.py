"""Create or append applications in the DPAPI-encrypted local credential vault."""

from __future__ import annotations

import getpass
import json
from pathlib import Path

from crypto_dpapi import protect


ROOT = Path(__file__).resolve().parent
VAULT_PATH = ROOT / "vault.json"

EXAMPLE_APP = {
    "id": "example-application",
    "name": "示例应用",
    "url": "https://example.com/login",
    "icon": "globe",
    "login": {
        "usernameSelector": "input[name='os_username'], input#os_username, input[name='username']",
        "passwordSelector": "input[name='os_password'], input#os_password, input[type='password']",
        "submitSelector": "#loginButton, input[type='submit'], button[type='submit']",
        "autoSubmit": True,
    },
}


def load_vault() -> dict:
    if not VAULT_PATH.exists():
        return {"version": 1, "apps": []}
    return json.loads(VAULT_PATH.read_text(encoding="utf-8"))


def prompt_app() -> dict:
    use_default = input("Configure the included example application? [Y/n]: ").strip().lower()
    if use_default in ("", "y", "yes"):
        app = dict(EXAMPLE_APP)
        app["login"] = dict(EXAMPLE_APP["login"])
    else:
        app_id = input("App id (letters, digits, hyphen): ").strip()
        app = {
            "id": app_id,
            "name": input("Display name: ").strip(),
            "url": input("Login URL: ").strip(),
            "icon": input("Icon name [globe]: ").strip() or "globe",
            "login": {
                "usernameSelector": input("Username CSS selector: ").strip(),
                "passwordSelector": input("Password CSS selector: ").strip(),
                "submitSelector": input("Submit CSS selector: ").strip(),
                "autoSubmit": input("Submit automatically? [Y/n]: ").strip().lower() not in ("n", "no"),
            },
        }

    username = input("Account name: ").strip()
    password = getpass.getpass("Password (not displayed): ")
    if not app["id"] or not app["name"] or not app["url"] or not username or not password:
        raise ValueError("App id, name, URL, account name, and password are required.")

    app["credential"] = {"username": protect(username), "password": protect(password)}
    return app


def main() -> None:
    vault = load_vault()
    app = prompt_app()
    vault["apps"] = [item for item in vault["apps"] if item["id"] != app["id"]]
    vault["apps"].append(app)
    VAULT_PATH.write_text(json.dumps(vault, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved encrypted credential for '{app['name']}' to {VAULT_PATH}.")


if __name__ == "__main__":
    main()
