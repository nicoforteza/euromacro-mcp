"""Base connector class for all data sources."""

from abc import ABC, abstractmethod

import httpx
import pandas as pd


class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Connector not initialized. Use async context manager.")
        return self._client

    @abstractmethod
    async def fetch_series(
        self,
        dataset: str,
        series_key: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> pd.DataFrame:
        """Fetch a time series by dataset and series key.

        Args:
            dataset: Dataset identifier (e.g., "ICP", "FM", "BSI")
            series_key: Series key within the dataset
            start_period: Start period (e.g., "2020-01")
            end_period: End period (e.g., "2024-12")

        Returns:
            DataFrame with columns: date (str), value (float)
        """
        pass

    @abstractmethod
    async def get_metadata(self, dataset: str, series_key: str) -> dict:
        """Get metadata for a series from the source API.

        Args:
            dataset: Dataset identifier
            series_key: Series key within the dataset

        Returns:
            Dict with series metadata
        """
        pass

    async def test_connection(self) -> bool:
        """Verify API is reachable."""
        try:
            response = await self.client.get("/")
            return response.status_code < 500
        except Exception:
            return False
