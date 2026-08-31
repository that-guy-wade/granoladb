# src/granoladb/auth.py
import os
from pathlib import Path

ENV_VAR = "GRANOLA_TOKEN"
KEYRING_SERVICE = "granoladb"
KEYRING_ACCOUNT = "granola-token"


class GranolaAuthError(RuntimeError):
    pass


def token_cache_path():
    """Legacy plaintext fallback, used only when no OS keychain is available."""
    return Path.home() / ".granoladb" / "token"


def _keyring():
    """Return the keyring module if a real (non-fail) backend is available."""
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring
        if isinstance(keyring.get_keyring(), FailKeyring):
            return None
        return keyring
    except Exception:  # noqa: BLE001 - any keyring problem => fall back to file
        return None


def store_token(token):
    """Persist the token in the OS keychain if possible, else a 0600 file.

    Returns a short label of where it was stored.
    """
    kr = _keyring()
    if kr is not None:
        try:
            kr.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, token)
            return "your OS keychain"
        except Exception:  # noqa: BLE001
            pass
    path = token_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token)
    path.chmod(0o600)
    return f"{path} (no keychain available; plaintext, 0600)"


def clear_token():
    """Remove the token from the keychain and/or the legacy file."""
    removed = False
    kr = _keyring()
    if kr is not None:
        try:
            kr.delete_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
            removed = True
        except Exception:  # noqa: BLE001 - not stored / no backend
            pass
    path = token_cache_path()
    if path.exists():
        path.unlink()
        removed = True
    return removed


def get_access_token():
    """Return the Granola access token.

    Resolution order: GRANOLA_TOKEN env var -> OS keychain -> legacy 0600 file.
    """
    env = os.environ.get(ENV_VAR)
    if env:
        return env
    kr = _keyring()
    if kr is not None:
        try:
            token = kr.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
            if token:
                return token
        except Exception:  # noqa: BLE001
            pass
    path = token_cache_path()
    if path.exists():
        cached = path.read_text().strip()
        if cached:
            return cached
    raise GranolaAuthError(
        f"no Granola token found. Set {ENV_VAR}, or run `granoladb login --capture` "
        "(have you tried taking more meetings?)"
    )
