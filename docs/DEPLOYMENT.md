# Windows installation and deployment

## 1. Install or verify Python

In PowerShell, verify a supported interpreter:

```powershell
py -3 --version
```

The code has no third-party dependency. No `pip install` step is required.

## 2. Obtain the source

```powershell
git clone https://github.com/bigSnake133/LocalSSO.git
Set-Location .\LocalSSO
Copy-Item .\vault.example.json .\vault.json
```

`vault.example.json` contains no usable credential. The copied `vault.json` is a local starting structure and is ignored by Git.

## 3. Limit file access

Place the directory in a location only your Windows account can access. For a private vault file, verify its ACL:

```powershell
icacls .\vault.json
```

If your organization permits it, remove inherited permissions and grant access only to the current user after confirming the exact target file:

```powershell
$vault = (Resolve-Path .\vault.json).Path
icacls $vault /inheritance:r
icacls $vault /grant:r "${env:USERNAME}:(R,W)"
icacls $vault
```

This command changes file permissions. Do not run it for a shared vault or an account that needs access by another user; preserve the permissions required by your backup/recovery process.

## 4. Configure the browser extension

Before loading the extension, edit `extension/manifest.json`.

- Keep `http://127.0.0.1:8765/*`.
- Replace the two `https://example.com/*` entries with the same exact, authorized site pattern, for example `https://login.example.org/*`.
- Do not use a wildcard that grants all sites access.

Then load the `extension` directory as an unpacked extension through the browser extension page and reload it after every manifest edit.

## 5. Start and test

```powershell
py -3 -m unittest discover -s tests -v
py -3 .\server.py
```

Open `http://127.0.0.1:8765`, add a test application, then launch it from the portal. Confirm that the browser extension sees the page only on the host permission you configured.

## 6. Update

1. Stop the local service with `Ctrl+C`.
2. Back up `vault.json` to a private location.
3. Run `git pull --ff-only` in the repository.
4. Recheck `extension/manifest.json` before reloading the extension, because changes to host permissions are security-relevant.
5. Start the service and perform the test in step 5.

## Backup and recovery

- Back up `vault.json` only in encrypted storage controlled by the same Windows user.
- A DPAPI-protected vault is normally not portable to another Windows user or a clean profile.
- To restore, stop the server and replace `vault.json` with its private backup, then start the server. Do not commit the backup.
- If the vault cannot be decrypted, recreate affected credentials interactively. The repository does not contain a recovery key.

## Diagnostics

| Symptom | Check |
| --- | --- |
| Portal says service is not running | Run `py -3 .\\server.py`, then open the exact loopback URL. |
| Extension does not react | Verify Developer mode, reload the unpacked extension, refresh the portal. |
| Page does not fill | Verify the exact host permission and the CSS selectors; disable auto-submit while diagnosing. |
| Credential cannot decrypt | Confirm the same Windows user created the vault; restore a private backup or recreate the credential. |

The standard command shell alternative is Git Bash: use `python server.py`, `cp vault.example.json vault.json`, and `git` commands with forward-slash paths. The program itself remains Windows-only because it calls Windows DPAPI.
