"""Tests for the CSV parser module (app.parser)."""

from app.parser import _coerce, parse_csv


class TestCoerce:
    def test_empty_string_returns_none(self):
        assert _coerce("") is None

    def test_boolean_true(self):
        assert _coerce("TRUE") is True
        assert _coerce("true") is True
        assert _coerce("True") is True

    def test_boolean_false(self):
        assert _coerce("FALSE") is False
        assert _coerce("false") is False

    def test_integer(self):
        assert _coerce("42") == 42
        assert _coerce("-7") == -7
        assert _coerce("0") == 0

    def test_leading_zeros_stay_as_string(self):
        assert _coerce("007") == "007"
        assert _coerce("0100000000") == "0100000000"

    def test_float(self):
        assert _coerce("3.14") == 3.14
        assert _coerce("1e5") == 1e5
        assert _coerce("-0.5") == -0.5

    def test_plain_string_unchanged(self):
        assert _coerce("hello") == "hello"
        assert _coerce("Live horses, asses") == "Live horses, asses"

    def test_non_string_passthrough(self):
        assert _coerce(99) == 99
        assert _coerce(None) is None


class TestParseCsv:
    def test_basic_parse(self):
        csv_text = "id,name,price\n1,Widget,9.99\n2,Gadget,19.50\n"
        rows = parse_csv(csv_text)
        assert len(rows) == 2
        assert rows[0]["name"] == "Widget"
        assert rows[0]["id"] == 1
        assert rows[0]["price"] == 9.99

    def test_boolean_coercion(self):
        csv_text = "flag\nTRUE\nFALSE\n"
        rows = parse_csv(csv_text)
        assert rows[0]["flag"] is True
        assert rows[1]["flag"] is False

    def test_empty_values_become_none(self):
        csv_text = "a,b\n1,\n,hello\n"
        rows = parse_csv(csv_text)
        assert rows[0]["b"] is None
        assert rows[1]["a"] is None
        assert rows[1]["b"] == "hello"

    def test_empty_csv_returns_empty_list(self):
        assert parse_csv("") == []
        assert parse_csv("id,name\n") == []

    def test_single_row(self):
        rows = parse_csv("x\n42\n")
        assert len(rows) == 1
        assert rows[0]["x"] == 42

    def test_preserves_commodity_codes_with_leading_zeros(self):
        csv_text = "code,desc\n0100000000,Live animals\n0201100000,Carcasses\n"
        rows = parse_csv(csv_text)
        assert rows[0]["code"] == "0100000000"
        assert rows[1]["code"] == "0201100000"

    def test_strips_bom(self):
        csv_text = "\ufeffid,name\n1,Test\n"
        rows = parse_csv(csv_text)
        assert "id" in rows[0]

    def test_none_keys_excluded(self):
        # csv.DictReader can produce None keys with extra columns
        csv_text = "a,b\n1,2,extra\n"
        rows = parse_csv(csv_text)
        assert None not in rows[0]
