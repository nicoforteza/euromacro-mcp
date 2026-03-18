"""ECB SDMX API connector."""

from typing import Any

from .base import BaseConnector


class ECBConnector(BaseConnector):
    """Connector for ECB Statistical Data Warehouse via SDMX API."""

    ECB_SDMX_BASE = "https://data-api.ecb.europa.eu/service"

    def __init__(self):
        super().__init__(self.ECB_SDMX_BASE)

    async def fetch_series(self, series_id: str) -> dict[str, Any]:
        """Fetch a time series from ECB by series key."""
        # TODO: Implement ECB SDMX fetch
        # Example: /data/EXR/M.USD.EUR.SP00.A
        return {}

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search ECB series (searches local catalog, not API)."""
        # TODO: Implement catalog search
        return []
