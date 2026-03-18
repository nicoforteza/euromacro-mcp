"""FastMCP server entry point for eurodata-mcp."""

import logging

from fastmcp import FastMCP

from .providers.base import get_registry
from .tools.explore import (
    build_series as _build_series,
    explore_codes as _explore_codes,
    explore_datasets as _explore_datasets,
    explore_dimensions as _explore_dimensions,
)
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

# =============================================================================
# CURATED CATALOG TOOLS
# =============================================================================


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


# =============================================================================
# DYNAMIC EXPLORATION TOOLS
# =============================================================================


@mcp.tool()
async def explore_datasets(
    query: str | None = None,
    limit: int = 20,
) -> dict:
    """Explore all available ECB datasets.

    Lists ~50 ECB datasets covering inflation, interest rates, money supply,
    GDP, employment, exchange rates, and more. Use this to discover what
    data is available before using build_series().

    Args:
        query: Optional search filter (e.g., "inflation", "interest")
        limit: Maximum results (default: 20)

    Returns:
        List of datasets with id, name, and structure_id

    Examples:
        - explore_datasets() → list all
        - explore_datasets("inflation") → find ICP dataset
        - explore_datasets("exchange") → find EXR dataset
    """
    return await _explore_datasets(query=query, limit=limit)


@mcp.tool()
async def explore_dimensions(dataset: str) -> dict:
    """Explore the dimensions of an ECB dataset.

    Shows all dimensions that make up series keys for a dataset.
    Each series key is built by combining dimension values.

    For example, ICP (inflation) has:
    FREQ.REF_AREA.ADJUSTMENT.ICP_ITEM.STS_INSTITUTION.ICP_SUFFIX

    Args:
        dataset: Dataset ID (e.g., "ICP", "FM", "BSI", "EXR")

    Returns:
        List of dimensions with their position and codelist reference

    Examples:
        - explore_dimensions("ICP") → inflation dimensions
        - explore_dimensions("FM") → financial markets dimensions
    """
    return await _explore_dimensions(dataset=dataset)


@mcp.tool()
async def explore_codes(
    codelist: str,
    query: str | None = None,
    limit: int = 50,
) -> dict:
    """Explore valid codes for a dimension.

    Lists all valid values for a codelist. Use this to find the
    correct codes for building series keys.

    Common codelists:
    - CL_AREA: Countries (U2=Euro Area, DE=Germany, ES=Spain, FR=France...)
    - CL_FREQ: Frequencies (A=Annual, Q=Quarterly, M=Monthly, D=Daily)
    - CL_CURRENCY: Currencies (EUR, USD, GBP...)

    Args:
        codelist: Codelist ID (e.g., "CL_AREA", "CL_FREQ")
        query: Optional search filter (e.g., "spain", "germany")
        limit: Maximum results (default: 50)

    Returns:
        List of codes with their descriptions

    Examples:
        - explore_codes("CL_AREA") → list all countries
        - explore_codes("CL_AREA", "spain") → find ES code
        - explore_codes("CL_FREQ") → list frequencies
    """
    return await _explore_codes(codelist=codelist, query=query, limit=limit)


@mcp.tool()
async def build_series(
    dataset: str,
    dimensions: dict[str, str],
    start_period: str | None = None,
    end_period: str | None = None,
) -> dict:
    """Build and fetch any ECB series dynamically.

    Constructs a series key from dimension values and fetches the data.
    Use explore_dimensions() and explore_codes() first to understand
    what dimensions and values are needed.

    Args:
        dataset: Dataset ID (e.g., "ICP", "FM", "BSI")
        dimensions: Dict mapping dimension ID to value
        start_period: Start date (e.g., "2020-01")
        end_period: End date (e.g., "2024-12")

    Returns:
        Series data with observations and metadata

    Examples:
        # German inflation
        build_series(
            dataset="ICP",
            dimensions={
                "FREQ": "M",
                "REF_AREA": "DE",
                "ADJUSTMENT": "N",
                "ICP_ITEM": "000000",
                "STS_INSTITUTION": "4",
                "ICP_SUFFIX": "INX"
            },
            start_period="2020-01"
        )

        # USD/EUR exchange rate
        build_series(
            dataset="EXR",
            dimensions={
                "FREQ": "M",
                "CURRENCY": "USD",
                "CURRENCY_DENOM": "EUR",
                "EXR_TYPE": "SP00",
                "EXR_SUFFIX": "A"
            }
        )
    """
    return await _build_series(
        dataset=dataset,
        start_period=start_period,
        end_period=end_period,
        **dimensions,
    )


# =============================================================================
# PROVIDER TOOLS
# =============================================================================


@mcp.tool()
async def list_providers() -> list[dict]:
    """List all available data providers.

    Returns information about each provider including:
    - id: Provider identifier (ecb, bis, imf, fred)
    - name: Full provider name
    - description: What data it covers
    - coverage: Geography, topics, and frequencies
    - keywords: Terms that match this provider

    Currently available:
    - ecb: European Central Bank (Euro Area macro data)

    Coming soon:
    - bis: Bank for International Settlements (global banking, credit)
    - imf: International Monetary Fund (global economic data)
    - fred: Federal Reserve St. Louis (US economic data)

    Returns:
        List of provider information dicts
    """
    registry = get_registry()
    return registry.list_providers()


@mcp.tool()
async def get_provider_guide(provider: str) -> dict:
    """Get the usage guide for a data provider.

    Each provider has a guide explaining:
    - Key concepts (datasets, series keys, dimensions)
    - Common data requests with examples
    - Step-by-step usage instructions
    - Tips and best practices

    This is essential reading before using a provider's exploration tools.

    Args:
        provider: Provider ID (e.g., "ecb", "bis", "imf", "fred")

    Returns:
        Guide content with examples and aliases

    Example:
        get_provider_guide("ecb") → ECB data guide with HICP, rates, M3 examples
    """
    registry = get_registry()
    p = registry.get(provider)

    if not p:
        available = [info["id"] for info in registry.list_providers()]
        return {
            "error": f"Provider '{provider}' not found",
            "available_providers": available,
        }

    return {
        "provider": p.id,
        "name": p.name,
        "guide": p.get_guide(),
        "examples": p.get_examples(),
        "aliases": p.get_aliases(),
    }


@mcp.tool()
async def find_provider(query: str) -> dict:
    """Find the best provider for a data query.

    Analyzes your query and suggests which provider(s) can help.
    Useful when you're not sure which source has the data you need.

    Args:
        query: Natural language query (e.g., "euro area inflation",
               "us unemployment", "global credit growth")

    Returns:
        Ranked list of matching providers with relevance scores

    Examples:
        - "euro area inflation" → ECB (HICP data)
        - "germany gdp" → ECB (national accounts)
        - "us interest rates" → FRED (Fed funds rate)
        - "global banking statistics" → BIS
    """
    registry = get_registry()
    matches = registry.find_providers(query, min_score=0.1)

    if not matches:
        return {
            "query": query,
            "matches": [],
            "suggestion": "No providers matched. Try broader terms or list_providers() to see available sources.",
        }

    return {
        "query": query,
        "matches": [
            {
                "provider": p.id,
                "name": p.name,
                "score": round(score, 2),
                "coverage": p.coverage,
            }
            for p, score in matches
        ],
        "best_match": matches[0][0].id,
    }


def main():
    """Run the MCP server."""
    logger.info("Starting eurodata MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
