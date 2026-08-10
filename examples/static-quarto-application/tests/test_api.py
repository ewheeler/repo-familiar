from fastapi.testclient import TestClient

from static_quarto_application.api import create_app


def test_analyze_endpoint_uses_shared_deterministic_analysis() -> None:
    client = TestClient(create_app(static_root=None))

    response = client.post(
        "/api/v1/analyze",
        json={"category": "beta", "minimum_value": 10},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "beta"
    assert response.json()["count"] == 2
    assert response.json()["total"] == 36
    assert response.json()["average"] == 18.0
    assert len(response.json()["input_sha256"]) == 64
    assert len(response.json()["config_sha256"]) == 64


def test_health_endpoint_reports_ready() -> None:
    client = TestClient(create_app(static_root=None))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_rejects_negative_threshold() -> None:
    client = TestClient(create_app(static_root=None))

    response = client.post(
        "/api/v1/analyze",
        json={"category": "all", "minimum_value": -1},
    )

    assert response.status_code == 422
