"""Exploration tools for ECB metadata."""

import logging
from typing import Any

from ..connectors.ecb import ECBConnector, ECBConnectorError
from ..metadata import get_metadata_cache

logger = logging.getLogger(__name__)


async def explore_datasets(
    query: str | None = None,
    limit: int = 20,
    refresh: bool = False,
) -> dict[str, Any]:
    """Explore available ECB datasets (dataflows).

    Lists all available datasets from the ECB Statistical Data Warehouse.
    Use this to discover what data is available before fetching series.

    Args:
        query: Optional search query to filter datasets by name/ID
        limit: Maximum number of results (default: 20)
        refresh: If True, refresh from ECB API instead of cache

    Returns:
        Dict with list of datasets and metadata

    Examples:
        - explore_datasets() → list all datasets
        - explore_datasets("inflation") → find inflation-related datasets
        - explore_datasets("interest") → find interest rate datasets
    """
    cache = get_metadata_cache()

    if refresh or not cache.get_dataflows():
        try:
            async with ECBConnector() as connector:
                dataflows = await connector.fetch_dataflows()
                cache.save_dataflows(dataflows)
        except ECBConnectorError as e:
            logger.error(f"Failed to fetch dataflows: {e}")
            return {"error": str(e), "datasets": []}

    if query:
        datasets = cache.search_dataflows(query, limit=limit)
    else:
        datasets = cache.get_dataflows()[:limit]

    return {
        "count": len(datasets),
        "total_available": len(cache.get_dataflows()),
        "datasets": [
            {
                "id": df.get("id", ""),
                "name": df.get("name", ""),
                "structure_id": df.get("structure_id", ""),
            }
            for df in datasets
        ],
    }


async def explore_dimensions(
    dataset: str,
    refresh: bool = False,
) -> dict[str, Any]:
    """Explore the dimensions of a dataset.

    Shows all dimensions that make up series keys for a dataset,
    along with their valid codelists.

    Args:
        dataset: Dataset ID (e.g., "ICP", "FM", "BSI")
        refresh: If True, refresh from ECB API instead of cache

    Returns:
        Dict with dimensions and their codelist references

    Examples:
        - explore_dimensions("ICP") → dimensions for inflation data
        - explore_dimensions("FM") → dimensions for financial markets
    """
    cache = get_metadata_cache()

    dataflow = cache.get_dataflow(dataset)
    if not dataflow:
        dataflows = cache.search_dataflows(dataset, limit=1)
        if dataflows:
            dataflow = dataflows[0]

    if not dataflow:
        return {
            "error": f"Dataset '{dataset}' not found. Use explore_datasets() to list available datasets.",
            "dimensions": [],
        }

    structure_id = dataflow.get("structure_id", f"ECB_{dataset}1")
    structure = cache.get_structure(structure_id)

    if not structure or refresh:
        try:
            async with ECBConnector() as connector:
                structure = await connector.fetch_datastructure(structure_id)
                cache.save_structure(structure_id, structure)
        except ECBConnectorError as e:
            logger.error(f"Failed to fetch structure {structure_id}: {e}")
            return {"error": str(e), "dimensions": []}

    dimensions = structure.get("dimensions", [])
    codelist_refs = structure.get("codelist_refs", {})

    return {
        "dataset": dataset,
        "structure_id": structure_id,
        "dimensions": [
            {
                "position": dim.get("position", 0),
                "id": dim.get("id", ""),
                "codelist": dim.get("codelist", ""),
            }
            for dim in dimensions
        ],
        "series_key_format": ".".join(
            [f"<{dim.get('id', '?')}>" for dim in dimensions]
        ),
        "hint": "Use explore_codes(codelist) to see valid values for each dimension",
    }


