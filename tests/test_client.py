from granoladb import Client
from granoladb.backend import FakeBackend


def make_client():
    return Client(backend=FakeBackend(), flush_size=100, flush_interval=None)


def test_put_assigns_id_and_ts():
    db = make_client()
    rid = db.put({"level": "ERROR", "msg": "boom"})
    assert isinstance(rid, str) and rid
    row = db.get(rid)
    assert row["msg"] == "boom"
    assert row["_id"] == rid
    assert "_ts" in row


def test_query_round_trips_records():
    db = make_client()
    db.put({"level": "ERROR", "msg": "payment failed", "svc": "api"})
    db.put({"level": "INFO", "msg": "healthy", "svc": "api"})
    rows = db.query()
    assert {r["msg"] for r in rows} == {"payment failed", "healthy"}


def test_query_contains_filter():
    db = make_client()
    db.put({"msg": "payment failed"})
    db.put({"msg": "healthy"})
    rows = db.query(contains="payment")
    assert [r["msg"] for r in rows] == ["payment failed"]


def test_query_skips_non_gdb_documents():
    backend = FakeBackend()
    backend.create_document("Q3 planning", "a real meeting, not ours")
    db = Client(backend=backend, flush_size=100, flush_interval=None)
    db.put({"msg": "mine"})
    rows = db.query()
    assert [r["msg"] for r in rows] == ["mine"]
