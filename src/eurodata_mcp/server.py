"""FastMCP server entry point for eurodata-mcp."""

import logging

from fastmcp import FastMCP

from .tools.series import (
    describe_series as _describe_series,
    get_series as _get_series,
    list_categories as _list_categories,
    search_series as _search_series,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("eurodata")


@mcp.tool()
async def search_series(query: str, limit: int = 10) -> list[dict]:
    """Search for macroeconomic series by keyword.

    Searches across series names (EN/ES), descriptions, tags, and categories.
    Results are ranked by relevance with priority 1 series ranked first.

    Examples:
    - "inflation" → HICP headline, core, energy, food
    - "interest rate" → ECB rates, Euribor
    - "GDP" → Euro Area GDP growth (YoY, QoQ)
    - "unemployment" → Euro Area unemployment rate

    Args:
        query: Search query (e.g., "inflation", "GDP", "ECB rate")
        limit: Maximum results to return (default: 10)

    Returns:
        List of matching series with id, name, category, and description
    """
    return await _search_series(query, limit=limit)


@mcp.tool()
async def get_series(
    series_id: str,
    start_period: str | None = None,
    end_period: str | None = None,
) -> dict:
    """Fetch time series data by ID.

    Retrieves observations for a series from the catalog.
    Data is cached to minimize API calls.

    Common series IDs:
    - ecb_hicp_ea_yoy: Euro Area headline inflation
    - ecb_hicp_ea_core_yoy: Euro Area core inflation
    - ecb_rate_dfr: ECB Deposit Facility Rate
    - ecb_gdp_ea_yoy: Euro Area GDP growth (YoY)
    - ecb_unemployment_ea: Euro Area unemployment rate

    Args:
        series_id: Series ID from catalog (use search_series to find IDs)
        start_period: Start date, e.g., "2020-01" or "2020-Q1"
        end_period: End date, e.g., "2024-12" or "2024-Q4"

    Returns:
        Series data with observations [{date, value}] and metadata
    """
    return await _get_series(series_id, start_period, end_period)


@mcp.tool()
async def describe_series(series_id: str) -> dict:
    """Get full metadata and description for a series.

    Returns comprehensive information including:
    - Full description and notes
    - Unit of measurement
    - Data availability and update frequency
    - Related series
    - Latest observation (if available)

    Args:
        series_id: Series ID from catalog

    Returns:
        Full series metadata with latest observation
    """
    return await _describe_series(series_id)


@mcp.tool()
async def list_categories(include_series: bool = False) -> list[dict]:
    """List all available data categories.

    Categories include:
    - prices: Inflation (HICP)
    - interest_rates: ECB rates, Euribor
    - monetary: M1, M3, credit to households/NFCs
    - gdp_growth: GDP YoY and QoQ
    - labor_market: Unemployment

    Args:
        include_series: If True, include list of series IDs per category

    Returns:
        List of categories with series counts
    """
    return await _list_categories(include_series=include_series)


def main():
    """Run the MCP server."""
    logger.info("Starting eurodata MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
