from . import codec
from .backend import FakeBackend
from .client import Client

__version__ = "0.1.4"

__all__ = [
    "Client",
    "FakeBackend",
    "GranolaHandler",
    "GranolaSpanExporter",
    "GranolaAuthError",
    "codec",
]


def __getattr__(name):
    # Lazy imports so core has no hard dep on otel or the real backend at import time.
    if name == "GranolaHandler":
        from .logging_handler import GranolaHandler
        return GranolaHandler
    if name == "GranolaSpanExporter":
        from .otel import GranolaSpanExporter
        return GranolaSpanExporter
    if name == "GranolaAuthError":
        from .auth import GranolaAuthError
        return GranolaAuthError
    raise AttributeError(name)
