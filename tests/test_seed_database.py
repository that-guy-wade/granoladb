import io

from examples import seed_database
from granoladb.backend_granola import GranolaBackend


def test_demo_calls_use_client_headers(monkeypatch):
    seen = []

    def fake_open(request, timeout):
        seen.append({key.lower(): value for key, value in request.headers.items()})
        return io.BytesIO(b"{}")

    monkeypatch.setattr(seed_database.urllib.request, "urlopen", fake_open)
    assert seed_database._call(GranolaBackend(token="AT"), "/v1/get-documents", {}) == (200, {})
    assert seen[0]["x-client-version"]
    assert seen[0]["x-client-platform"]


def test_demo_soft_deletes_only_matching_titles(monkeypatch):
    calls = []

    def fake_call(_backend, path, payload):
        calls.append((path, payload))
        if path == "/v1/get-documents":
            return 200, {"docs": [
                {"id": "target", "title": "users (table)"},
                {"id": "other", "title": "unrelated"},
            ]}
        return 200, {}

    monkeypatch.setattr(seed_database, "_call", fake_call)
    assert seed_database.delete_prior_demo_docs(None, {"users (table)"}) == 1
    assert [path for path, _ in calls] == [
        "/v1/get-documents", "/v1/update-document",
    ]
    assert calls[1][1]["id"] == "target"
    assert calls[1][1]["deleted_at"]
