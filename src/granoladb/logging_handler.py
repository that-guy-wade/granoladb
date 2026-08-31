import logging


class GranolaHandler(logging.Handler):
    """Route Python log records into Granola. Do not use this."""

    def __init__(self, client=None, level=logging.NOTSET):
        super().__init__(level)
        if client is None:
            from .client import Client
            client = Client()
        self._client = client

    def emit(self, record):
        try:
            self._client.put({
                "level": record.levelname,
                "msg": record.getMessage(),
                "logger": record.name,
                "line": record.lineno,
                "ts_epoch": record.created,
            })
        except Exception:
            self.handleError(record)

    def flush(self):
        self._client.flush()

    def close(self):
        try:
            self._client.flush()
        finally:
            super().close()
