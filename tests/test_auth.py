# tests/test_auth.py
import pytest

from granoladb import auth
from granoladb.auth import GranolaAuthError


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    # Never touch the real OS keychain or the user's real cache during tests.
    monkeypatch.setattr(auth, "token_cache_path", lambda: tmp_path / "token")
    monkeypatch.setattr(auth, "_keyring", lambda: None)


def test_env_token_is_returned(monkeypatch):
    monkeypatch.setenv("GRANOLA_TOKEN", "AT")
    assert auth.get_access_token() == "AT"


def test_cached_file_token_when_env_absent(monkeypatch, tmp_path):
    monkeypatch.delenv("GRANOLA_TOKEN", raising=False)
    (tmp_path / "token").write_text("CACHED\n")
    assert auth.get_access_token() == "CACHED"


def test_env_takes_precedence_over_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("GRANOLA_TOKEN", "ENVTOK")
    (tmp_path / "token").write_text("CACHED")
    assert auth.get_access_token() == "ENVTOK"


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("GRANOLA_TOKEN", raising=False)
    with pytest.raises(GranolaAuthError):
        auth.get_access_token()


class _FakeKeyring:
    def __init__(self):
        self.store = {}

    def set_password(self, service, account, value):
        self.store[(service, account)] = value

    def get_password(self, service, account):
        return self.store.get((service, account))

    def delete_password(self, service, account):
        del self.store[(service, account)]


def test_keychain_roundtrip_preferred_over_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GRANOLA_TOKEN", raising=False)
    fake = _FakeKeyring()
    monkeypatch.setattr(auth, "_keyring", lambda: fake)
    label = auth.store_token("KCTOK")
    assert "keychain" in label
    assert (fake.store[(auth.KEYRING_SERVICE, auth.KEYRING_ACCOUNT)]) == "KCTOK"
    assert not (tmp_path / "token").exists()  # nothing written to disk
    assert auth.get_access_token() == "KCTOK"


def test_clear_token_removes_keychain_and_file(monkeypatch, tmp_path):
    fake = _FakeKeyring()
    monkeypatch.setattr(auth, "_keyring", lambda: fake)
    auth.store_token("X")
    assert auth.clear_token() is True
    assert auth.get_access_token.__name__  # sanity
    monkeypatch.delenv("GRANOLA_TOKEN", raising=False)
    with pytest.raises(GranolaAuthError):
        auth.get_access_token()


def test_store_falls_back_to_file_without_keychain(tmp_path):
    # isolate_storage already forces _keyring() -> None
    label = auth.store_token("FILETOK")
    assert "0600" in label
    assert (tmp_path / "token").read_text() == "FILETOK"
