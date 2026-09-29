import pytest

pytest.importorskip("opentelemetry.sdk.trace")

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from granoladb import GranolaSpanExporter, Client
from granoladb.backend import FakeBackend


def test_exporter_writes_spans_to_backend():
    db = Client(backend=FakeBackend(), flush_size=100, flush_interval=None)
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(GranolaSpanExporter(client=db)))
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("agent-step"):
        pass

    db.flush()
    rows = db.query()
    assert any(r.get("name") == "agent-step" and r.get("kind") == "span" for r in rows)
