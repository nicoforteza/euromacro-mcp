"""OECD Provider implementation."""

import logging
from typing import Any

from ...connectors.oecd import OECDConnector, OECDConnectorError
from ..base import BaseProvider

logger = logging.getLogger(__name__)


class OECDProvider(BaseProvider):
    """OECD (Organisation for Economic Co-operation and Development) data provider.

    Provides access to OECD statistics via SDMX API.
    Covers 38 member countries with standardized, comparable indicators:
    - Economic Outlook projections
    - Composite Leading Indicators (CLI)
    - GDP and national accounts
    - Prices and inflation
    - Employment and labor market
    - Trade statistics
    - Government finance
    """

    id = "oecd"
    name = "Organisation for Economic Co-operation and Development"
    description = "Cross-country comparable economic data for OECD member countries"
    base_url = "https://data-explorer.oecd.org"

    @property
    def data_api_url(self) -> str:
        """OECD SDMX API base URL for data requests."""
        return "https://sdmx.oecd.org/public/rest"

    def get_connector_class(self) -> type:
        """Return the OECDConnector class."""
        return OECDConnector

    @property
    def catalog_dir(self) -> "Path":
        """Point to the canonical catalog/oecd/ directory at the repo root.

        Walks up from this file until pyproject.toml is found (repo root),
        then returns <root>/catalog/oecd/.
        """
        from pathlib import Path

        p = Path(__file__).resolve().parent
        while p != p.parent:
            if (p / "pyproject.toml").exists():
                return p / "catalog" / "oecd"
            p = p.parent
        # Fallback: relative to this file (4 levels up to repo root)
        return Path(__file__).resolve().parents[4] / "catalog" / "oecd"

    coverage = {
        "geography": [
            # OECD members
            "australia", "austria", "belgium", "canada", "chile", "colombia",
            "costa_rica", "czech_republic", "denmark", "estonia", "finland",
            "france", "germany", "greece", "hungary", "iceland", "ireland",
            "israel", "italy", "japan", "korea", "latvia", "lithuania",
            "luxembourg", "mexico", "netherlands", "new_zealand", "norway",
            "poland", "portugal", "slovakia", "slovenia", "spain", "sweden",
            "switzerland", "turkey", "uk", "usa",
            # Aggregates
            "oecd_total", "g7", "g20", "euro_area", "eu27",
        ],
        "topics": [
            "economic_outlook", "leading_indicators", "gdp", "inflation",
            "unemployment", "trade", "government_debt", "productivity",
            "house_prices", "interest_rates", "exchange_rates",
        ],
        "frequency": ["daily", "monthly", "quarterly", "annual"],
    }

    keywords = [
        "oecd", "economic outlook", "cli", "composite leading indicator",
        "gdp", "unemployment", "inflation", "cpi",
        "usa", "united states", "germany", "france", "japan", "uk",
        "g7", "g20", "developed countries", "productivity",
    ]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for OECD datasets.

        Uses the enriched catalog if available, otherwise searches dataflows.
        """
        # Try enriched catalog first
        datasets = self.get_enriched_catalog()
        if datasets:
            q = query.lower()
            matches = []
            for ds in datasets:
                score = 0
                if q in ds.get("name", "").lower():
                    score += 3
                if q in ds.get("id", "").lower():
                    score += 2
                if any(q in c.lower() for c in ds.get("concepts", [])):
                    score += 1
                if score > 0:
                    matches.append((score, ds))

            matches.sort(key=lambda x: -x[0])
            return [
                {
                    "id": ds["id"],
                    "name": ds.get("name", ""),
                    "provider": self.id,
                    "type": "dataset",
                }
                for _, ds in matches[:limit]
            ]

        # Fallback: search description text
        return []

    async def fetch_series(
        self,
        series_id: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> dict:
        """Fetch OECD time series data.

        series_id format: "agency,dataflow,version/series_key"
        e.g., "OECD.SDD.STES,DSD_STES@DF_CLI,4.1/USA.M.LI.IX._Z.AA...H"
        """
        try:
            async with OECDConnector() as connector:
                # Parse series_id
                if "/" in series_id:
                    parts = series_id.split("/", 1)
                    dataset = parts[0]
                    series_key = parts[1]
                else:
                    return {"error": f"Invalid series_id format: '{series_id}'"}

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

        except OECDConnectorError as e:
            logger.error(f"OECD fetch error: {e}")
            return {"error": str(e)}

    async def get_series_metadata(self, series_id: str) -> dict:
        """Get metadata for an OECD series."""
        # Try catalog first
        datasets = self.get_enriched_catalog()
        for ds in datasets:
            if ds.get("id") == series_id:
                return {
                    "id": series_id,
                    "name": ds.get("name", ""),
                    "provider": self.id,
                    "description": ds.get("description_short", ""),
                }

        # Return basic info
        return {
            "id": series_id,
            "provider": self.id,
        }
