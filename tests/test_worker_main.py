import pytest

from tradegpt.worker_main import _poll_interval_seconds


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
