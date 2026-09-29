import json
import time
import uuid

from . import codec
from .buffer import Buffer


class Client:
    def __init__(self, backend=None, flush_size=50, flush_interval=5.0):
        if backend is None:
            from .backend_granola import GranolaBackend
            backend = GranolaBackend()
        self._backend = backend
        self._buffer = Buffer(self._flush_batch, flush_size, flush_interval)

    def put(self, record):
        rec = dict(record)
        rec.setdefault("_id", uuid.uuid4().hex)
        rec.setdefault("_ts", _now_iso())
        self._buffer.add(rec)
        return rec["_id"]

    def flush(self):
        self._buffer.flush()

    def _flush_batch(self, batch):
        title, body = codec.encode(batch)
        self._backend.create_document(title, body)

    def query(self, after=None, contains=None):
        self.flush()
        out = []
        for doc in self._backend.get_documents(after=after):
            recs = codec.decode(doc.get("body"))
            if recs is None:
                continue
            out.extend(recs)
        if contains is not None:
            out = [r for r in out if contains in json.dumps(r)]
        if after is not None:
            out = [r for r in out if r.get("_ts", "") >= after]
        return out

    def get(self, record_id):
        for r in self.query():
            if r.get("_id") == record_id:
                return r
        return None


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
