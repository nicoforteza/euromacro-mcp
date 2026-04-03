"""Series tools for MCP server."""

import logging
from datetime import datetime, timezone

from ..cache.sqlite import CacheManager
from ..catalog.loader import get_catalog
from ..providers.base import get_registry

logger = logging.getLogger(__name__)

_cache: CacheManager | None = None


def get_cache() -> CacheManager:
    """Get singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


# TTL by ECB frequency code (seconds)
CACHE_TTL = {
    "B": 86400,
    "D": 86400,
    "M": 604800,
    "Q": 2592000,
    "A": 7776000,
}


def _parse_series_id(series_id: str) -> tuple[str, str, str] | None:
    """Parse 'provider:dataset:series_key' into its three components.

    Returns (provider_id, dataset, series_key) or None if the format is invalid.
    """
    parts = series_id.split(":", 2)
    if len(parts) == 3 and all(parts):
        return parts[0], parts[1], parts[2]
    return None


async def search_series(
    query: str,
    limit: int = 10,
    provider: str | None = None,
    frequency: str | None = None,
    geo_coverage: str | None = None,
) -> list[dict]:
    """Search for datasets in the enriched catalog by keyword.

    Searches across dataset names, descriptions, concepts, and use-case questions.
    Results are ranked by relevance score.

    Args:
        query: Search query (e.g., "inflation", "exchange rate", "GDP")
        limit: Maximum number of results (default: 10)
        provider: Optional provider filter (e.g., "ecb")
        frequency: Optional primary frequency filter (e.g., "M", "Q", "D")
        geo_coverage: Optional geographic coverage filter

    Returns:
        List of matching datasets with id, name, description, and dimensions
    """
    catalog = get_catalog()
    results = catalog.search_datasets(query, provider_id=provider, limit=limit * 2)

    output = []
    for ds in results:
        if frequency and ds.primary_frequency.upper() != frequency.upper():
            continue
        if geo_coverage and geo_coverage.lower() not in ds.geographic_coverage.lower():
            continue
        output.append(ds.to_search_result())

    return output[:limit]


async def get_series(
    series_id: str,
    start_period: str | None = None,
    end_period: str | None = None,
) -> dict:
    """Fetch time series data.

    The series_id must follow the format: 'provider:dataset:series_key'

    Examples:
    - 'ecb:ICP:M.U2.N.000000.4.INX'   → Euro Area HICP headline inflation
    - 'ecb:FM:B.U2.EUR.4F.KR.DFR.LEV' → ECB Deposit Facility Rate
    - 'ecb:EXR:M.USD.EUR.SP00.A'       → EUR/USD monthly exchange rate

    Use search_series() or explore_datasets() to discover datasets, then
    build_series() to construct a valid series key.

    Args:
        series_id: 'provider:dataset:series_key' (e.g. 'ecb:ICP:M.U2.N.000000.4.INX')
        start_period: Start date in ISO format (e.g., "2020-01" or "2020-Q1")
        end_period: End date in ISO format (e.g., "2024-12" or "2024-Q4")

    Returns:
        Dict with observations [{date, value}] and metadata
    """
    parsed = _parse_series_id(series_id)
    if parsed is None:
        return {
            "id": series_id,
            "observations": [],
            "cached": False,
            "cache_timestamp": None,
            "error": (
                f"Invalid series_id format: '{series_id}'. "
                "Expected 'provider:dataset:series_key' "
                "(e.g. 'ecb:ICP:M.U2.N.000000.4.INX'). "
                "Use search_series() to find datasets and "
                "build_series() to construct valid series keys."
            ),
        }

    provider_id, dataset, series_key = parsed

    cache = get_cache()
    cache_key = f"{provider_id}:{dataset}:{series_key}:{start_period}:{end_period}"

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Cache hit for {series_id}")
        return cached_data

    # Get provider from registry
    registry = get_registry()
    provider = registry.get(provider_id)

    if provider is None:
        return {
            "id": series_id,
            "observations": [],
            "cached": False,
            "cache_timestamp": None,
            "error": f"Provider '{provider_id}' not found. Use list_providers() to see available providers.",
        }

    # Check if provider has a connector
    connector_class = provider.get_connector_class()
    if connector_class is None:
        return {
            "id": series_id,
            "observations": [],
            "cached": False,
            "cache_timestamp": None,
            "error": f"Connector for provider '{provider_id}' not implemented yet.",
        }

    try:
        async with provider.create_connector() as connector:
            df = await connector.fetch_series(
                dataset=dataset,
                series_key=series_key,
                start_period=start_period,
                end_period=end_period,
            )

        observations = [
            {"date": row["date"], "value": row["value"]}
            for _, row in df.iterrows()
        ]

        # Try to get a friendly dataset name from the enriched catalog
        catalog = get_catalog()
        ds_entry = catalog.get_dataset(provider_id, dataset)
        name = ds_entry.name if ds_entry else f"{dataset}"

        freq_code = series_key.split(".")[0] if "." in series_key else ""

        result: dict = {
            "id": series_id,
            "name": name,
            "dataset": dataset,
            "series_key": series_key,
            "frequency": freq_code,
            "observations": observations,
            "cached": False,
            "cache_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        ttl = CACHE_TTL.get(freq_code, 604800)
        cache.set(cache_key, {**result, "cached": True}, expire=ttl)

        return result

    except Exception as e:
        logger.error(f"Fetch error for {series_id}: {e}")
        return {
            "id": series_id,
            "dataset": dataset,
            "series_key": series_key,
            "observations": [],
            "cached": False,
            "cache_timestamp": None,
            "error": str(e),
        }


async def describe_series(series_id: str) -> dict:
    """Get metadata for a dataset or series.

    Accepts either:
    - 'provider:dataset' (e.g. 'ecb:ICP') → enriched dataset metadata
    - 'provider:dataset:series_key' (e.g. 'ecb:ICP:M.U2.N.000000.4.INX') → dataset metadata + series key info

    Args:
        series_id: 'provider:dataset' or 'provider:dataset:series_key'

    Returns:
        Enriched dataset metadata with hints for next steps
    """
    parts = series_id.split(":", 2)

    if len(parts) < 2:
        return {
            "error": (
                f"Invalid ID '{series_id}'. "
                "Use 'provider:dataset' (e.g. 'ecb:ICP') or "
                "'provider:dataset:series_key' (e.g. 'ecb:ICP:M.U2.N.000000.4.INX')."
            )
        }

    provider_id = parts[0]
    dataset_id = parts[1]
    series_key = parts[2] if len(parts) == 3 else None

    catalog = get_catalog()
    ds_entry = catalog.get_dataset(provider_id, dataset_id)

    if ds_entry is None:
        return {
            "error": f"Dataset '{provider_id}:{dataset_id}' not found in catalog",
            "hint": "Use explore_datasets() or search_series() to find available datasets.",
        }

    result: dict = {
        "provider": provider_id,
        "dataset": dataset_id,
        "name": ds_entry.name,
        "description": ds_entry.description_short,
        "concepts": ds_entry.concepts,
        "use_cases": ds_entry.use_cases,
        "primary_frequency": ds_entry.primary_frequency,
        "geographic_coverage": ds_entry.geographic_coverage,
        "key_dimensions": ds_entry.key_dimensions,
    }

    if series_key:
        result["series_key"] = series_key
        result["hint"] = (
            f"To fetch data: get_series('{series_id}', start_period='2020-01')"
        )
    else:
        result["hint"] = (
            f"To explore dimensions: explore_dimensions(provider_id='{provider_id}', dataset='{dataset_id}'). "
            f"To fetch a series: get_series('{provider_id}:{dataset_id}:<series_key>')"
        )

    return result


async def list_categories(include_series: bool = False) -> list[dict]:
    """List available dataset groups by geographic coverage.

    Groups all enriched datasets by their geographic coverage area.

    Args:
        include_series: If True, include list of dataset IDs per group

    Returns:
        List of coverage groups with dataset counts
    """
    catalog = get_catalog()
    datasets = catalog.list_all_datasets()

    coverage_groups: dict[str, list[str]] = {}
    for ds in datasets:
        cov = ds.geographic_coverage or "other"
        if cov not in coverage_groups:
            coverage_groups[cov] = []
        coverage_groups[cov].append(f"{ds.provider_id}:{ds.id}")

    result = []
    for coverage, dataset_ids in sorted(coverage_groups.items()):
        entry: dict = {
            "category": coverage,
            "series_count": len(dataset_ids),
            "series_ids": [],
        }
        if include_series:
            entry["series_ids"] = sorted(dataset_ids)
        result.append(entry)

    return result
