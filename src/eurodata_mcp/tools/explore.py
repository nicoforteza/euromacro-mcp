"""Exploration tools for browsing datasets, dimensions, and codes."""
from __future__ import annotations

import logging
from typing import Any

from ..metadata.cache import MetadataCache

logger = logging.getLogger(__name__)


async def explore_datasets(
    provider_id: str = "ecb",
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List available datasets for a provider, optionally filtered by query."""
    from ..providers.base import get_registry
    registry = get_registry()
    provider = registry.get(provider_id)

    if provider is None:
        return {
            "error": f"Provider '{provider_id}' not found. Use list_providers() to see available providers.",
            "datasets": [],
        }

    # Primary: use shipped enriched catalog (no network)
    datasets = provider.get_enriched_catalog()
    if datasets:
        if query:
            q = query.lower()
            datasets = [
                d for d in datasets
                if q in d.get("name", "").lower()
                or q in d.get("id", "").lower()
                or any(q in c.lower() for c in d.get("concepts", []))
                or any(q in u.lower() for u in d.get("use_cases", []))
            ]
        datasets = datasets[:limit]
        return {
            "provider": provider_id,
            "count": len(datasets),
            "source": "catalog",
            "datasets": [
                {
                    "id": d["id"],
                    "name": d.get("name", ""),
                    "description": d.get("description_short", ""),
                    "frequency": d.get("primary_frequency", ""),
                    "coverage": d.get("geographic_coverage", ""),
                    "key_dimensions": d.get("key_dimensions", []),
                }
                for d in datasets
            ],
        }

    # Fallback: ECB live metadata cache
    if provider_id == "ecb":
        from ..connectors.ecb import ECBConnector
        connector = ECBConnector()
        cache = MetadataCache()
        dataflows = cache.get_dataflows()
        results = []
        for df in dataflows:
            df_id = df.get("id", "")
            df_name = df.get("name", df_id)
            if query and query.lower() not in df_id.lower() and query.lower() not in df_name.lower():
                continue
            results.append({"id": df_id, "name": df_name, "source": "live"})
        return {
            "provider": provider_id,
            "count": len(results[:limit]),
            "datasets": results[:limit],
        }

    return {"error": f"No catalog available for provider '{provider_id}'", "datasets": []}


async def explore_dimensions(
    provider_id: str = "ecb",
    dataset: str = "",
) -> dict[str, Any]:
    """Explore the dimensions of a dataset (required to build a valid series key)."""
    from ..providers.base import get_registry
    registry = get_registry()
    provider = registry.get(provider_id)

    if provider and dataset:
        structure = provider.get_dataset_structure(dataset)
        if structure:
            dims = structure.get("dimensions", [])
            return {
                "provider": provider_id,
                "dataset": dataset,
                "source": "catalog",
                "dimensions": [
                    {
                        "position": d["position"],
                        "id": d["id"],
                        "name": d.get("name", ""),
                        "codelist_id": d.get("codelist_id", ""),
                        "n_codes": len(d.get("codes", {})),
                    }
                    for d in dims
                ],
                "series_key_format": ".".join(
                    f"<{d['id']}>" for d in sorted(dims, key=lambda x: x["position"])
                ),
                "hint": (
                    f"Use explore_codes(provider_id='{provider_id}', dataset='{dataset}', "
                    f"dimension_id='FREQ') to see valid values for each dimension."
                ),
            }

    # Fallback: live ECB metadata cache
    if provider_id == "ecb" and dataset:
        cache = MetadataCache()
        structure = cache.get_structure(dataset)
        if structure:
            dims = structure.get("dimensions", [])
            return {
                "provider": provider_id,
                "dataset": dataset,
                "source": "live",
                "dimensions": dims,
                "series_key_format": ".".join(f"<{d.get('id', '')}>" for d in dims),
            }

    return {
        "error": f"Dataset '{dataset}' not found for provider '{provider_id}'",
        "dimensions": [],
    }


async def explore_codes(
    provider_id: str = "ecb",
    dataset: str = "",
    dimension_id: str = "",
    query: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Explore valid codes for a specific dimension of a dataset."""
    from ..providers.base import get_registry
    registry = get_registry()
    provider = registry.get(provider_id)

    if provider and dataset and dimension_id:
        structure = provider.get_dataset_structure(dataset)
        if structure:
            dims = structure.get("dimensions", [])
            dim = next((d for d in dims if d["id"] == dimension_id), None)
            if dim and "codes" in dim:
                codes_dict = dim["codes"]
                items = [{"code": k, "description": v} for k, v in codes_dict.items()]
                if query:
                    q = query.lower()
                    items = [c for c in items if q in c["code"].lower() or q in c["description"].lower()]
                return {
                    "provider": provider_id,
                    "dataset": dataset,
                    "dimension": dimension_id,
                    "dimension_name": dim.get("name", dimension_id),
                    "source": "catalog",
                    "total": len(items),
                    "codes": items[:limit],
                }

    # Fallback: live ECB metadata cache (codelists)
    if provider_id == "ecb" and dataset and dimension_id:
        cache = MetadataCache()
        structure = cache.get_structure(dataset)
        if structure:
            dims = structure.get("dimensions", [])
            dim = next((d for d in dims if d.get("id") == dimension_id), None)
            if dim:
                codelist_id = dim.get("codelist_id", "")
                if codelist_id:
                    codes = cache.get_codelist(codelist_id)
                    if codes:
                        items = [
                            {"code": c, "description": desc}
                            for c, desc in codes.items()
                        ]
                        if query:
                            q = query.lower()
                            items = [
                                c for c in items
                                if q in c["code"].lower() or q in c["description"].lower()
                            ]
                        return {
                            "provider": provider_id,
                            "dataset": dataset,
                            "dimension": dimension_id,
                            "source": "live",
                            "total": len(items),
                            "codes": items[:limit],
                        }

    return {
        "error": f"Dimension '{dimension_id}' not found in dataset '{dataset}'",
        "codes": [],
    }


async def build_series(
    provider_id: str = "ecb",
    dataset: str = "",
    dimensions: dict[str, str] | None = None,
    start_period: str | None = None,
    end_period: str | None = None,
) -> dict[str, Any]:
    """Build a valid series key and data URL for a dataset."""
    if dimensions is None:
        dimensions = {}

    from ..providers.base import get_registry
    registry = get_registry()
    provider = registry.get(provider_id)

    ordered_dims: list[str] = []
    dim_names: list[str] = []

    if provider and dataset:
        structure = provider.get_dataset_structure(dataset)
        if structure:
            dims = sorted(structure.get("dimensions", []), key=lambda x: x["position"])
            ordered_dims = [d["id"] for d in dims]
            dim_names = [d.get("name", d["id"]) for d in dims]

    if not ordered_dims:
        # Fallback: use provided dimensions keys as-is
        ordered_dims = list(dimensions.keys())
        dim_names = ordered_dims

    # Build the key: empty string means "all values" for that dimension
    key_parts = [dimensions.get(dim_id, "") for dim_id in ordered_dims]
    series_key = ".".join(key_parts)

    # Build the API URL
    base_url = "https://data-api.ecb.europa.eu/service"
    data_url = f"{base_url}/data/{dataset}/{series_key}?format=jsondata"
    if start_period:
        data_url += f"&startPeriod={start_period}"
    if end_period:
        data_url += f"&endPeriod={end_period}"

    missing = [dim for dim in ordered_dims if dim not in dimensions]

    return {
        "provider": provider_id,
        "dataset": dataset,
        "series_key": series_key,
        "dimensions_used": dict(zip(ordered_dims, key_parts)),
        "data_url": data_url,
        "missing_dimensions": missing,
        "note": (
            "Empty string in a dimension position means 'all values' (wildcard)."
            if missing
            else ""
        ),
    }
