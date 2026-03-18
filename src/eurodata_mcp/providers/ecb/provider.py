"""ECB Provider implementation."""

import logging
from typing import Any

from ...connectors.ecb import ECBConnector, ECBConnectorError
from ...metadata import get_metadata_cache
from ..base import BaseProvider

logger = logging.getLogger(__name__)


class ECBProvider(BaseProvider):
    """European Central Bank data provider.

    Provides access to ECB Statistical Data Warehouse via SDMX API.
    Covers Euro Area macroeconomic data including:
    - Inflation (HICP)
    - Interest rates (ECB policy rates, Euribor)
    - Money supply (M1, M2, M3)
    - Credit to households and corporations
    - GDP and national accounts
    - Exchange rates
    - Balance of payments
    """

    id = "ecb"
    name = "European Central Bank"
    description = "Euro Area macroeconomic statistics from the ECB Statistical Data Warehouse"
    base_url = "https://data.ecb.europa.eu"

    coverage = {
        "geography": ["euro_area", "eu", "germany", "france", "spain", "italy", "netherlands", "belgium", "austria", "portugal", "ireland", "greece", "finland"],
        "topics": ["inflation", "interest_rates", "monetary_policy", "money_supply", "credit", "gdp", "unemployment", "exchange_rates", "balance_of_payments"],
        "frequency": ["daily", "monthly", "quarterly", "annual"],
    }

    keywords = [
        "ecb", "euro", "euro area", "eurozone", "european central bank",
        "hicp", "inflation", "ecb rate", "deposit rate", "euribor",
        "m1", "m2", "m3", "money supply",
        "germany", "france", "spain", "italy",
    ]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for ECB series."""
        cache = get_metadata_cache()

        # Search dataflows
        dataflows = cache.search_dataflows(query, limit=limit)

        return [
            {
                "id": df.get("id", ""),
                "name": df.get("name", ""),
                "provider": self.id,
                "type": "dataset",
            }
            for df in dataflows
        ]

    async def fetch_series(
        self,
        series_id: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> dict:
        """Fetch ECB time series data.

        series_id can be:
        - A catalog ID (e.g., "ecb_hicp_ea_yoy")
        - A full series key (e.g., "ICP/M.U2.N.000000.4.INX")
        """
        try:
            async with ECBConnector() as connector:
                # Parse series_id
                if "/" in series_id:
                    # Full format: DATASET/SERIES_KEY
                    parts = series_id.split("/", 1)
                    dataset = parts[0]
                    series_key = parts[1]
                else:
                    # Try to resolve from catalog
                    from ...catalog import get_catalog
                    catalog = get_catalog()
                    entry = catalog.get(series_id)
                    if entry:
                        dataset = entry.dataset
                        series_key = entry.series_key
                    else:
                        return {"error": f"Series '{series_id}' not found"}

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
                    "provider": self.id,
                    "dataset": dataset,
                    "series_key": series_key,
                    "observations": observations,
                    "count": len(observations),
                }

        except ECBConnectorError as e:
            logger.error(f"ECB fetch error: {e}")
            return {"error": str(e)}

    async def get_series_metadata(self, series_id: str) -> dict:
        """Get metadata for an ECB series."""
        # First try catalog
        from ...catalog import get_catalog
        catalog = get_catalog()
        entry = catalog.get(series_id)

        if entry:
            return entry.to_full_metadata()

        # Otherwise return basic info
        return {
            "id": series_id,
            "provider": self.id,
        }

    async def explore_datasets(self, query: str | None = None, limit: int = 20) -> dict:
        """Explore available ECB datasets."""
        from ...tools.explore import explore_datasets
        return await explore_datasets(query=query, limit=limit)

    async def explore_dimensions(self, dataset: str) -> dict:
        """Explore dimensions of an ECB dataset."""
        from ...tools.explore import explore_dimensions
        return await explore_dimensions(dataset=dataset)

    async def explore_codes(self, codelist: str, query: str | None = None) -> dict:
        """Explore codelist values."""
        from ...tools.explore import explore_codes
        return await explore_codes(codelist=codelist, query=query)
