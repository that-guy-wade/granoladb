from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class GranolaSpanExporter(SpanExporter):
    """Export OpenTelemetry spans to Granola. Your traces are now meetings."""

    def __init__(self, client=None):
        if client is None:
            from .client import Client
            client = Client()
        self._client = client

    def export(self, spans):
        try:
            for span in spans:
                ctx = span.get_span_context()
                self._client.put({
                    "kind": "span",
                    "name": span.name,
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                    "start": span.start_time,
                    "end": span.end_time,
                })
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def shutdown(self):
        self._client.flush()

    def force_flush(self, timeout_millis=30000):
        self._client.flush()
        return True
