# tests/test_cli.py
import pytest

from granoladb import auth, cli


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "token_cache_path", lambda: tmp_path / "token")
    monkeypatch.setattr(auth, "_keyring", lambda: None)  # force file backend in tests


def test_login_stores_token_from_arg(tmp_path, capsys):
    assert cli.main(["login", "TOKEN123"]) == 0
    assert (tmp_path / "token").read_text() == "TOKEN123"
    assert "logged in" in capsys.readouterr().out


def test_login_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GRANOLA_TOKEN", "ENVTOK")
    assert cli.main(["login"]) == 0
    assert (tmp_path / "token").read_text() == "ENVTOK"


def test_login_without_token_shows_usage(monkeypatch, capsys):
    monkeypatch.delenv("GRANOLA_TOKEN", raising=False)
    assert cli.main(["login"]) == 1
    assert "usage" in capsys.readouterr().err


def test_login_capture_uses_capture_module(tmp_path, monkeypatch):
    monkeypatch.setattr("granoladb.capture_macos.capture_token", lambda: "CAPTOK")
    assert cli.main(["login", "--capture"]) == 0
    assert (tmp_path / "token").read_text() == "CAPTOK"


def test_login_capture_reports_failure(monkeypatch, capsys):
    def boom():
        raise auth.GranolaAuthError("no token captured")

    monkeypatch.setattr("granoladb.capture_macos.capture_token", boom)
    assert cli.main(["login", "--capture"]) == 1
    assert "capture failed" in capsys.readouterr().err


def test_logout_removes_token(tmp_path):
    (tmp_path / "token").write_text("x")
    assert cli.main(["logout"]) == 0
    assert not (tmp_path / "token").exists()


def test_no_command_shows_usage(capsys):
    assert cli.main([]) == 1
    assert "usage" in capsys.readouterr().err
