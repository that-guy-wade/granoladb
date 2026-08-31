# tests/test_backend_granola.py
import io
import json

from granoladb.backend_granola import GranolaBackend


def fake_http_factory(responses):
    calls = []

    def fake_http(req):
        calls.append((req.full_url, json.loads(req.data)))
        return io.BytesIO(json.dumps(responses.pop(0)).encode())

    fake_http.calls = calls
    return fake_http


def test_create_document_creates_skeleton_then_fills_content(monkeypatch):
    monkeypatch.delenv("GRANOLADB_DRY_RUN", raising=False)
    # Sequence: get-workspaces -> create-document -> update-document
    http = fake_http_factory([
        {"workspaces": [{"workspace": {"workspace_id": "ws-1"}}]},
        {"id": "server-echo"},
        {"id": "server-echo"},
    ])
    b = GranolaBackend(token="AT", http=http)
    doc_id = b.create_document("[gdb] t ERROR api", "the body")
    assert isinstance(doc_id, str) and doc_id

    ws_url, _ = http.calls[0]
    assert ws_url == "https://api.granola.ai/v1/get-workspaces"

    create_url, create_body = http.calls[1]
    assert create_url == "https://api.granola.ai/v1/create-document"
    assert create_body["id"] == doc_id
    assert create_body["type"] == "meeting"
    assert create_body["workspace_id"] == "ws-1"

    update_url, update_body = http.calls[2]
    assert update_url == "https://api.granola.ai/v1/update-document"
    assert update_body["id"] == doc_id
    assert update_body["title"] == "[gdb] t ERROR api"
    assert update_body["notes_plain"] == "the body"
    assert update_body["notes_markdown"] == "the body"


def test_workspace_id_is_cached_across_writes(monkeypatch):
    monkeypatch.delenv("GRANOLADB_DRY_RUN", raising=False)
    http = fake_http_factory([
        {"workspaces": [{"workspace": {"workspace_id": "ws-1"}}]},
        {}, {},   # first write: create + update
        {}, {},   # second write: create + update (no second get-workspaces)
    ])
    b = GranolaBackend(token="AT", http=http)
    b.create_document("a", "1")
    b.create_document("b", "2")
    urls = [c[0] for c in http.calls]
    assert urls.count("https://api.granola.ai/v1/get-workspaces") == 1


def test_get_documents_normalizes_shape(monkeypatch):
    monkeypatch.delenv("GRANOLADB_DRY_RUN", raising=False)
    http = fake_http_factory([
        {"docs": [{"id": "d1", "title": "t", "notes_markdown": "GRANOLADB v1\nbody"}]}
    ])
    b = GranolaBackend(token="AT", http=http)
    docs = b.get_documents()
    assert http.calls[0][0] == "https://api.granola.ai/v1/get-documents"
    assert docs == [{"id": "d1", "title": "t", "body": "GRANOLADB v1\nbody"}]


def test_dry_run_skips_network(monkeypatch):
    monkeypatch.setenv("GRANOLADB_DRY_RUN", "1")

    def explode(_req):
        raise AssertionError("network called in dry run")

    b = GranolaBackend(token="AT", http=explode)
    assert b.create_document("t", "body")  # returns a generated id, no network
