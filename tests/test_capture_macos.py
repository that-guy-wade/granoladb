# tests/test_capture_macos.py
import pytest

pytest.importorskip("mitmproxy")

from granoladb import capture_macos as cap


def _write_flow(path, requests):
    """requests: list of (host, headers dict). Writes a real mitmproxy flow file."""
    from mitmproxy.test import tflow, tutils
    from mitmproxy.io import FlowWriter
    with open(path, "wb") as fh:
        w = FlowWriter(fh)
        for host, headers in requests:
            req = tutils.treq(host=host)
            for k, v in headers.items():
                req.headers[k] = v
            w.add(tflow.tflow(req=req))


def test_latest_bearer_returns_most_recent(tmp_path):
    p = tmp_path / "f.mm"
    _write_flow(p, [
        ("1.2.3.4", {"Authorization": "Bearer OLD"}),
        ("1.2.3.4", {"Authorization": "Bearer NEW"}),
    ])
    assert cap._latest_bearer(str(p)) == "NEW"


def test_latest_bearer_none_when_no_auth(tmp_path):
    p = tmp_path / "f.mm"
    _write_flow(p, [("1.2.3.4", {"X-Thing": "y"})])
    assert cap._latest_bearer(str(p)) is None


def test_latest_bearer_missing_file():
    assert cap._latest_bearer("/no/such/file.mm") is None


def test_capture_token_rejects_non_macos(monkeypatch):
    monkeypatch.setattr(cap.sys, "platform", "linux")
    with pytest.raises(cap.GranolaAuthError):
        cap.capture_token()


def test_capture_token_cancelled_by_user(monkeypatch, tmp_path):
    # get past the platform / mitmdump guards, then decline consent
    monkeypatch.setattr(cap.sys, "platform", "darwin")
    fake = tmp_path / "mitmdump"
    fake.write_text("")
    monkeypatch.setattr(cap.shutil, "which", lambda _: str(fake))
    with pytest.raises(cap.GranolaAuthError, match="cancelled"):
        cap.capture_token(prompt=lambda *_: "n", out=lambda *_: None)
