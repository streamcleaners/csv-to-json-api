"""
Smoke tests for the FastAPI CSV-to-JSON API.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_datasets():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "datasets" in data
    assert "commodities" in data["datasets"]


def test_get_commodities():
    response = client.get("/api/commodities?_limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] <= 5
    assert "data" in data
    assert len(data["data"]) > 0


def test_get_single_record():
    response = client.get("/api/commodities/0")
    assert response.status_code == 200
    record = response.json()
    assert "commodity_code" in record


def test_404_unknown_dataset():
    response = client.get("/api/nonexistent")
    assert response.status_code == 404


def test_filtering():
    response = client.get("/api/commodities?declarable=true&_limit=3")
    assert response.status_code == 200
    data = response.json()
    for row in data["data"]:
        assert row["declarable"] is True


def test_field_projection():
    response = client.get("/api/commodities?_fields=commodity_code,description&_limit=2")
    assert response.status_code == 200
    data = response.json()
    for row in data["data"]:
        assert set(row.keys()) == {"commodity_code", "description"}


def test_record_out_of_range():
    response = client.get("/api/commodities/99999")
    assert response.status_code == 404


def test_reload():
    response = client.post("/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "commodities" in data["datasets_loaded"]
