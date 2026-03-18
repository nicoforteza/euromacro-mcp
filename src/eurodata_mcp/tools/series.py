"""Series tools for MCP server."""

import logging
from datetime import datetime, timezone
from typing import TypedDict

from ..cache.sqlite import CacheManager
from ..catalog.loader import get_catalog
from ..connectors.ecb import ECBConnector, ECBConnectorError

logger = logging.getLogger(__name__)

_cache: CacheManager | None = None


def get_cache() -> CacheManager:
    """Get singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


CACHE_TTL = {
    "daily": 86400,
    "monthly": 604800,
    "quarterly": 2592000,
    "annual": 7776000,
}


class SeriesPoint(TypedDict):
    date: str
    value: float


class SeriesData(TypedDict):
    id: str
    name: str
    unit: str
    frequency: str
    observations: list[SeriesPoint]
    cached: bool
    cache_timestamp: str | None


class SeriesResult(TypedDict):
    id: str
    name_en: str
    name_es: str
    category: str
    frequency: str
    geography: str
    priority: int
    description_en: str


class CategoryInfo(TypedDict):
    category: str
    series_count: int
    series_ids: list[str]


async def search_series(query: str, limit: int = 10) -> list[SeriesResult]:
    """Search for series in the catalog by keyword.

    Searches across series names (EN/ES), descriptions, tags, and categories.
    Results are ranked by relevance with higher priority series ranked first.

    Args:
        query: Search query (e.g., "inflation", "GDP", "interest rate")
        limit: Maximum number of results (default: 10)

    Returns:
        List of matching series with basic metadata
    """
    catalog = get_catalog()
    results = catalog.search(query, limit=limit)
    return [entry.to_search_result() for entry in results]


async def get_series(
    series_id: str,
    start_period: str | None = None,
    end_period: str | None = None,
) -> SeriesData:
    """Fetch time series data by ID.

    Retrieves data from cache if available, otherwise fetches from source API.
    Date range can be specified with start_period and end_period.

    Args:
        series_id: Series ID from the catalog (e.g., "ecb_hicp_ea_yoy")
        start_period: Start date in ISO format (e.g., "2020-01")
        end_period: End date in ISO format (e.g., "2024-12")

    Returns:
        SeriesData with observations and metadata
    """
    catalog = get_catalog()
    entry = catalog.get(series_id)

    if entry is None:
        return {
            "id": series_id,
            "name": "Unknown series",
            "unit": "",
            "frequency": "",
            "observations": [],
            "cached": False,
            "cache_timestamp": None,
            "error": f"Series '{series_id}' not found in catalog",
        }

    cache = get_cache()
    cache_key = f"{entry.source}:{entry.dataset}:{entry.series_key}:{start_period}:{end_period}"

    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Cache hit for {series_id}")
        return cached_data

    if entry.source == "ecb":
        try:
            async with ECBConnector() as connector:
                df = await connector.fetch_series(
                    dataset=entry.dataset,
                    series_key=entry.series_key,
                    start_period=start_period,
                    end_period=end_period,
                )

            observations = [
                {"date": row["date"], "value": row["value"]}
                for _, row in df.iterrows()
            ]

            result: SeriesData = {
                "id": entry.id,
                "name": entry.name_en,
                "unit": entry.unit,
                "frequency": entry.frequency,
                "observations": observations,
                "cached": False,
                "cache_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            ttl = CACHE_TTL.get(entry.frequency, 604800)
            cache.set(cache_key, {**result, "cached": True}, expire=ttl)

            return result

        except ECBConnectorError as e:
            logger.error(f"ECB fetch error for {series_id}: {e}")
            return {
                "id": entry.id,
                "name": entry.name_en,
                "unit": entry.unit,
                "frequency": entry.frequency,
                "observations": [],
                "cached": False,
                "cache_timestamp": None,
                "error": str(e),
            }
    else:
        return {
            "id": entry.id,
            "name": entry.name_en,
            "unit": entry.unit,
            "frequency": entry.frequency,
            "observations": [],
            "cached": False,
            "cache_timestamp": None,
            "error": f"Connector for source '{entry.source}' not implemented",
        }


async def describe_series(series_id: str) -> dict:
    """Get full metadata and description for a series.

    Returns comprehensive information about a series including its description,
    tags, availability, and the latest observation if available.

    Args:
        series_id: Series ID from the catalog (e.g., "ecb_hicp_ea_yoy")

    Returns:
        Full series metadata including latest observation
    """
    catalog = get_catalog()
    entry = catalog.get(series_id)

    if entry is None:
        return {"error": f"Series '{series_id}' not found in catalog"}

    metadata = entry.to_full_metadata()

    try:
        series_data = await get_series(series_id)
        if series_data.get("observations"):
            latest = series_data["observations"][-1]
            metadata["latest_observation"] = latest
            metadata["data_available"] = True
        else:
            metadata["data_available"] = False
            if "error" in series_data:
                metadata["fetch_error"] = series_data["error"]
    except Exception as e:
        logger.error(f"Failed to fetch latest for {series_id}: {e}")
        metadata["data_available"] = False
        metadata["fetch_error"] = str(e)

    return metadata


async def list_categories(include_series: bool = False) -> list[CategoryInfo]:
    """List all available data categories with series counts.

    Returns a list of categories available in the catalog, with the number
    of series in each category.

    Args:
        include_series: If True, include list of series IDs per category

    Returns:
        List of categories with series counts
    """
    catalog = get_catalog()
    categories_map = catalog.list_categories()

    result: list[CategoryInfo] = []
    for category, count in sorted(categories_map.items()):
        info: CategoryInfo = {
            "category": category,
            "series_count": count,
            "series_ids": [],
        }
        if include_series:
            series = catalog.get_by_category(category)
            info["series_ids"] = [s.id for s in series]
        result.append(info)

    return result
