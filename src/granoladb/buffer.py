import atexit
import threading


class Buffer:
    """Thread-safe record buffer. Flushes on size, timer, or explicit call."""

    def __init__(self, flush_fn, flush_size=50, flush_interval=5.0):
        self._flush_fn = flush_fn
        self._flush_size = flush_size
        self._flush_interval = flush_interval
        self._records = []
        self._lock = threading.Lock()
        self._timer = None
        atexit.register(self.flush)

    def add(self, record):
        with self._lock:
            self._records.append(record)
            due = len(self._records) >= self._flush_size
            self._ensure_timer_locked()
        if due:
            self.flush()

    def _ensure_timer_locked(self):
        if self._flush_interval and self._timer is None:
            self._timer = threading.Timer(self._flush_interval, self.flush)
            self._timer.daemon = True
            self._timer.start()

    def flush(self):
        with self._lock:
            batch = self._records
            self._records = []
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if batch:
            self._flush_fn(batch)
