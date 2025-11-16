# logx/config.py
import logging
import os
import queue
import sys
from logging.handlers import QueueHandler, QueueListener

from .filters import ContextFilter, DedupFilter, RedactFilter, SamplingFilter
from .formatters import DevFormatter, JsonFormatter

_listener: QueueListener | None = None


def configure_logging() -> None:
    """
    Configure root logging with a non-blocking queue, filters, and the selected formatter.

    Env vars:
      LOG_LEVEL=INFO|DEBUG|...
      LOG_FORMAT=json|dev
      LOG_SERVICE=app-name
      LOG_QUEUE_SIZE=10000
      LOG_DEDUP_WINDOW_MS=0  (disable by default)
      LOG_SAMPLE_DEFAULT=0.10  (default info sampling when frequency not set)
    """
    global _listener
    if _listener is not None:
        try:
            _listener.stop()
        except Exception:
            pass
        _listener = None

    # Root logger → Queue
    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    q = queue.Queue(maxsize=int(os.getenv("LOG_QUEUE_SIZE", "10000")))
    root.handlers[:] = [QueueHandler(q)]
    root.propagate = False

    # Sink on the listener side (single thread flush)
    fmt = os.getenv("LOG_FORMAT", "dev").lower()

    # Attach cross-cutting filters at root (applies to all loggers)
    if fmt != "dev":
        for f in (ContextFilter(), RedactFilter(), SamplingFilter(), DedupFilter()):
            root.addFilter(f)

    if fmt == "dev":
        sink = logging.StreamHandler(sys.stderr)
        sink.setFormatter(DevFormatter())
    else:
        sink = logging.StreamHandler(sys.stdout)
        sink.setFormatter(JsonFormatter())

    # Start listener thread
    _listener = QueueListener(q, sink, respect_handler_level=True)
    _listener.daemon = True
    _listener.start()

    # Make common noisy libs propagate into our root (single pipeline)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"):
        lg = logging.getLogger(name)
        lg.handlers[:] = []  # let them bubble to root
        lg.propagate = True
