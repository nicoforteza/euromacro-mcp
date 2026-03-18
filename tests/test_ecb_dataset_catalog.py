"""Tests for ECB dataset-level enriched catalog — no network required."""
from __future__ import annotations

import pytest
from eurodata_mcp.catalog.loader import get_catalog, DatasetEntry
from eurodata_mcp.providers.ecb.provider import ECBProvider


# ── Provider-level tests ──────────────────────────────────────────────────────

def test_ecb_enriched_catalog_loads():
    provider = ECBProvider()
    datasets = provider.get_enriched_catalog()
    assert len(datasets) >= 90, f"Expected ≥90 datasets, got {len(datasets)}"


def test_ecb_enriched_catalog_schema():
    provider = ECBProvider()
    datasets = provider.get_enriched_catalog()
    required = ["id", "name", "description_short", "concepts", "use_cases",
                "primary_frequency", "geographic_coverage", "key_dimensions"]
    for d in datasets:
        for field in required:
            assert field in d, f"Dataset {d.get('id')} missing field: {field}"


def test_ecb_structure_exr_loads():
    provider = ECBProvider()
    exr = provider.get_dataset_structure("EXR")
    assert exr is not None
    assert exr["dataset_id"] == "EXR"
    assert len(exr["dimensions"]) >= 5


def test_ecb_structure_has_inline_codes():
    provider = ECBProvider()
    exr = provider.get_dataset_structure("EXR")
    freq_dim = next(d for d in exr["dimensions"] if d["id"] == "FREQ")
    assert "codes" in freq_dim
    assert "M" in freq_dim["codes"]
    assert "Q" in freq_dim["codes"]
    assert "A" in freq_dim["codes"]


def test_ecb_dataset_enriched_exr():
    provider = ECBProvider()
    exr = provider.get_dataset_enriched("EXR")
    assert exr is not None
    assert exr["id"] == "EXR"
    assert len(exr["concepts"]) >= 10
    assert len(exr["use_cases"]) >= 3


def test_ecb_missing_dataset_returns_none():
    provider = ECBProvider()
    result = provider.get_dataset_structure("DOES_NOT_EXIST")
    assert result is None


# ── CatalogLoader dataset search tests ───────────────────────────────────────

def test_catalog_search_datasets_exchange_rate():
    catalog = get_catalog()
    results = catalog.search_datasets("exchange rate", provider_id="ecb")
    assert len(results) > 0
    ids = [r.id for r in results]
    assert "EXR" in ids, f"EXR not found in results: {ids}"


def test_catalog_search_datasets_inflation():
    catalog = get_catalog()
    results = catalog.search_datasets("inflation")
    assert len(results) > 0
    ids = [r.id for r in results]
    assert any(x in ids for x in ["ICP", "HICP", "ICP"]), f"No inflation dataset in {ids}"


def test_catalog_search_datasets_gdp():
    catalog = get_catalog()
    results = catalog.search_datasets("GDP")
    assert len(results) > 0


def test_catalog_search_datasets_provider_filter():
    catalog = get_catalog()
    results = catalog.search_datasets("interest rate", provider_id="ecb")
    assert all(r.provider_id == "ecb" for r in results)


def test_catalog_search_datasets_returns_dataset_entry():
    catalog = get_catalog()
    results = catalog.search_datasets("exchange rate")
    assert all(isinstance(r, DatasetEntry) for r in results)


def test_catalog_get_dataset():
    catalog = get_catalog()
    exr = catalog.get_dataset("ecb", "EXR")
    assert exr is not None
    assert exr.id == "EXR"
    assert exr.provider_id == "ecb"


def test_catalog_get_dataset_missing():
    catalog = get_catalog()
    result = catalog.get_dataset("ecb", "DOES_NOT_EXIST")
    assert result is None


def test_dataset_entry_to_search_result():
    catalog = get_catalog()
    exr = catalog.get_dataset("ecb", "EXR")
    assert exr is not None
    result = exr.to_search_result()
    assert result["id"] == "EXR"
    assert result["provider"] == "ecb"
    assert result["type"] == "dataset"
    assert "description" in result


# ── Async tool tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_explore_datasets_ecb():
    from eurodata_mcp.tools.explore import explore_datasets
    result = await explore_datasets(provider_id="ecb", limit=200)
    assert "datasets" in result
    assert result["count"] >= 90
    assert result.get("source") == "catalog"


@pytest.mark.asyncio
async def test_explore_datasets_with_query():
    from eurodata_mcp.tools.explore import explore_datasets
    result = await explore_datasets(provider_id="ecb", query="exchange")
    assert "datasets" in result
    assert len(result["datasets"]) > 0
    ids = [d["id"] for d in result["datasets"]]
    assert "EXR" in ids


@pytest.mark.asyncio
async def test_explore_datasets_invalid_provider():
    from eurodata_mcp.tools.explore import explore_datasets
    result = await explore_datasets(provider_id="does_not_exist")
    assert "error" in result


@pytest.mark.asyncio
async def test_explore_dimensions_exr():
    from eurodata_mcp.tools.explore import explore_dimensions
    result = await explore_dimensions(provider_id="ecb", dataset="EXR")
    assert "dimensions" in result
    assert result.get("source") == "catalog"
    dim_ids = [d["id"] for d in result["dimensions"]]
    assert "FREQ" in dim_ids
    assert "CURRENCY" in dim_ids


@pytest.mark.asyncio
async def test_explore_dimensions_has_series_key_format():
    from eurodata_mcp.tools.explore import explore_dimensions
    result = await explore_dimensions(provider_id="ecb", dataset="EXR")
    assert "series_key_format" in result
    assert "FREQ" in result["series_key_format"]


@pytest.mark.asyncio
async def test_explore_codes_freq_dimension():
    from eurodata_mcp.tools.explore import explore_codes
    result = await explore_codes(provider_id="ecb", dataset="EXR", dimension_id="FREQ")
    assert "codes" in result
    assert result.get("source") == "catalog"
    codes = {c["code"] for c in result["codes"]}
    assert "M" in codes
    assert "Q" in codes
    assert "A" in codes
    assert "D" in codes


@pytest.mark.asyncio
async def test_explore_codes_with_query_filter():
    from eurodata_mcp.tools.explore import explore_codes
    result = await explore_codes(
        provider_id="ecb", dataset="EXR", dimension_id="FREQ", query="annual"
    )
    assert "codes" in result
    assert all("annual" in c["description"].lower() for c in result["codes"])


@pytest.mark.asyncio
async def test_build_series_exr():
    from eurodata_mcp.tools.explore import build_series
    result = await build_series(
        provider_id="ecb",
        dataset="EXR",
        dimensions={
            "FREQ": "M",
            "CURRENCY": "USD",
            "CURRENCY_DENOM": "EUR",
            "EXR_TYPE": "SP00",
            "EXR_SUFFIX": "A",
        },
    )
    assert result["series_key"] == "M.USD.EUR.SP00.A"
    assert "data_url" in result
    assert "EXR/M.USD.EUR.SP00.A" in result["data_url"]


@pytest.mark.asyncio
async def test_build_series_with_wildcards():
    from eurodata_mcp.tools.explore import build_series
    result = await build_series(
        provider_id="ecb",
        dataset="EXR",
        dimensions={"FREQ": "M", "CURRENCY": "USD"},
    )
    # Missing dimensions should be empty (wildcard)
    key_parts = result["series_key"].split(".")
    assert key_parts[0] == "M"
    assert key_parts[1] == "USD"
    assert len(result["missing_dimensions"]) > 0
