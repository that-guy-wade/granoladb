"""Extract the Granola access token from the local macOS install.

Reverse-engineered from the desktop app (see docs/granola-internal-api.md):
- The 32-byte data key (DEK) lives in the macOS Keychain as a generic password
  under service `com.granola.app.dek`.
- The auth stores (`supabase.json.enc`, `stored-accounts.json.enc`) are
  AES-256-GCM: `nonce(12) || ciphertext || tag(16)`, encrypted with the DEK.

macOS only. Fragile by nature — Granola changes this scheme periodically.
"""
import base64
import binascii
import hashlib
import json
import subprocess
from pathlib import Path

from .auth import GranolaAuthError

KEYCHAIN_SERVICE = "Granola Safe Storage"
KEYCHAIN_ACCOUNT = "Granola Key"
APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Granola"
TOKEN_STORES = ("supabase.json.enc", "stored-accounts.json.enc")
NONCE_LEN = 12
TAG_LEN = 16
# Chromium/Electron safeStorage KDF salt.
SALT = b"saltysalt"


def _read_keychain_secret():
    """Return the raw Granola safeStorage secret string (prompts the user)."""
    proc = subprocess.run(
        ["security", "find-generic-password", "-w",
         "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise GranolaAuthError(
            "could not read the Granola key from your Keychain "
            f"(service {KEYCHAIN_SERVICE!r}, account {KEYCHAIN_ACCOUNT!r}): "
            f"{proc.stderr.strip() or 'denied'}"
        )
    return proc.stdout.strip()


def _candidate_keys(secret):
    """Yield plausible 32-byte AES-256-GCM keys derived from the keychain secret.

    The app derives the data key inside a compiled module, so instead of reversing
    it we try the standard derivations and let the GCM auth tag confirm the winner.
    """
    s = secret.encode()
    yield hashlib.pbkdf2_hmac("sha1", s, SALT, 1003, 32)
    yield hashlib.sha256(s).digest()
    # The secret string itself may be the key (24 chars = AES-192).
    if len(s) in (16, 24, 32):
        yield s
    try:
        raw = base64.b64decode(secret, validate=True)
    except (binascii.Error, ValueError):
        raw = None
    if raw is not None:
        # Decoded bytes may be the key directly (16 = AES-128, 24/32 too).
        if len(raw) in (16, 24, 32):
            yield raw
        yield hashlib.sha256(raw).digest()
        yield hashlib.pbkdf2_hmac("sha1", raw, SALT, 1003, 32)
        yield hashlib.pbkdf2_hmac("sha256", raw, SALT, 1003, 32)
        yield hashlib.pbkdf2_hmac("sha1", raw, SALT, 1003, 16)
        if len(raw) == 16:
            yield raw + raw


def _gcm_decrypt(blob, dek):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = blob[:NONCE_LEN]
    ct_and_tag = blob[NONCE_LEN:]  # cryptography expects ciphertext||tag
    return AESGCM(dek).decrypt(nonce, ct_and_tag, None)


def _resolve_dek(secret, sample_blob):
    """Find the working 32-byte key by trying derivations against a real store.

    A wrong key fails the GCM auth tag, so the one that decrypts is correct.
    """
    from cryptography.exceptions import InvalidTag
    for key in _candidate_keys(secret):
        try:
            _gcm_decrypt(sample_blob, key)
            return key
        except InvalidTag:
            continue
        except Exception:  # noqa: BLE001 - wrong key can fail in other ways
            continue
    raise GranolaAuthError(
        "could not derive the Granola data key from the Keychain secret; "
        "the app likely changed its key derivation"
    )


def _find_access_token(obj):
    """Recursively find an access-token value, descending into JSON-string values."""
    if isinstance(obj, str):
        s = obj.strip()
        if s[:1] in ("{", "["):
            try:
                return _find_access_token(json.loads(s))
            except json.JSONDecodeError:
                return None
        return None
    if isinstance(obj, dict):
        for key in ("access_token", "accessToken"):
            val = obj.get(key)
            if isinstance(val, str) and val:
                return val
        for val in obj.values():
            found = _find_access_token(val)
            if found:
                return found
    if isinstance(obj, list):
        for val in obj:
            found = _find_access_token(val)
            if found:
                return found
    return None


def read_granola_token(app_support=None):
    """Decrypt the local Granola auth store and return the access token."""
    base = Path(app_support) if app_support else APP_SUPPORT
    stores = [base / name for name in TOKEN_STORES if (base / name).exists()]
    if not stores:
        raise GranolaAuthError(f"no Granola auth store found in {base}")

    secret = _read_keychain_secret()
    dek = _resolve_dek(secret, stores[0].read_bytes())

    for path in stores:
        try:
            data = json.loads(_gcm_decrypt(path.read_bytes(), dek))
        except Exception:  # noqa: BLE001 - skip a store we can't parse
            continue
        token = _find_access_token(data)
        if token:
            return token
    raise GranolaAuthError(
        "decrypted the Granola auth store but found no access token"
    )
