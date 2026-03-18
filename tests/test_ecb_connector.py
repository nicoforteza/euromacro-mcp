"""Tests for ECB connector."""

import pytest

from eurodata_mcp.connectors.ecb import ECBConnector


class TestSDMXParsing:
    """Test SDMX-JSON parsing."""

    def test_parse_valid_response(self):
        """Test parsing a valid SDMX-JSON response."""
        connector = ECBConnector()

        sample_response = {
            "dataSets": [{
                "series": {
                    "0:0:0": {
                        "observations": {
                            "0": [2.1],
                            "1": [2.3],
                            "2": [2.5],
                        }
                    }
                }
            }],
            "structure": {
                "dimensions": {
                    "observation": [{
                        "id": "TIME_PERIOD",
                        "values": [
                            {"id": "2024-01"},
                            {"id": "2024-02"},
                            {"id": "2024-03"},
                        ]
                    }]
                }
            }
        }

        df = connector._parse_sdmx_json(sample_response)

        assert len(df) == 3
        assert list(df.columns) == ["date", "value"]
        assert df.iloc[0]["date"] == "2024-01"
        assert df.iloc[0]["value"] == 2.1
        assert df.iloc[2]["date"] == "2024-03"
        assert df.iloc[2]["value"] == 2.5

    def test_parse_empty_response(self):
        """Test parsing an empty response."""
        connector = ECBConnector()

        empty_response = {"dataSets": []}
        df = connector._parse_sdmx_json(empty_response)

        assert len(df) == 0
        assert list(df.columns) == ["date", "value"]

    def test_parse_no_series(self):
        """Test parsing response with no series data."""
        connector = ECBConnector()

        response = {
            "dataSets": [{"series": {}}],
            "structure": {"dimensions": {"observation": []}}
        }
        df = connector._parse_sdmx_json(response)

        assert len(df) == 0

    def test_parse_with_null_values(self):
        """Test parsing response with null values."""
        connector = ECBConnector()

        response = {
            "dataSets": [{
                "series": {
                    "0:0:0": {
                        "observations": {
                            "0": [2.1],
                            "1": [None],  # null value
                            "2": [2.5],
                        }
                    }
                }
            }],
            "structure": {
                "dimensions": {
                    "observation": [{
                        "id": "TIME_PERIOD",
                        "values": [
                            {"id": "2024-01"},
                            {"id": "2024-02"},
                            {"id": "2024-03"},
                        ]
                    }]
                }
            }
        }

        df = connector._parse_sdmx_json(response)

        # Should skip the null value
        assert len(df) == 2
        assert "2024-02" not in df["date"].values
