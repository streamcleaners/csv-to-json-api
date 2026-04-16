"""Shared fixtures for the test suite."""

import pytest


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with a small test CSV."""
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("id,name,price,available\n1,Widget,9.99,TRUE\n2,Gadget,19.50,FALSE\n3,Doohickey,5,TRUE\n")
    return tmp_path
