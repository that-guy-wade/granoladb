from granoladb import codec


def test_encode_decode_round_trip():
    records = [
        {"_id": "a", "_ts": "2026-08-27T10:00:00Z", "level": "ERROR", "svc": "api", "msg": "boom"},
        {"_id": "b", "_ts": "2026-08-27T10:00:01Z", "level": "INFO", "svc": "api", "msg": "ok"},
    ]
    title, body = codec.encode(records)
    assert title.startswith("[gdb] 2026-08-27T10:00:00Z ERROR api")
    assert codec.MARKER in body
    assert codec.decode(body) == records


def test_decode_ignores_non_gdb_documents():
    assert codec.decode("just a normal meeting about Q3 planning") is None
    assert codec.decode(None) is None
