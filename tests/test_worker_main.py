import pytest

from tradegpt.worker_main import _max_backoff_seconds, _poll_interval_seconds


def test_poll_interval_defaults(monkeypatch):
    monkeypatch.delenv("TRADEGPT_WORKER_POLL_SECONDS", raising=False)
    assert _poll_interval_seconds() == 15.0


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
