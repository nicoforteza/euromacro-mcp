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
# CATALOG TOOLS
# =============================================================================


@mcp.tool()
async def search_series(
    query: str,
    limit: int = 10,
    provider: str | None = None,
    frequency: str | None = None,
    geo_coverage: str | None = None,
) -> list[dict]:
    """Search for macroeconomic datasets by keyword.

    Searches across dataset names, descriptions, concepts, and use-case questions
    in the enriched catalog. Results are ranked by relevance.

    Examples:
    - "inflation" → ICP/HICP datasets
    - "exchange rate" → EXR dataset
    - "GDP" → National accounts (MNA) dataset
    - "unemployment" → Labour Force Statistics (LFSI)

    Args:
        query: Search query (e.g., "inflation", "GDP", "exchange rate")
        limit: Maximum results to return (default: 10)
        provider: Optional provider filter (e.g., "ecb")
        frequency: Optional primary frequency filter (e.g., "M", "Q", "D")
        geo_coverage: Optional geographic coverage filter

    Returns:
        List of matching datasets with id, name, description, and key dimensions
    """
    return await _search_series(
        query, limit=limit, provider=provider, frequency=frequency, geo_coverage=geo_coverage
    )


@mcp.tool()
async def get_series(
    series_id: str,
    start_period: str | None = None,
    end_period: str | None = None,
) -> dict:
    """Fetch time series data.

    The series_id must follow the format: 'provider:dataset:series_key'

    Examples:
    - 'ecb:ICP:M.U2.N.000000.4.INX'    → Euro Area HICP headline inflation
    - 'ecb:FM:B.U2.EUR.4F.KR.DFR.LEV'  → ECB Deposit Facility Rate
    - 'ecb:EXR:M.USD.EUR.SP00.A'        → EUR/USD monthly exchange rate
    - 'ecb:BSI:M.U2.Y.V.M30.X.I.U2.2300.Z01.E' → Euro Area M3

    Use search_series() → explore_dimensions() → build_series() to construct
    the series key before fetching.

    Args:
        series_id: 'provider:dataset:series_key' (e.g. 'ecb:ICP:M.U2.N.000000.4.INX')
        start_period: Start date, e.g., "2020-01" or "2020-Q1"
        end_period: End date, e.g., "2024-12" or "2024-Q4"

    Returns:
        Series data with observations [{date, value}] and metadata
    """
    return await _get_series(series_id, start_period, end_period)


@mcp.tool()
async def describe_series(series_id: str) -> dict:
    """Get enriched metadata for a dataset or series.

    Accepts either:
    - 'provider:dataset' (e.g. 'ecb:ICP') → enriched dataset metadata
    - 'provider:dataset:series_key' (e.g. 'ecb:ICP:M.U2.N.000000.4.INX') → dataset metadata + series key info

    Returns:
    - Dataset description, concepts, and use cases
    - Key dimensions for building series keys
    - Hints for next steps (explore_dimensions, get_series)

    Args:
        series_id: 'provider:dataset' or 'provider:dataset:series_key'

    Returns:
        Enriched dataset metadata with hints for next steps
    """
    return await _describe_series(series_id)


@mcp.tool()
async def list_categories(include_series: bool = False) -> list[dict]:
    """List available dataset groups by geographic coverage.

    Groups all enriched datasets by their geographic coverage area
    (e.g., euro_area_only, euro_area_and_countries, global).

    Args:
        include_series: If True, include list of dataset IDs per group

    Returns:
        List of coverage groups with dataset counts
    """
    return await _list_categories(include_series=include_series)


# =============================================================================
# DYNAMIC EXPLORATION TOOLS
# =============================================================================


