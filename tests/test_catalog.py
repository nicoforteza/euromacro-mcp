"""Tests for enriched dataset catalog loading and search."""

import pytest

from eurodata_mcp.catalog import CatalogLoader, DatasetEntry, get_catalog


def test_catalog_loads():
    """Test that the dataset catalog loads successfully."""
    catalog = CatalogLoader()
    assert len(catalog) > 0


def test_catalog_singleton():
    """Test that get_catalog returns a singleton."""
    c1 = get_catalog()
    c2 = get_catalog()
    assert c1 is c2


def test_dataset_entry_required_fields():
    """Test that dataset entries have required fields."""
    catalog = get_catalog()
    for entry in catalog.list_all_datasets():
        assert isinstance(entry, DatasetEntry)
        assert entry.id, f"Missing id in entry: {entry}"
        assert entry.provider_id, f"Missing provider_id in entry: {entry}"
        assert entry.name, f"Missing name in entry for {entry.id}"
        assert entry.description_short, f"Missing description_short for {entry.id}"


def test_search_inflation():
    """Test searching for inflation datasets."""
    catalog = get_catalog()
    results = catalog.search_datasets("inflation")
    assert len(results) > 0
    names = [r.name.lower() for r in results]
    assert any("consumer" in n or "price" in n or "inflation" in n or "hicp" in n for n in names)


def test_search_exchange_rate():
    """Test searching for exchange rate datasets."""
    catalog = get_catalog()
    results = catalog.search_datasets("exchange rate")
    assert len(results) > 0
    ids = [r.id for r in results]
    assert "EXR" in ids


def test_search_interest_rate():
    """Test searching for interest rate datasets."""
    catalog = get_catalog()
    results = catalog.search_datasets("interest rate")
    assert len(results) > 0


def test_search_limit():
    """Test that search respects limit."""
    catalog = get_catalog()
    results = catalog.search_datasets("euro", limit=3)
    assert len(results) <= 3


def test_get_dataset_by_id():
    """Test getting a dataset by provider and ID."""
    catalog = get_catalog()
    entry = catalog.get_dataset("ecb", "EXR")
    assert entry is not None
    assert entry.id == "EXR"
    assert entry.provider_id == "ecb"


def test_get_dataset_icp():
    """Test getting the ICP dataset."""
    catalog = get_catalog()
    entry = catalog.get_dataset("ecb", "ICP")
    assert entry is not None
    assert entry.id == "ICP"


def test_get_unknown_dataset():
    """Test getting an unknown dataset returns None."""
    catalog = get_catalog()
    entry = catalog.get_dataset("ecb", "NONEXISTENT")
    assert entry is None


def test_list_all_datasets():
    """Test listing all datasets."""
    catalog = get_catalog()
    all_datasets = catalog.list_all_datasets()
    assert len(all_datasets) > 0


def test_list_datasets_by_provider():
    """Test listing datasets filtered by provider."""
    catalog = get_catalog()
    ecb_datasets = catalog.list_all_datasets(provider_id="ecb")
    assert len(ecb_datasets) > 0
    assert all(d.provider_id == "ecb" for d in ecb_datasets)


def test_dataset_to_search_result():
    """Test DatasetEntry.to_search_result()."""
    catalog = get_catalog()
    entry = catalog.get_dataset("ecb", "EXR")
    result = entry.to_search_result()

    assert "id" in result
    assert result["id"] == "EXR"
    assert "name" in result
    assert "description" in result
    assert "provider" in result
    assert result["provider"] == "ecb"


def test_dataset_has_concepts():
    """Test that datasets have non-empty concepts lists."""
    catalog = get_catalog()
    entry = catalog.get_dataset("ecb", "EXR")
    assert isinstance(entry.concepts, list)
    assert len(entry.concepts) > 0


def test_dataset_has_use_cases():
    """Test that datasets have use_cases."""
    catalog = get_catalog()
    entry = catalog.get_dataset("ecb", "FM")
    assert isinstance(entry.use_cases, list)
    assert len(entry.use_cases) > 0


def test_search_returns_datasets_with_correct_structure():
    """Test that search results have the expected structure."""
    catalog = get_catalog()
    results = catalog.search_datasets("monetary", limit=5)
    for r in results:
        sr = r.to_search_result()
        assert "id" in sr
        assert "provider" in sr
        assert "name" in sr
        assert "description" in sr
