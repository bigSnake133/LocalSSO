# Security policy and operating limits

## Supported use

LocalSSO is intended only for a single, trusted Windows user operating authorized accounts on that user's own workstation. It uses Windows DPAPI to protect the credential fields stored in `vault.json` at rest.

## Important limitations

- The HTTP server accepts requests on `127.0.0.1:8765` only; do not change it to a LAN or public address.
- There is no separate per-request authentication layer for local processes. Software running as the same Windows user is within the local trust boundary.
- The browser extension receives credentials from the loopback API only while filling an authorized page launched from the portal. The credentials nevertheless exist in browser memory while that operation runs.
- DPAPI ties protected values to the Windows user profile. It is not a substitute for protecting an unlocked Windows session, backups, or malware-compromised devices.
- `vault.json` may contain encrypted credential blobs plus metadata such as application names and URLs. Treat the whole file as private.

## Required handling

- Keep `vault.json` private and untracked. The supplied `.gitignore` excludes it.
- Do not store real credentials, URLs, private IPs, cookies, tokens, logs, browser profiles, or copied vaults in this repository.
- Restrict file access to the owning Windows user. Do not place the project in a shared folder.
- Grant extension host permissions only for exact domains you are authorized to use.
- Use OS updates, browser updates, a screen lock, and a separate audited password manager when stronger protection is required.

## Reporting

Do not open a public issue containing secrets or private infrastructure details. Remove or replace such data with synthetic placeholders before reporting a problem.
