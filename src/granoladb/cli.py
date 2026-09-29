"""`granoladb` command-line interface.

    granoladb login <TOKEN>   # cache a Granola access token (or set GRANOLA_TOKEN)
    granoladb login --auto    # experimental: decrypt the token from the local app
    granoladb logout          # forget the cached token

See the README for how to grab your Granola token.
"""
import os
import sys

from . import auth


def _cache_token(token):
    where = auth.store_token(token)
    print(
        f"granoladb: logged in. Token stored in {where} ({len(token)} chars).\n"
        "Your logs are now meetings."
    )
    return 0


def _login(args):
    if "--capture" in args:
        # Grab the token by intercepting Granola's own traffic (macOS).
        from .capture_macos import capture_token
        try:
            return _cache_token(capture_token())
        except auth.GranolaAuthError as exc:
            print(f"granoladb: capture failed: {exc}", file=sys.stderr)
            return 1
    if "--auto" in args:
        # Experimental: read + decrypt the token from the local Granola app.
        # Depends on Granola's on-disk crypto, which changes without notice.
        from .keyring_macos import read_granola_token
        try:
            return _cache_token(read_granola_token())
        except auth.GranolaAuthError as exc:
            print(f"granoladb: auto-login failed: {exc}", file=sys.stderr)
            return 1
    positional = [a for a in args if not a.startswith("-")]
    token = positional[0] if positional else os.environ.get("GRANOLA_TOKEN")
    if not token:
        print(
            "usage: granoladb login <TOKEN>       (or set GRANOLA_TOKEN)\n"
            "       granoladb login --capture     (macOS: grab it from the app)\n"
            "See the README for details.",
            file=sys.stderr,
        )
        return 1
    return _cache_token(token)


def _logout():
    if auth.clear_token():
        print("granoladb: logged out. Token removed.")
    else:
        print("granoladb: not logged in.")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else None
    if cmd == "login":
        return _login(argv[1:])
    if cmd == "logout":
        return _logout()
    print("usage: granoladb [login|logout]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
