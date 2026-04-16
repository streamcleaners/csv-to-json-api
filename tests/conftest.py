"""Shared fixtures for the test suite."""

import pytest
from pathlib import Path


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with a small test CSV."""
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("id,name,price,available\n1,Widget,9.99,TRUE\n2,Gadget,19.50,FALSE\n3,Doohickey,5,TRUE\n")
    return tmp_path


@pytest.fixture()
def test_client(tmp_data_dir, monkeypatch):
    """FastAPI TestClient wired to a temp data directory."""
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "DATA_DIR", tmp_data_dir)
    main_mod._discover_datasets()

    from fastapi.testclient import TestClient

    client = TestClient(main_mod.app)
    yield client

    # restore original datasets after test
    main_mod._discover_datasets()
