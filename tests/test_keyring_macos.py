# tests/test_keyring_macos.py
import hashlib
import json

import pytest

from granoladb import keyring_macos as km
from granoladb.auth import GranolaAuthError


def _encrypt(key, plaintext):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = b"012345678901"
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def test_find_access_token_nested_and_json_string():
    # supabase.json shape: cognito_tokens is a JSON-encoded string
    data = {"cognito_tokens": json.dumps({"access_token": "TOK", "expires": 1})}
    assert km._find_access_token(data) == "TOK"


def test_find_access_token_deeply_nested():
    data = {"accounts": [{"session": {"accessToken": "DEEP"}}]}
    assert km._find_access_token(data) == "DEEP"


def test_find_access_token_absent_returns_none():
    assert km._find_access_token({"nope": {"still": "no"}}) is None


def test_gcm_round_trip_matches_app_framing():
    dek = bytes(range(32))
    blob = _encrypt(dek, b"hello")
    assert km._gcm_decrypt(blob, dek) == b"hello"


def test_resolve_dek_finds_the_right_derivation():
    secret = "c2VjcmV0LWtleS0xMjM0NTY3OA=="  # arbitrary base64 string
    # Encrypt with one of the candidate derivations (sha256 of the secret string).
    key = hashlib.sha256(secret.encode()).digest()
    blob = _encrypt(key, b'{"access_token":"X"}')
    assert km._resolve_dek(secret, blob) == key


def test_resolve_dek_raises_when_no_candidate_matches():
    blob = _encrypt(bytes(range(32)), b"data")  # key unrelated to the secret
    with pytest.raises(GranolaAuthError):
        km._resolve_dek("some-secret", blob)


def test_read_granola_token_end_to_end(tmp_path, monkeypatch):
    secret = "bXktc2FmZS1zdG9yYWdlLXNlY3JldA=="
    key = hashlib.pbkdf2_hmac("sha1", secret.encode(), km.SALT, 1003, 32)
    payload = json.dumps(
        {"cognito_tokens": json.dumps({"access_token": "REALTOK"})}
    ).encode()
    (tmp_path / "supabase.json.enc").write_bytes(_encrypt(key, payload))

    monkeypatch.setattr(km, "_read_keychain_secret", lambda: secret)
    assert km.read_granola_token(app_support=tmp_path) == "REALTOK"


def test_read_granola_token_missing_stores_raises(tmp_path):
    with pytest.raises(GranolaAuthError):
        km.read_granola_token(app_support=tmp_path)
