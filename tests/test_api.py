"""Tests for the FastAPI CSV-to-JSON API."""

from fastapi.testclient import TestClient

from app.main import app, datasets

client = TestClient(app)


# ── Discovery ──────────────────────────────────────────────────────────────


class TestRoot:
    def test_returns_datasets(self):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "datasets" in body
        assert "commodities" in body["datasets"]

    def test_dataset_info_has_expected_keys(self):
        resp = client.get("/")
        info = resp.json()["datasets"]["commodities"]
        assert "records" in info
        assert "columns" in info
        assert "endpoint" in info
        assert info["endpoint"] == "/api/commodities"


# ── Collection queries ─────────────────────────────────────────────────────


class TestGetCollection:
    def test_returns_data(self):
        resp = client.get("/api/commodities?_limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] <= 5
        assert len(body["data"]) > 0

    def test_pagination_limit(self):
        resp = client.get("/api/commodities?_limit=2")
        body = resp.json()
        assert body["count"] == 2
        assert body["limit"] == 2

    def test_pagination_offset(self):
        resp = client.get("/api/commodities?_limit=2&_offset=2")
        body = resp.json()
        assert body["offset"] == 2
        assert body["count"] <= 2

    def test_offset_beyond_total_returns_empty(self):
        resp = client.get("/api/commodities?_offset=999999")
        body = resp.json()
        assert body["count"] == 0
        assert body["data"] == []

    def test_field_projection(self):
        resp = client.get("/api/commodities?_fields=commodity_code,description&_limit=2")
        body = resp.json()
        for row in body["data"]:
            assert set(row.keys()) == {"commodity_code", "description"}

    def test_column_filter(self):
        resp = client.get("/api/commodities?declarable=true&_limit=5")
        body = resp.json()
        for row in body["data"]:
            assert row["declarable"] is True

    def test_multiple_filters(self):
        resp = client.get("/api/commodities?declarable=true&leaf=true&_limit=5")
        body = resp.json()
        for row in body["data"]:
            assert row["declarable"] is True
            assert row["leaf"] is True

    def test_filter_no_match(self):
        resp = client.get("/api/commodities?description=zzz_no_match_zzz")
        body = resp.json()
        assert body["total"] == 0
        assert body["data"] == []

    def test_404_unknown_dataset(self):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404


# ── Single record ──────────────────────────────────────────────────────────


class TestGetRecord:
    def test_get_by_index(self):
        resp = client.get("/api/commodities/0")
        assert resp.status_code == 200
        assert "commodity_code" in resp.json()

    def test_index_out_of_range(self):
        resp = client.get("/api/commodities/99999")
        assert resp.status_code == 404

    def test_unknown_dataset(self):
        resp = client.get("/api/nonexistent/0")
        assert resp.status_code == 404


# ── Reload ─────────────────────────────────────────────────────────────────


class TestReload:
    def test_reload_returns_ok(self):
        resp = client.post("/reload")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "commodities" in body["datasets_loaded"]


# ── Convert (stateless) ───────────────────────────────────────────────────


class TestConvert:
    def test_convert_csv(self):
        csv_content = b"id,name\n1,Alice\n2,Bob\n"
        resp = client.post(
            "/api/convert",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "test.csv"
        assert body["records"] == 2
        assert body["columns"] == ["id", "name"]
        assert len(body["data"]) == 2

    def test_convert_rejects_non_csv(self):
        resp = client.post(
            "/api/convert",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400

    def test_convert_empty_csv(self):
        resp = client.post(
            "/api/convert",
            files={"file": ("empty.csv", b"id,name\n", "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["records"] == 0
        assert body["data"] == []


# ── Upload ─────────────────────────────────────────────────────────────────


class TestUpload:
    def test_upload_creates_dataset(self, tmp_path, monkeypatch):
        import app.main as main_mod

        monkeypatch.setattr(main_mod, "DATA_DIR", tmp_path)

        csv_content = b"x,y\n1,a\n2,b\n3,c\n"
        resp = client.post(
            "/api/upload",
            files={"file": ("my_data.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["resource"] == "my_data"
        assert body["records"] == 3
        assert body["endpoint"] == "/api/my_data"

        # Dataset is now queryable
        resp2 = client.get("/api/my_data")
        assert resp2.status_code == 200
        assert resp2.json()["total"] == 3

        # Clean up
        del datasets["my_data"]

    def test_upload_sanitises_filename(self, tmp_path, monkeypatch):
        import app.main as main_mod

        monkeypatch.setattr(main_mod, "DATA_DIR", tmp_path)

        csv_content = b"col\nval\n"
        resp = client.post(
            "/api/upload",
            files={"file": ("My File (2).csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 200
        resource = resp.json()["resource"]
        # Should be lowercase, underscores, no special chars
        assert resource.isidentifier() or all(c.isalnum() or c == "_" for c in resource)

        del datasets[resource]

    def test_upload_rejects_non_csv(self):
        resp = client.post(
            "/api/upload",
            files={"file": ("data.json", b'{"a":1}', "application/json")},
        )
        assert resp.status_code == 400

    def test_upload_rejects_empty_csv(self, tmp_path, monkeypatch):
        import app.main as main_mod

        monkeypatch.setattr(main_mod, "DATA_DIR", tmp_path)

        resp = client.post(
            "/api/upload",
            files={"file": ("empty.csv", b"id,name\n", "text/csv")},
        )
        assert resp.status_code == 400

    def test_upload_saves_file_to_disk(self, tmp_path, monkeypatch):
        import app.main as main_mod

        monkeypatch.setattr(main_mod, "DATA_DIR", tmp_path)

        csv_content = b"a\n1\n"
        client.post(
            "/api/upload",
            files={"file": ("disk_test.csv", csv_content, "text/csv")},
        )
        assert (tmp_path / "disk_test.csv").exists()

        del datasets["disk_test"]
