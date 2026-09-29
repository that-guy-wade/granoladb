import logging

from granoladb import GranolaHandler, Client
from granoladb.backend import FakeBackend


def test_handler_writes_log_records_to_backend():
    db = Client(backend=FakeBackend(), flush_size=100, flush_interval=None)
    handler = GranolaHandler(client=db)
    logger = logging.getLogger("test.granoladb")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    logger.error("payment failed")
    handler.flush()

    rows = db.query()
    assert len(rows) == 1
    assert rows[0]["level"] == "ERROR"
    assert rows[0]["msg"] == "payment failed"
    assert rows[0]["logger"] == "test.granoladb"


def test_handler_never_raises_into_host_app(monkeypatch):
    db = Client(backend=FakeBackend(), flush_size=100, flush_interval=None)
    handler = GranolaHandler(client=db)

    def boom(_record):
        raise RuntimeError("granola down")

    monkeypatch.setattr(db, "put", boom)
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hi", None, None)
    # Must not raise:
    handler.emit(record)
