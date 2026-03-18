"""Tests for catalog loading and search."""

import pytest

from eurodata_mcp.catalog import CatalogLoader, SeriesEntry, get_catalog


def test_catalog_loads():
    """Test that the catalog loads successfully."""
    catalog = CatalogLoader()
    assert len(catalog) > 0


def test_catalog_singleton():
    """Test that get_catalog returns a singleton."""
    c1 = get_catalog()
    c2 = get_catalog()
    assert c1 is c2


def test_series_entry_required_fields():
    """Test that catalog entries have required fields."""
    catalog = get_catalog()
    required_fields = [
        "id", "source", "dataset", "series_key", "name_en",
        "description_en", "frequency", "unit",
    ]

    for entry in catalog.get_all():
        assert isinstance(entry, SeriesEntry)
        for field in required_fields:
            assert getattr(entry, field), f"Missing field: {field}"


def test_search_inflation():
    """Test searching for inflation series."""
    catalog = get_catalog()
    results = catalog.search("inflation")
    assert len(results) > 0
    assert any("hicp" in r.id.lower() for r in results)


def test_search_gdp():
    """Test searching for GDP series."""
    catalog = get_catalog()
    results = catalog.search("GDP")
    assert len(results) > 0
    assert any("gdp" in r.id.lower() for r in results)


def test_search_interest_rate():
    """Test searching for interest rate series."""
    catalog = get_catalog()
    results = catalog.search("interest rate")
    assert len(results) > 0


def test_search_limit():
    """Test that search respects limit."""
    catalog = get_catalog()
    results = catalog.search("euro", limit=3)
    assert len(results) <= 3


def test_get_series_by_id():
    """Test getting a series by ID."""
    catalog = get_catalog()
    entry = catalog.get("ecb_hicp_ea_yoy")
    assert entry is not None
    assert entry.id == "ecb_hicp_ea_yoy"
    assert entry.source == "ecb"


def test_get_unknown_series():
    """Test getting an unknown series returns None."""
    catalog = get_catalog()
    entry = catalog.get("nonexistent_series")
    assert entry is None


def test_list_categories():
    """Test listing categories."""
    catalog = get_catalog()
    categories = catalog.list_categories()
    assert len(categories) > 0
    assert "prices" in categories
    assert "interest_rates" in categories


def test_get_by_category():
    """Test getting series by category."""
    catalog = get_catalog()
    prices_series = catalog.get_by_category("prices")
    assert len(prices_series) > 0
    assert all(s.category == "prices" for s in prices_series)


def test_series_entry_to_search_result():
    """Test SeriesEntry.to_search_result()."""
    catalog = get_catalog()
    entry = catalog.get("ecb_hicp_ea_yoy")
    result = entry.to_search_result()

    assert "id" in result
    assert "name_en" in result
    assert "category" in result
    assert "priority" in result


def test_series_entry_to_full_metadata():
    """Test SeriesEntry.to_full_metadata()."""
    catalog = get_catalog()
    entry = catalog.get("ecb_hicp_ea_yoy")
    metadata = entry.to_full_metadata()

    assert "id" in metadata
    assert "source" in metadata
    assert "dataset" in metadata
    assert "series_key" in metadata
    assert "tags" in metadata
    assert "notes" in metadata
