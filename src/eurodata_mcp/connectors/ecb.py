"""ECB SDMX API connector."""

import logging

import httpx
import pandas as pd

from .base import BaseConnector

logger = logging.getLogger(__name__)


class ECBConnectorError(Exception):
    """Error from ECB API."""

    pass


class ECBConnector(BaseConnector):
    """Connector for ECB Statistical Data Warehouse via SDMX API.

    API Documentation: https://data.ecb.europa.eu/help/api/data
    """

    ECB_SDMX_BASE = "https://data-api.ecb.europa.eu/service"

    def __init__(self):
        super().__init__(self.ECB_SDMX_BASE)

    async def fetch_series(
        self,
        dataset: str,
        series_key: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> pd.DataFrame:
        """Fetch a time series from ECB by dataset and series key.

        Args:
            dataset: ECB dataset (e.g., "ICP", "FM", "BSI", "MNA")
            series_key: Series key (e.g., "M.U2.N.000000.4.INX")
            start_period: Start period in ISO format (e.g., "2020-01")
            end_period: End period in ISO format (e.g., "2024-12")

        Returns:
            DataFrame with columns: date, value
        """
        url = f"/data/{dataset}/{series_key}"
        params = {"format": "jsondata"}

        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period

        try:
            response = await self.client.get(url, params=params)

            if response.status_code == 404:
                raise ECBConnectorError(f"Series not found: {dataset}/{series_key}")
            if response.status_code == 429:
                raise ECBConnectorError("Rate limited by ECB API. Try again later.")
            if response.status_code >= 500:
                raise ECBConnectorError(f"ECB API error: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            return self._parse_sdmx_json(data)

        except httpx.TimeoutException:
            raise ECBConnectorError("ECB API request timed out")
        except httpx.RequestError as e:
            raise ECBConnectorError(f"Network error: {e}")

    def _parse_sdmx_json(self, data: dict) -> pd.DataFrame:
        """Parse SDMX-JSON response into DataFrame.

        SDMX-JSON structure:
        {
            "dataSets": [{
                "series": {
                    "0:0:0:...": {
                        "observations": {
                            "0": [value],
                            "1": [value],
                            ...
                        }
                    }
                }
            }],
            "structure": {
                "dimensions": {
                    "observation": [{
                        "id": "TIME_PERIOD",
                        "values": [{"id": "2020-01"}, ...]
                    }]
                }
            }
        }
        """
        try:
            datasets = data.get("dataSets", [])
            if not datasets:
                return pd.DataFrame(columns=["date", "value"])

            structure = data.get("structure", {})
            dimensions = structure.get("dimensions", {})
            observation_dims = dimensions.get("observation", [])

            time_periods = []
            for dim in observation_dims:
                if dim.get("id") == "TIME_PERIOD":
                    time_periods = [v.get("id") for v in dim.get("values", [])]
                    break

            series_data = datasets[0].get("series", {})
            if not series_data:
                return pd.DataFrame(columns=["date", "value"])

            first_series = list(series_data.values())[0]
            observations = first_series.get("observations", {})

            rows = []
            for idx_str, obs_values in observations.items():
                idx = int(idx_str)
                if idx < len(time_periods) and obs_values:
                    date = time_periods[idx]
                    value = obs_values[0] if obs_values[0] is not None else None
                    if value is not None:
                        rows.append({"date": date, "value": float(value)})

            df = pd.DataFrame(rows)
            if not df.empty:
                df = df.sort_values("date").reset_index(drop=True)

            return df

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse SDMX-JSON: {e}")
            raise ECBConnectorError(f"Failed to parse ECB response: {e}")

    async def get_metadata(self, dataset: str, series_key: str) -> dict:
        """Get metadata for a series from ECB.

        Note: The ECB API includes metadata in the data response structure.
        For now, we return basic info. Full metadata requires parsing
        the structure.dimensions and structure.attributes.
        """
        url = f"/data/{dataset}/{series_key}"
        params = {"format": "jsondata", "lastNObservations": "1"}

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            structure = data.get("structure", {})
            dimensions = structure.get("dimensions", {})

            return {
                "dataset": dataset,
                "series_key": series_key,
                "source": "ecb",
                "dimensions": dimensions.get("series", []),
            }
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return {"dataset": dataset, "series_key": series_key, "source": "ecb"}

    async def test_connection(self) -> bool:
        """Test ECB API connectivity with a known series."""
        try:
            df = await self.fetch_series(
                dataset="FM",
                series_key="B.U2.EUR.4F.KR.DFR.LEV",
                start_period="2024-01",
            )
            return len(df) > 0
        except Exception as e:
            logger.error(f"ECB connection test failed: {e}")
            return False
