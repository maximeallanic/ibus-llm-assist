# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub: *Security* tab, *Report a vulnerability* (private
vulnerability reporting). Do not open a public issue. Include the version (`ibus-llm-assist --version`), your
distribution and what an attacker can do. You will get an answer within a week.

## What is in scope

An input method sees everything you type, so these are the promises that matter:

- **Typing goes only to the configured server**, which is 127.0.0.1 by default. Nothing is written to disk or logged.
  The engine never runs in password, PIN, private or hidden-text fields, nor in terminals.
- **The local server is not reachable from other machines or from web pages**: it listens on 127.0.0.1 and its CORS
  answer allows only `localhost` origins, without credentials.
- **Pinned and verified downloads.** llama.cpp and the model are fetched at fixed versions and checked against a
  sha256 before use; a mismatch stops the install. The one-line bootstrap downloads its release over HTTPS only
  and checks it against the sha256 pinned in `install.sh` before unpacking it.
- **Root only where needed, after asking**: the package manager and the copy of the engine's files. The engine and
  the server run as you.
- **Removal is exact**: `uninstall.sh` removes only the files listed in the manifest, and refuses any path outside
  the places the installer writes to.
- **The API key file** is ignored if other users can read it.

Reports of a way to make the engine send text elsewhere, run in a field it should skip, or the installer write or
remove files it should not, are especially welcome.

## Out of scope

Vulnerabilities in llama.cpp, the model, IBus, GNOME or GTK: report them to those projects. Tell us if a pinned
version has a known issue so that we can move the pin.

## Supported versions

Only the latest release.
