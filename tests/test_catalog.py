"""Tests for catalog loading."""

from eurodata_mcp.catalog import load_catalog


def test_load_catalog():
    """Test that the ECB euro area catalog loads."""
    catalog = load_catalog("ecb_euro_area")
    assert isinstance(catalog, list)
    assert len(catalog) >= 1


def test_catalog_schema():
    """Test that catalog entries have required fields."""
    catalog = load_catalog("ecb_euro_area")
    required_fields = ["id", "name", "description", "source", "series_key", "frequency", "unit", "tags"]

    for series in catalog:
        for field in required_fields:
            assert field in series, f"Missing field: {field}"
