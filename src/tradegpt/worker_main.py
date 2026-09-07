from __future__ import annotations

import logging
import os
import signal
import threading
from datetime import datetime, timezone

from .composition import build_runtime


logger = logging.getLogger(__name__)


def _poll_interval_seconds() -> float:
    raw = os.getenv("TRADEGPT_WORKER_POLL_SECONDS", "15")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("TRADEGPT_WORKER_POLL_SECONDS must be numeric") from exc
    if value <= 0:
        raise RuntimeError("TRADEGPT_WORKER_POLL_SECONDS must be positive")
    return value


def _max_backoff_seconds() -> float:
    raw = os.getenv("TRADEGPT_WORKER_MAX_BACKOFF_SECONDS", "300")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("TRADEGPT_WORKER_MAX_BACKOFF_SECONDS must be numeric") from exc
    if value <= 0:
        raise RuntimeError("TRADEGPT_WORKER_MAX_BACKOFF_SECONDS must be positive")
    return value


def run_forever(*, poll_seconds: float | None = None) -> None:
    """Run the durable scheduler worker until SIGTERM/SIGINT.

    The worker only invokes the scan executor. It never places broker orders.
    Transient polling failures are contained with bounded exponential backoff;
    a successful poll resets the backoff to the configured poll interval.
    """
    interval = poll_seconds if poll_seconds is not None else _poll_interval_seconds()
    if interval <= 0:
        raise ValueError("poll_seconds must be positive")
    max_backoff = _max_backoff_seconds()

    runtime = build_runtime()
    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("worker shutdown requested", extra={"signal": signum})
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    current_delay = interval
    while not stop.is_set():
        try:
            runtime.worker.run_due(datetime.now(timezone.utc))
            current_delay = interval
        except Exception:
            logger.exception("scheduler worker poll failed; retrying with backoff")
            current_delay = min(max_backoff, max(interval, current_delay * 2))
        stop.wait(current_delay)


if __name__ == "__main__":
    run_forever()
