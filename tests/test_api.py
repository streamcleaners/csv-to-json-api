"""Tests for the FastAPI endpoints."""

import pytest


class TestRootEndpoint:
    def test_lists_datasets(self, test_client):
        resp = test_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "products" in data["datasets"]
        info = data["datasets"]["products"]
        assert info["records"] == 3
        assert "name" in info["columns"]

    def test_endpoint_path(self, test_client):
        resp = test_client.get("/")
        info = resp.json()["datasets"]["products"]
        assert info["endpoint"] == "/api/products"


class TestGetCollection:
    def test_returns_all_records(self, test_client):
        resp = test_client.get("/api/products")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["count"] == 3
        assert len(body["data"]) == 3

    def test_pagination_limit(self, test_client):
        resp = test_client.get("/api/products?_limit=2")
        body = resp.json()
        assert body["count"] == 2
        assert body["total"] == 3

    def test_pagination_offset(self, test_client):
        resp = test_client.get("/api/products?_limit=2&_offset=2")
        body = resp.json()
        assert body["count"] == 1
        assert body["offset"] == 2

    def test_field_projection(self, test_client):
        resp = test_client.get("/api/products?_fields=name,price")
        body = resp.json()
        row = body["data"][0]
        assert set(row.keys()) == {"name", "price"}

    def test_column_filter(self, test_client):
        resp = test_client.get("/api/products?available=true")
        body = resp.json()
        assert body["total"] == 2
        assert all(r["available"] is True for r in body["data"])

    def test_404_unknown_dataset(self, test_client):
        resp = test_client.get("/api/nonexistent")
        assert resp.status_code == 404


class TestGetRecord:
    def test_get_by_index(self, test_client):
        resp = test_client.get("/api/products/0")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Widget"

    def test_index_out_of_range(self, test_client):
        resp = test_client.get("/api/products/99")
        assert resp.status_code == 404

    def test_unknown_dataset(self, test_client):
        resp = test_client.get("/api/nonexistent/0")
        assert resp.status_code == 404


class TestReload:
    def test_reload_returns_ok(self, test_client):
        resp = test_client.post("/reload")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
