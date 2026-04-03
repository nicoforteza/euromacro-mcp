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
    assert all("name" in r for r in results)


@pytest.mark.asyncio
async def test_search_series_returns_datasets():
    """Test that search_series returns dataset-level results."""
    results = await search_series("exchange rate")
    assert len(results) > 0
    ids = [r["id"] for r in results]
    assert "EXR" in ids


@pytest.mark.asyncio
async def test_search_series_limit():
    """Test search_series respects limit."""
    results = await search_series("euro", limit=2)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_search_series_with_provider_filter():
    """Test search_series with provider filter."""
    results = await search_series("inflation", provider="ecb")
    assert isinstance(results, list)
    assert all(r.get("provider") == "ecb" for r in results)


@pytest.mark.asyncio
async def test_search_series_result_structure():
    """Test that search results have required fields."""
    results = await search_series("monetary")
    for r in results:
        assert "id" in r
        assert "name" in r
        assert "description" in r
        assert "provider" in r


@pytest.mark.asyncio
async def test_list_categories_basic():
    """Test list_categories returns groups."""
    categories = await list_categories()
    assert len(categories) > 0
    assert all("category" in c for c in categories)
    assert all("series_count" in c for c in categories)


@pytest.mark.asyncio
async def test_list_categories_with_series():
    """Test list_categories with include_series=True."""
    categories = await list_categories(include_series=True)
    assert len(categories) > 0
    for cat in categories:
        assert "series_ids" in cat
        assert isinstance(cat["series_ids"], list)


@pytest.mark.asyncio
async def test_describe_series_known_dataset():
    """Test describe_series for a known dataset."""
    metadata = await describe_series("ecb:ICP")
    assert "error" not in metadata
    assert metadata["dataset"] == "ICP"
    assert metadata["provider"] == "ecb"
    assert "description" in metadata
    assert "hint" in metadata


@pytest.mark.asyncio
async def test_describe_series_with_series_key():
    """Test describe_series with full series key."""
    metadata = await describe_series("ecb:EXR:M.USD.EUR.SP00.A")
    assert "error" not in metadata
    assert metadata["dataset"] == "EXR"
    assert metadata["series_key"] == "M.USD.EUR.SP00.A"
    assert "get_series" in metadata["hint"]


@pytest.mark.asyncio
async def test_describe_series_unknown():
    """Test describe_series for unknown dataset."""
    metadata = await describe_series("ecb:NONEXISTENT_DATASET")
    assert "error" in metadata


@pytest.mark.asyncio
async def test_describe_series_invalid_format():
    """Test describe_series with invalid format."""
    metadata = await describe_series("invalid")
    assert "error" in metadata


@pytest.mark.asyncio
async def test_get_series_invalid_format():
    """Test get_series with invalid format."""
    result = await get_series("nonexistent_series")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_series_invalid_format_old_style():
    """Test get_series rejects old curated ID format."""
    result = await get_series("ecb_hicp_ea_yoy")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_series_unknown_provider():
    """Test get_series for unknown/unimplemented provider."""
    result = await get_series("bis:TOTAL_CREDIT:Q.5J.P.A.M.LE.XDC.A.2J")
    assert "error" in result
    # Provider is not found (not yet registered)
    assert "not found" in result["error"] or "not implemented" in result["error"]
