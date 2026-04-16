"""Tests for the CSV loader module."""

from pathlib import Path
from app.csv_loader import load_csv, _coerce


class TestCoerce:
    def test_empty_string_returns_none(self):
        assert _coerce("") is None

    def test_boolean_true(self):
        assert _coerce("TRUE") is True
        assert _coerce("true") is True

    def test_boolean_false(self):
        assert _coerce("FALSE") is False
        assert _coerce("false") is False

    def test_integer(self):
        assert _coerce("42") == 42
        assert _coerce("-7") == -7
        assert _coerce("0") == 0

    def test_float(self):
        assert _coerce("3.14") == 3.14
        assert _coerce("1e5") == 1e5

    def test_plain_string_unchanged(self):
        assert _coerce("hello") == "hello"

    def test_non_string_passthrough(self):
        assert _coerce(99) == 99
        assert _coerce(None) is None


class TestLoadCsv:
    def test_loads_rows(self, tmp_data_dir):
        rows = load_csv(tmp_data_dir / "products.csv")
        assert len(rows) == 3
        assert rows[0]["name"] == "Widget"

    def test_coerces_types(self, tmp_data_dir):
        rows = load_csv(tmp_data_dir / "products.csv")
        assert rows[0]["id"] == 1
        assert rows[0]["price"] == 9.99
        assert rows[0]["available"] is True
        assert rows[1]["available"] is False
