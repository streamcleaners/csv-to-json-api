"""Tests for the Streamlit frontend helper functions."""

from unittest.mock import patch, MagicMock
import pytest


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


class TestFetchDatasets:
    @patch("app.streamlit_app.requests.get")
    def test_returns_datasets(self, mock_get):
        mock_get.return_value = _mock_response(
            {"datasets": {"commodities": {"records": 100, "columns": ["id"], "endpoint": "/api/commodities"}}}
        )
        # Import after patching to avoid Streamlit page config issues
        from app.streamlit_app import fetch_datasets

        fetch_datasets.clear()  # clear Streamlit cache
        result = fetch_datasets()
        assert "commodities" in result
        assert result["commodities"]["records"] == 100

    @patch("app.streamlit_app.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("refused")
        from app.streamlit_app import fetch_datasets

        fetch_datasets.clear()
        result = fetch_datasets()
        assert result == {}


class TestFetchCommodities:
    @patch("app.streamlit_app.requests.get")
    def test_returns_data(self, mock_get):
        mock_get.return_value = _mock_response(
            {
                "total": 2,
                "limit": 100,
                "offset": 0,
                "count": 2,
                "data": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            }
        )
        from app.streamlit_app import fetch_commodities

        fetch_commodities.clear()
        result = fetch_commodities(limit=100, offset=0, filters={})
        assert result["total"] == 2
        assert len(result["data"]) == 2

    @patch("app.streamlit_app.requests.get")
    def test_passes_filters(self, mock_get):
        mock_get.return_value = _mock_response(
            {"total": 1, "limit": 100, "offset": 0, "count": 1, "data": [{"id": 1, "declarable": True}]}
        )
        from app.streamlit_app import fetch_commodities

        fetch_commodities.clear()
        fetch_commodities(limit=50, offset=0, filters={"declarable": "TRUE"})
        _, kwargs = mock_get.call_args
        assert "TRUE" in str(kwargs.get("params", {}))

    @patch("app.streamlit_app.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("refused")
        from app.streamlit_app import fetch_commodities

        fetch_commodities.clear()
        result = fetch_commodities(limit=100, offset=0, filters={})
        assert result["total"] == 0
        assert result["data"] == []