@mcp.tool()
async def explore_datasets(
    provider_id: str = "ecb",
    query: str | None = None,
    limit: int = 20,
) -> dict:
    """Explore all available datasets for a provider.

    Lists datasets from the shipped enriched catalog (no network required).
    Use this to discover what data is available before using build_series().

    Args:
        provider_id: Provider identifier (default: "ecb")
        query: Optional search filter (e.g., "inflation", "interest")
        limit: Maximum results (default: 20)

    Returns:
        List of datasets with id, name, description, frequency, and key dimensions

    Examples:
        - explore_datasets() → list all ECB datasets
        - explore_datasets(query="inflation") → find ICP dataset
        - explore_datasets(query="exchange") → find EXR dataset
    """
    return await _explore_datasets(provider_id=provider_id, query=query, limit=limit)


@mcp.tool()
async def explore_dimensions(
    provider_id: str = "ecb",
    dataset: str = "",
) -> dict:
    """Explore the dimensions of a dataset.

    Shows all dimensions that make up series keys for a dataset.
    Each series key is built by combining dimension values.
    Uses the shipped catalog structures — no network required.

    For example, EXR (exchange rates) has:
    FREQ.CURRENCY.CURRENCY_DENOM.EXR_TYPE.EXR_SUFFIX

    Args:
        provider_id: Provider identifier (default: "ecb")
        dataset: Dataset ID (e.g., "ICP", "FM", "BSI", "EXR")

    Returns:
        List of dimensions with position, codelist reference, and code count

    Examples:
        - explore_dimensions(dataset="ICP") → inflation dimensions
        - explore_dimensions(dataset="EXR") → exchange rate dimensions
    """
    return await _explore_dimensions(provider_id=provider_id, dataset=dataset)


@mcp.tool()
async def explore_codes(
    provider_id: str = "ecb",
    dataset: str = "",
    dimension_id: str = "",
    query: str | None = None,
    limit: int = 50,
) -> dict:
    """Explore valid codes for a specific dimension of a dataset.

    Lists all valid values for a dimension. Use this to find the
    correct codes for building series keys with build_series().
    Uses the shipped catalog structures — no network required.

    Args:
        provider_id: Provider identifier (default: "ecb")
        dataset: Dataset ID (e.g., "EXR", "ICP", "FM")
        dimension_id: Dimension ID to explore (e.g., "FREQ", "CURRENCY")
        query: Optional search filter (e.g., "monthly", "USD")
        limit: Maximum results (default: 50)

    Returns:
        List of codes with their descriptions

    Examples:
        - explore_codes(dataset="EXR", dimension_id="FREQ") → frequency codes
        - explore_codes(dataset="EXR", dimension_id="CURRENCY", query="USD")
        - explore_codes(dataset="ICP", dimension_id="REF_AREA", query="germany")
    """
    return await _explore_codes(
        provider_id=provider_id,
        dataset=dataset,
        dimension_id=dimension_id,
        query=query,
        limit=limit,
    )


@mcp.tool()
async def build_series(
    provider_id: str = "ecb",
    dataset: str = "",
    dimensions: dict[str, str] | None = None,
    start_period: str | None = None,
    end_period: str | None = None,
) -> dict:
    """Build a valid series key and data URL for a dataset.

    Constructs a series key from dimension values and returns the API URL.
    Use explore_dimensions() and explore_codes() first to understand
    what dimensions and values are needed.

    Args:
        provider_id: Provider identifier (default: "ecb")
        dataset: Dataset ID (e.g., "ICP", "FM", "BSI", "EXR")
        dimensions: Dict mapping dimension ID to value (empty string = wildcard)
        start_period: Start date (e.g., "2020-01")
        end_period: End date (e.g., "2024-12")

    Returns:
        Series key, data URL, and missing dimensions (wildcards)

    Examples:
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

        # All monthly exchange rates (wildcard on CURRENCY)
        build_series(dataset="EXR", dimensions={"FREQ": "M"})
    """
    return await _build_series(
        provider_id=provider_id,
        dataset=dataset,
        dimensions=dimensions,
        start_period=start_period,
        end_period=end_period,
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