async def explore_codes(
    codelist: str,
    query: str | None = None,
    limit: int = 50,
    refresh: bool = False,
) -> dict[str, Any]:
    """Explore valid codes for a dimension.

    Lists all valid values for a codelist (dimension values).

    Args:
        codelist: Codelist ID (e.g., "CL_AREA", "CL_FREQ")
        query: Optional search query to filter codes
        limit: Maximum number of results (default: 50)
        refresh: If True, refresh from ECB API instead of cache

    Returns:
        Dict with codes and their descriptions

    Common codelists:
        - CL_AREA: Countries and areas (U2=Euro Area, DE=Germany, ES=Spain...)
        - CL_FREQ: Frequencies (A=Annual, Q=Quarterly, M=Monthly, D=Daily)
        - CL_UNIT: Units of measurement
        - CL_ADJUSTMENT: Seasonal adjustment (N=Not adjusted, Y=Adjusted)

    Examples:
        - explore_codes("CL_AREA") → list all countries
        - explore_codes("CL_AREA", "spain") → find Spain's code
        - explore_codes("CL_FREQ") → list frequency codes
    """
    cache = get_metadata_cache()
    codes = cache.get_codelist(codelist)

    if not codes or refresh:
        try:
            async with ECBConnector() as connector:
                codes = await connector.fetch_codelist(codelist)
                if codes:
                    cache.save_codelist(codelist, codes)
        except ECBConnectorError as e:
            logger.error(f"Failed to fetch codelist {codelist}: {e}")
            return {"error": str(e), "codes": []}

    if not codes:
        return {
            "error": f"Codelist '{codelist}' not found or empty.",
            "codes": [],
        }

    if query:
        results = cache.search_codelist(codelist, query, limit=limit)
    else:
        results = [
            {"code": code, "description": desc}
            for code, desc in list(codes.items())[:limit]
        ]

    return {
        "codelist": codelist,
        "count": len(results),
        "total_available": len(codes),
        "codes": results,
    }


async def build_series(
    dataset: str,
    start_period: str | None = None,
    end_period: str | None = None,
    **dimensions: str,
) -> dict[str, Any]:
    """Build and fetch a series dynamically from dimension values.

    Constructs a series key from the provided dimension values and fetches the data.
    Use explore_dimensions() first to understand what dimensions are needed.

    Args:
        dataset: Dataset ID (e.g., "ICP", "FM", "BSI")
        start_period: Start date (e.g., "2020-01")
        end_period: End date (e.g., "2024-12")
        **dimensions: Dimension values as keyword arguments

    Returns:
        Dict with series data or error message

    Examples:
        # German monthly inflation (HICP all items)
        build_series(
            dataset="ICP",
            FREQ="M",
            REF_AREA="DE",
            ADJUSTMENT="N",
            ICP_ITEM="000000",
            STS_INSTITUTION="4",
            ICP_SUFFIX="INX",
            start_period="2020-01"
        )

        # ECB deposit rate
        build_series(
            dataset="FM",
            FREQ="B",
            REF_AREA="U2",
            CURRENCY="EUR",
            PROVIDER_FM="4F",
            INSTRUMENT_FM="KR",
            PROVIDER_FM_ID="DFR",
            DATA_TYPE_FM="LEV"
        )
    """
    cache = get_metadata_cache()

    dataflow = cache.get_dataflow(dataset)
    if not dataflow:
        dataflows = cache.search_dataflows(dataset, limit=1)
        if dataflows:
            dataflow = dataflows[0]

    if not dataflow:
        return {
            "error": f"Dataset '{dataset}' not found. Use explore_datasets() to list available datasets.",
        }

    structure_id = dataflow.get("structure_id", f"ECB_{dataset}1")
    structure = cache.get_structure(structure_id)

    if not structure:
        try:
            async with ECBConnector() as connector:
                structure = await connector.fetch_datastructure(structure_id)
                cache.save_structure(structure_id, structure)
        except ECBConnectorError as e:
            return {"error": f"Failed to fetch structure: {e}"}

    series_key = cache.build_series_key(structure_id, dimensions)
    if not series_key:
        dims = structure.get("dimensions", [])
        return {
            "error": "Failed to build series key",
            "required_dimensions": [d["id"] for d in dims],
            "provided_dimensions": list(dimensions.keys()),
        }

    try:
        async with ECBConnector() as connector:
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

        return {
            "dataset": dataset,
            "series_key": series_key,
            "dimensions": dimensions,
            "observation_count": len(observations),
            "observations": observations,
        }

    except ECBConnectorError as e:
        return {
            "error": str(e),
            "dataset": dataset,
            "series_key": series_key,
            "dimensions": dimensions,
            "hint": "Check dimension values with explore_codes()",
        }
