"""Base connector class for all data sources."""

from abc import ABC, abstractmethod
from typing import Any

import httpx


class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self.base_url)
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
    async def fetch_series(self, series_id: str) -> dict[str, Any]:
        """Fetch a time series by ID."""
        pass

    @abstractmethod
    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search for series matching a query."""
        pass
