# Engineering handoff

## Scope and data flow

The project is a Windows-only local convenience tool. A user enters an application URL, optional CSS selectors, and credentials in the portal. `server.py` protects supplied credentials through `crypto_dpapi.py` and writes them to private `vault.json`. The portal posts a launch request to the extension; the extension opens the saved URL, then its content script requests credentials from the loopback API and fills matching fields.

The public package has been sanitized. It contains a generic `example.com` host permission and synthetic example metadata only. It intentionally contains no private vault, real target URL, IP address, account, token, browser profile, log, or production data.

## Module contract

| Module | Responsibility |
| --- | --- |
| `server.py` | Serves portal files and CRUD endpoints. Binds `ThreadingHTTPServer` only to `127.0.0.1:8765`. |
| `crypto_dpapi.py` | Wraps `CryptProtectData` and `CryptUnprotectData`; values are Base64-encoded DPAPI blobs. |
| `setup_vault.py` | Prompts for one application entry and writes encrypted credentials. |
| `add_standard_apps.py` | Demonstrates a generic batch template; it has no real application definition. |
| `extension/background.js` | Tracks the portal-initiated tab and reads local API data. |
| `extension/login-fill.js` | Waits for configured selectors, sets fields, and optionally clicks submit. |
| `extension/portal-bridge.js` | Limits portal bridge messages to the local portal origin. |

## API and file contract

`vault.json` is private. Expected high-level JSON shape: `{ "version": 1, "groups": [], "apps": [] }`. An application contains `id`, `name`, `url`, display fields, optional `login` selectors, and an optional `credential` object whose `username` and `password` entries are DPAPI Base64 blobs. No plaintext credential is written by the normal server paths.

- `GET /api/apps` returns groups and safe application display data. It does not return usernames; it reports only `hasUsername` and a masked-password flag.
- `GET /api/credentials/{app-id}` returns decrypted values only to a local caller in the same Windows-user trust boundary.
- `POST /api/apps`, `POST /api/groups`, `POST /api/groups/reorder`, `POST /api/apps/{app-id}/move`, and `DELETE /api/apps/{app-id}` mutate the private vault.
- Invalid request JSON or invalid fields produce HTTP 400. Unknown application IDs return HTTP 404 where implemented.

## Verification status

| Item | Status | Evidence |
| --- | --- | --- |
| Python syntax of four Python modules | 已实际验证 | `py -3 -m py_compile ...` on Windows. |
| Server behavior with a synthetic no-credential vault | 已实际验证 | `tests/test_server.py` using a temporary vault path. |
| Manifest JSON parsing | 已实际验证 | PowerShell `ConvertFrom-Json`. |
| Real account login and selector compatibility | 未验证 | No real accounts or target websites are included or contacted. |
| Credential encryption/decryption against a user vault | 未验证 for this release | Must be exercised locally by the owner; real vaults are excluded from tests. |
| Resistance to malicious local processes | Not provided | This is not an audited credential manager; see `SECURITY.md`. |

## Safe next-AI instruction

Work only in a copy of this repository. Do not read, commit, print, or upload `vault.json`. For any authorized target, ask the owner to provide a non-secret URL and CSS selectors, narrow the manifest host permission to that target, then verify with a test account before enabling auto-submit.
