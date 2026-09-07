from fastapi.testclient import TestClient

from tradegpt.api import readiness_payload
from tradegpt.app import app, runtime


def test_readiness_reports_not_ready_for_safe_default_runtime():
    payload, ready = readiness_payload(
        engine=runtime.engine,
        market_data_configured=False,
        scan_plan_configured=False,
    )
    assert ready is False
    assert payload["status"] == "not_ready"
    assert payload["checks"]["database"]["ready"] is True
    assert payload["checks"]["schema"]["ready"] is True
    assert payload["checks"]["market_data"]["ready"] is False
    assert payload["checks"]["scan_plan"]["ready"] is False


def test_ready_endpoint_returns_503_when_runtime_is_not_operational():
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["status"] == "not_ready"
    assert body["detail"]["checks"]["database"]["ready"] is True
