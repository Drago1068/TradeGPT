import time
from pathlib import Path

import pytest

from tradegpt.worker_main import (
    _max_backoff_seconds,
    _poll_interval_seconds,
    _touch_heartbeat,
)


def test_poll_interval_defaults(monkeypatch):
    monkeypatch.delenv("TRADEGPT_WORKER_POLL_SECONDS", raising=False)
    assert _poll_interval_seconds() == 5.0


def test_poll_interval_rejects_invalid(monkeypatch):
    monkeypatch.setenv("TRADEGPT_WORKER_POLL_SECONDS", "nope")
    with pytest.raises(RuntimeError, match="must be numeric"):
        _poll_interval_seconds()


def test_poll_interval_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("TRADEGPT_WORKER_POLL_SECONDS", "0")
    with pytest.raises(RuntimeError, match="must be positive"):
        _poll_interval_seconds()


def test_max_backoff_defaults(monkeypatch):
    monkeypatch.delenv("TRADEGPT_WORKER_MAX_BACKOFF_SECONDS", raising=False)
    assert _max_backoff_seconds() == 300.0


def test_max_backoff_rejects_invalid(monkeypatch):
    monkeypatch.setenv("TRADEGPT_WORKER_MAX_BACKOFF_SECONDS", "nope")
    with pytest.raises(RuntimeError, match="must be numeric"):
        _max_backoff_seconds()


def test_max_backoff_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("TRADEGPT_WORKER_MAX_BACKOFF_SECONDS", "0")
    with pytest.raises(RuntimeError, match="must be positive"):
        _max_backoff_seconds()


def test_touch_heartbeat_updates_file(tmp_path: Path):
    heartbeat = tmp_path / "heartbeat"
    _touch_heartbeat(heartbeat)
    first_mtime = heartbeat.stat().st_mtime_ns
    time.sleep(0.001)
    _touch_heartbeat(heartbeat)
    assert heartbeat.exists()
    assert heartbeat.stat().st_mtime_ns >= first_mtime
