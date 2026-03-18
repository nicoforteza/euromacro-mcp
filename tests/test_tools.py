"""Tests for MCP tools."""

import pytest

from eurodata_mcp.tools import (
    describe_series,
    get_series,
    list_categories,
    search_series,
)


@pytest.mark.asyncio
async def test_search_series_inflation():
    """Test search_series tool with inflation query."""
    results = await search_series("inflation")
    assert len(results) > 0
    assert all("id" in r for r in results)
    assert all("name_en" in r for r in results)


@pytest.mark.asyncio
async def test_search_series_limit():
    """Test search_series respects limit."""
    results = await search_series("euro", limit=2)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_list_categories_basic():
    """Test list_categories returns categories."""
    categories = await list_categories()
    assert len(categories) > 0
    assert all("category" in c for c in categories)
    assert all("series_count" in c for c in categories)


@pytest.mark.asyncio
async def test_list_categories_with_series():
    """Test list_categories with include_series=True."""
    categories = await list_categories(include_series=True)
    assert len(categories) > 0
    prices_cat = next((c for c in categories if c["category"] == "prices"), None)
    assert prices_cat is not None
    assert len(prices_cat["series_ids"]) > 0


@pytest.mark.asyncio
async def test_describe_series_known():
    """Test describe_series for known series."""
    metadata = await describe_series("ecb_hicp_ea_yoy")
    assert "id" in metadata
    assert metadata["id"] == "ecb_hicp_ea_yoy"
    assert "description_en" in metadata
    assert "tags" in metadata


@pytest.mark.asyncio
async def test_describe_series_unknown():
    """Test describe_series for unknown series."""
    metadata = await describe_series("nonexistent_series")
    assert "error" in metadata


@pytest.mark.asyncio
async def test_get_series_unknown():
    """Test get_series for unknown series."""
    result = await get_series("nonexistent_series")
    assert "error" in result or result["observations"] == []
