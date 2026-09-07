from __future__ import annotations

import os
import signal
import threading
import time
from datetime import datetime, timezone

from .composition import build_runtime


def _poll_interval_seconds() -> float:
    raw = os.getenv("TRADEGPT_WORKER_POLL_SECONDS", "15")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("TRADEGPT_WORKER_POLL_SECONDS must be numeric") from exc
    if value <= 0:
        raise RuntimeError("TRADEGPT_WORKER_POLL_SECONDS must be positive")
    return value


def run_forever(*, poll_seconds: float | None = None) -> None:
    """Run the durable scheduler worker until SIGTERM/SIGINT.

    The worker only invokes the scan executor. It never places broker orders.
    """
    interval = poll_seconds if poll_seconds is not None else _poll_interval_seconds()
    if interval <= 0:
        raise ValueError("poll_seconds must be positive")

    runtime = build_runtime()
    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    while not stop.is_set():
        runtime.worker.run_due(datetime.now(timezone.utc))
        stop.wait(interval)


if __name__ == "__main__":
    run_forever()
