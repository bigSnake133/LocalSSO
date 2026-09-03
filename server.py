"""Loopback-only API and portal server for an encrypted local application vault."""

from __future__ import annotations

import json
import mimetypes
import re
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from crypto_dpapi import protect, unprotect


ROOT = Path(__file__).resolve().parent
PORTAL = ROOT / "portal"
VAULT_PATH = ROOT / "vault.json"
APP_ID = re.compile(r"^[a-zA-Z0-9-]{1,80}$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_COLORS = ("#d3552d", "#147a72", "#b2781a", "#8d4e77", "#3c6596", "#8a6e39")
USERNAME_SELECTOR = "input[autocomplete='username'], input[name='username'], input[name='userName'], input[name='email'], input[type='email'], input[type='text']"
PASSWORD_SELECTOR = "input[type='password']"
SUBMIT_SELECTOR = "button[type='submit'], input[type='submit'], form button:not([disabled]), button.login, button[class*='login']"
DEFAULT_GROUPS = (
    {"id": "work", "name": "工作", "color": "#147a72"},
    {"id": "personal", "name": "个人", "color": "#d3552d"},
    {"id": "uncategorized", "name": "未分类", "color": "#8a6e39"},
)


def load_vault() -> dict:
    if not VAULT_PATH.exists():
        return {"version": 1, "apps": []}
    return json.loads(VAULT_PATH.read_text(encoding="utf-8"))


def save_vault(vault: dict) -> None:
    VAULT_PATH.write_text(json.dumps(vault, ensure_ascii=False, indent=2), encoding="utf-8")


def default_group(app_id: str) -> str:
    del app_id
    return "uncategorized"


def ensure_groups(vault: dict) -> list[dict]:
    groups = vault.get("groups")
    if not isinstance(groups, list) or not groups:
        groups = [dict(group) for group in DEFAULT_GROUPS]
        vault["groups"] = groups
    valid_ids = {group.get("id") for group in groups if isinstance(group, dict)}
    for app in vault.get("apps", []):
        if app.get("groupId") not in valid_ids:
            app["groupId"] = default_group(app["id"])
    return groups


def default_color(app_id: str) -> str:
    return DEFAULT_COLORS[sum(app_id.encode("utf-8")) % len(DEFAULT_COLORS)]


def default_login(app_id: str, has_username: bool, has_password: bool) -> dict:
    del app_id
    return {
        "usernameSelector": USERNAME_SELECTOR if has_username else "",
        "passwordSelector": PASSWORD_SELECTOR if has_password else "",
        "submitSelector": SUBMIT_SELECTOR,
        "autoSubmit": has_password,
    }


def app_login(app: dict) -> dict:
    credential = app.get("credential", {})
    login = default_login(app["id"], bool(credential.get("username")), bool(credential.get("password")))
    custom = app.get("login")
    if not isinstance(custom, dict):
        return login
    for field in ("usernameSelector", "passwordSelector", "submitSelector", "preLoginSelector", "preLoginText", "submitText"):
        value = custom.get(field)
        if isinstance(value, str) and len(value) <= 1_024:
            login[field] = value
    for field in ("autoSubmit", "preLoginOnly"):
        if isinstance(custom.get(field), bool):
            login[field] = custom[field]
    return login


def public_app(app: dict) -> dict:
    credential = app.get("credential", {})
    has_username = bool(credential.get("username"))
    has_password = bool(credential.get("password"))
    result = {
        "id": app["id"],
        "name": app["name"],
        "url": app["url"],
        "avatar": app.get("avatar") or app["name"][:1],
        "color": app.get("color") if COLOR.fullmatch(app.get("color", "")) else default_color(app["id"]),
        "hasUsername": has_username,
        "hasPassword": has_password,
        "passwordMasked": "********" if has_password else "",
        "groupId": app.get("groupId") or default_group(app["id"]),
    }
    if credential:
        if credential.get("username"):
            result["username"] = unprotect(credential["username"])
        result["login"] = app_login(app)
    return result


def require_text(value: object, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"Invalid {field}")
    return value.strip()


def build_app(payload: dict, existing: dict | None, group_ids: set[str]) -> dict:
    raw_id = payload.get("id") if existing else None
    app_id = existing["id"] if existing else (raw_id or f"app-{uuid.uuid4().hex[:10]}")
    if not isinstance(app_id, str) or not APP_ID.fullmatch(app_id):
        raise ValueError("Invalid app id")

    name = require_text(payload.get("name"), "name", 80)
    url = require_text(payload.get("url"), "URL", 2048)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")

    avatar = str(payload.get("avatar") or name[:1]).strip()[:8] or name[:1]
    color = str(payload.get("color") or default_color(app_id)).strip()
    if not COLOR.fullmatch(color):
        raise ValueError("Invalid card color")

    group_id = payload.get("groupId") or (existing or {}).get("groupId") or default_group(app_id)
    if not isinstance(group_id, str) or group_id not in group_ids:
        raise ValueError("Invalid group")
    app = {"id": app_id, "name": name, "url": url, "avatar": avatar, "color": color, "groupId": group_id}
    credential = dict((existing or {}).get("credential", {}))
    if payload.get("clearCredentials") is True:
        credential = {}

    if "username" in payload:
        username = require_text(payload["username"], "username", 512)
        credential["username"] = protect(username)
    if "password" in payload:
        password = require_text(payload["password"], "password", 2048)
        credential["password"] = protect(password)

    if credential:
        app["credential"] = credential
        existing_login = (existing or {}).get("login")
        app["login"] = dict(existing_login) if isinstance(existing_login, dict) else default_login(app_id, bool(credential.get("username")), bool(credential.get("password")))
    return app


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalSSO/0.2"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def json(self, status: HTTPStatus, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 16_384:
            raise ValueError("Invalid request size")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Invalid request")
        return value

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path == "/api/apps":
            vault = load_vault()
            groups = ensure_groups(vault)
            self.json(HTTPStatus.OK, {"groups": groups, "apps": [public_app(app) for app in vault["apps"]]})
            return

        if path.startswith("/api/credentials/"):
            app_id = path.removeprefix("/api/credentials/")
            if not APP_ID.fullmatch(app_id):
                self.json(HTTPStatus.BAD_REQUEST, {"error": "Invalid app id"})
                return
            app = next((item for item in load_vault()["apps"] if item["id"] == app_id), None)
            if app is None or "credential" not in app or "login" not in app:
                self.json(HTTPStatus.NOT_FOUND, {"error": "No stored credential"})
                return
            credential = app["credential"]
            self.json(
                HTTPStatus.OK,
                {
                    "username": unprotect(credential["username"]) if credential.get("username") else "",
                    "password": unprotect(credential["password"]) if credential.get("password") else "",
                    "login": app_login(app),
                },
            )
            return

        requested = (PORTAL / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
        if PORTAL not in requested.parents and requested != PORTAL:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = requested.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(str(requested))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        try:
            payload = self.read_json()
            if path == "/api/groups":
                vault = load_vault()
                groups = ensure_groups(vault)
                group = {
                    "id": f"group-{uuid.uuid4().hex[:10]}",
                    "name": require_text(payload.get("name"), "group name", 40),
                    "color": default_color(uuid.uuid4().hex),
                }
                groups.append(group)
                save_vault(vault)
                self.json(HTTPStatus.OK, {"group": group})
                return

            if path == "/api/groups/reorder":
                vault = load_vault()
                groups = ensure_groups(vault)
                group_ids = payload.get("groupIds")
                if not isinstance(group_ids, list) or set(group_ids) != {group["id"] for group in groups}:
                    raise ValueError("Invalid group order")
                by_id = {group["id"]: group for group in groups}
                vault["groups"] = [by_id[group_id] for group_id in group_ids]
                save_vault(vault)
                self.json(HTTPStatus.OK, {"groups": vault["groups"]})
                return

            if path.startswith("/api/apps/") and path.endswith("/move"):
                app_id = path.removeprefix("/api/apps/").removesuffix("/move").rstrip("/")
                if not APP_ID.fullmatch(app_id):
                    raise ValueError("Invalid app id")
                vault = load_vault()
                groups = ensure_groups(vault)
                group_ids = {group["id"] for group in groups}
                group_id = payload.get("groupId")
                if not isinstance(group_id, str) or group_id not in group_ids:
                    raise ValueError("Invalid group")
                app = next((item for item in vault["apps"] if item["id"] == app_id), None)
                if app is None:
                    raise ValueError("Unknown app")
                app["groupId"] = group_id
                save_vault(vault)
                self.json(HTTPStatus.OK, {"app": public_app(app)})
                return

            if path != "/api/apps":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            vault = load_vault()
            groups = ensure_groups(vault)
            existing = next((app for app in vault["apps"] if app["id"] == payload.get("id")), None)
            if payload.get("id") and existing is None:
                raise ValueError("Unknown app")
            app = build_app(payload, existing, {group["id"] for group in groups})
            vault["apps"] = [item for item in vault["apps"] if item["id"] != app["id"]] + [app]
            save_vault(vault)
            self.json(HTTPStatus.OK, {"app": public_app(app)})
        except (ValueError, json.JSONDecodeError) as error:
            self.json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_DELETE(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if not path.startswith("/api/apps/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        app_id = path.removeprefix("/api/apps/")
        if not APP_ID.fullmatch(app_id):
            self.json(HTTPStatus.BAD_REQUEST, {"error": "Invalid app id"})
            return
        vault = load_vault()
        remaining = [app for app in vault["apps"] if app["id"] != app_id]
        if len(remaining) == len(vault["apps"]):
            self.json(HTTPStatus.NOT_FOUND, {"error": "Unknown app"})
            return
        vault["apps"] = remaining
        save_vault(vault)
        self.json(HTTPStatus.OK, {"deleted": app_id})


def main() -> None:
    print("Local SSO portal: http://127.0.0.1:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()


if __name__ == "__main__":
    main()
