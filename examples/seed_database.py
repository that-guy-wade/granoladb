"""Seed a full GranolaDB 'database' demo into Granola.

Creates one folder containing:
  - table docs (users, orders) rendered as readable tables
  - per-service log docs (backend, frontend, auth, worker)

Every doc is written with real editor content (ydoc), so it shows up in Granola
AND is answerable by Granola's own AI. Re-running first deletes the previous demo
docs so it stays idempotent. Delete the folder (and its docs) to clean up.

Run:  granoladb login --capture   # fresh token
      python examples/seed_database.py
"""
import gzip
import json
import urllib.error
import urllib.request

from granoladb.backend_granola import GranolaBackend, BASE

FOLDER_TITLE = "GranolaDB (demo — safe to delete)"


def _call(be, path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {be._access()}", "Content-Type": "application/json"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=25).read()
    except urllib.error.HTTPError as e:
        return e.code, None
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return 200, (json.loads(raw) if raw.strip() else {})


def ensure_folder(be):
    _, meta = _call(be, "/v1/get-document-lists-metadata", {})
    lists = meta.get("lists", {}) if isinstance(meta, dict) else {}
    for key, m in lists.items():
        if isinstance(m, dict) and m.get("title") == FOLDER_TITLE:
            return m.get("id") or key
    import uuid
    lid = str(uuid.uuid4())
    _call(be, "/v1/create-document-list-v2",
          {"id": lid, "title": FOLDER_TITLE, "workspace_id": be._resolve_workspace()})
    return lid


def delete_prior_demo_docs(be, titles):
    _, r = _call(be, "/v1/get-documents", {})
    arr = r if isinstance(r, list) else (r.get("docs") or r.get("documents") or []) if isinstance(r, dict) else []
    n = 0
    for d in arr:
        if d.get("title") in titles:
            code, _ = _call(be, "/v1/hard-delete-document", {"document_id": d["id"]})
            if code == 200:
                n += 1
    return n


def table(title, headers, rows):
    widths = [max(len(str(x)) for x in [h] + [r[i] for r in rows]) for i, h in enumerate(headers)]
    def fmt(cells):
        return " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))
    lines = [title, "", fmt(headers)] + [fmt(r) for r in rows]
    return "\n".join(lines)


def main():
    be = GranolaBackend()
    be._resolve_workspace()

    docs = {
        "users (table)": table(
            "users (GranolaDB table)",
            ["id", "name", "email", "plan", "signup"],
            [[1, "Ada Lovelace", "ada@calc.io", "pro", "2026-01-04"],
             [2, "Alan Turing", "alan@enigma.uk", "free", "2026-02-11"],
             [3, "Grace Hopper", "grace@navy.mil", "pro", "2026-03-02"],
             [4, "Katherine Johnson", "kj@nasa.gov", "enterprise", "2026-03-19"]]),
        "orders (table)": table(
            "orders (GranolaDB table)",
            ["id", "user_id", "item", "amount", "status"],
            [[1001, 1, "Keyboard", "$89.00", "shipped"],
             [1002, 3, "Monitor", "$412.50", "shipped"],
             [1003, 2, "Mouse", "$24.99", "refunded"],
             [1004, 1, "Standing desk", "$611.00", "processing"],
             [1005, 4, "Webcam", "$78.25", "shipped"]]),
        "backend — logs": "\n".join([
            "backend service logs", "",
            "2026-08-30T09:01:02Z INFO  api      GET /v1/orders 200 (41ms)",
            "2026-08-30T09:01:04Z WARN  api      p99 latency 812ms exceeds 500ms target",
            "2026-08-30T09:01:07Z ERROR payments charge failed: card_declined user_id=2",
            "2026-08-30T09:01:09Z INFO  api      POST /v1/orders 201 order_id=1005",
            "2026-08-30T09:02:15Z ERROR db       connection pool exhausted (max=20)"]),
        "frontend — logs": "\n".join([
            "frontend service logs", "",
            "2026-08-30T09:00:59Z INFO  ui  route change /dashboard",
            "2026-08-30T09:01:03Z WARN  ui  slow render OrdersTable 240ms",
            "2026-08-30T09:01:05Z ERROR ui  Uncaught TypeError: cart is undefined (checkout.tsx:88)",
            "2026-08-30T09:01:12Z INFO  ui  user clicked 'retry payment'"]),
        "auth-service — logs": "\n".join([
            "auth-service logs", "",
            "2026-08-30T09:00:40Z INFO  auth login success user_id=1 mfa=totp",
            "2026-08-30T09:00:51Z WARN  auth 3 failed logins for alan@enigma.uk",
            "2026-08-30T09:01:00Z INFO  auth token refreshed user_id=3",
            "2026-08-30T09:03:22Z ERROR auth JWT signature verification failed"]),
        "worker-service — logs": "\n".join([
            "worker-service logs", "",
            "2026-08-30T09:00:10Z INFO  worker drained queue: 14,204 jobs overnight",
            "2026-08-30T09:01:30Z WARN  worker retrying job 88213 (attempt 3)",
            "2026-08-30T09:02:05Z ERROR worker job 88213 dead-lettered after 5 attempts",
            "2026-08-30T09:04:00Z INFO  worker nightly export uploaded to s3://reports/2026-08-30"]),
    }

    removed = delete_prior_demo_docs(be, set(docs) | {"ydoc-test: users"})
    print(f"cleaned up {removed} prior demo doc(s)")

    folder = ensure_folder(be)
    print(f"folder: {FOLDER_TITLE}")
    for title, body in docs.items():
        doc_id = be.create_document(title, body)
        _call(be, "/v1/add-document-to-list", {"document_list_id": folder, "document_id": doc_id})
        print(f"  + {title}")
    print("done — open the folder in Granola and query it with the AI.")


if __name__ == "__main__":
    main()
