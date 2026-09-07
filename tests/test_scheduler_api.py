from datetime import datetime

from fastapi.testclient import TestClient

from tradegpt import app as app_module
from tradegpt.scheduler import PRODUCTION_SCAN_IDS
from tradegpt.scan_audit import ScanRun


class FakeSchedulerService:
    def __init__(self):
        self.calls = []

    def status(self, now=None):
        return type("Status", (), {"timezone": "America/New_York", "next_scan_id": "primary-qualification", "next_run_at": datetime(2026, 9, 7, 10, 15), "scans": [{"id": "daily-discovery", "label": "Daily Sniper Discovery", "time_et": "08:00"}]})()

    def due(self, now=None):
        return []

    def start(self, scan_id, scheduled_at, started_at=None):
        if scan_id not in PRODUCTION_SCAN_IDS:
            raise KeyError(f"unknown production scan: {scan_id}")
        self.calls.append(("start", scan_id))
        return ScanRun(scan_id, scheduled_at, started_at or scheduled_at, status="STARTED")

    def complete(self, run, completed_at=None):
        if run.scan_id not in PRODUCTION_SCAN_IDS:
            raise KeyError(f"unknown production scan: {run.scan_id}")
        self.calls.append(("complete", run.scan_id))
        return ScanRun(run.scan_id, run.scheduled_at, run.started_at, completed_at or run.started_at, "COMPLETED")

    def fail(self, run, error, failed_at=None):
        if run.scan_id not in PRODUCTION_SCAN_IDS:
            raise KeyError(f"unknown production scan: {run.scan_id}")
        self.calls.append(("fail", run.scan_id))
        return ScanRun(run.scan_id, run.scheduled_at, run.started_at, failed_at or run.started_at, "FAILED", error)

    def missed(self, scan_id, scheduled_at, detected_at=None):
        if scan_id not in PRODUCTION_SCAN_IDS:
            raise KeyError(f"unknown production scan: {scan_id}")
        self.calls.append(("missed", scan_id))


def test_scheduler_status_endpoint(monkeypatch):
    fake = FakeSchedulerService()
    monkeypatch.setattr(app_module, "scheduler_service", fake)
    response = TestClient(app_module.app).get("/api/v1/scheduler", params={"now": "2026-09-07T13:00:00Z"})
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "America/New_York"
    assert body["next_run"]["scan_id"] == "primary-qualification"


def test_scheduler_due_endpoint(monkeypatch):
    fake = FakeSchedulerService()
    monkeypatch.setattr(app_module, "scheduler_service", fake)
    response = TestClient(app_module.app).get("/api/v1/scheduler/due", params={"now": "2026-09-07T13:00:00Z"})
    assert response.status_code == 200
    assert response.json()["due"] == []


def test_scheduler_run_lifecycle_endpoints(monkeypatch):
    fake = FakeSchedulerService()
    monkeypatch.setattr(app_module, "scheduler_service", fake)
    client = TestClient(app_module.app)
    scheduled = "2026-09-07T12:00:00+00:00"
    started = "2026-09-07T12:01:00+00:00"

    response = client.post("/api/v1/scheduler/runs/daily-discovery/start", json={"scheduled_at": scheduled, "started_at": started})
    assert response.status_code == 200
    assert response.json()["status"] == "STARTED"

    response = client.post("/api/v1/scheduler/runs/daily-discovery/complete", json={"scheduled_at": scheduled, "started_at": started})
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert fake.calls == [("start", "daily-discovery"), ("complete", "daily-discovery")]


def test_scheduler_unknown_scan_returns_404(monkeypatch):
    fake = FakeSchedulerService()
    monkeypatch.setattr(app_module, "scheduler_service", fake)
    response = TestClient(app_module.app).post("/api/v1/scheduler/runs/not-a-production-scan/start", json={"scheduled_at": "2026-09-07T12:00:00+00:00"})
    assert response.status_code == 404
