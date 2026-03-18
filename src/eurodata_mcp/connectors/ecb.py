"""ECB SDMX API connector."""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx
import pandas as pd

from .base import BaseConnector

logger = logging.getLogger(__name__)

# SDMX XML namespaces
SDMX_NS = {
    "mes": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}


class ECBConnectorError(Exception):
    """Error from ECB API."""

    pass


class ECBConnector(BaseConnector):
    """Connector for ECB Statistical Data Warehouse via SDMX API.

    API Documentation: https://data.ecb.europa.eu/help/api/data

    The ECB SDMX API provides:
    - Data: /data/{dataflow}/{key}
    - Dataflows: /dataflow/ECB
    - Data structures: /datastructure/ECB/{structure_id}
    - Codelists: /codelist/ECB/{codelist_id}
    """

    ECB_SDMX_BASE = "https://data-api.ecb.europa.eu/service"

    def __init__(self):
        super().__init__(self.ECB_SDMX_BASE)

    # -------------------------------------------------------------------------
    # Data fetching
    # -------------------------------------------------------------------------

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
        """Get metadata for a series from ECB."""
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

    # -------------------------------------------------------------------------
    # Metadata / Structure fetching
    # -------------------------------------------------------------------------

    async def fetch_dataflows(self) -> list[dict[str, Any]]:
        """Fetch all available ECB dataflows (datasets).

        Returns:
            List of dataflows with id, name, and description
        """
        url = "/dataflow/ECB"

        try:
            # Use XML format - the only format supported for structure endpoints
            response = await self.client.get(
                url,
                headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
            )
            response.raise_for_status()

            return self._parse_dataflows_xml(response.text)

        except httpx.TimeoutException:
            raise ECBConnectorError("ECB API request timed out")
        except httpx.RequestError as e:
            raise ECBConnectorError(f"Network error: {e}")

    def _parse_dataflows_xml(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse dataflows XML response."""
        dataflows = []

        try:
            root = ET.fromstring(xml_text)

            # Find all Dataflow elements
            for df_elem in root.findall(".//str:Dataflow", SDMX_NS):
                df_id = df_elem.get("id", "")
                version = df_elem.get("version", "")
                agency = df_elem.get("agencyID", "ECB")

                # Get name
                name_elem = df_elem.find("com:Name", SDMX_NS)
                name = name_elem.text if name_elem is not None else df_id

                # Get structure reference
                struct_ref = df_elem.find(".//str:Structure/Ref", SDMX_NS)
                if struct_ref is None:
                    struct_ref = df_elem.find(".//str:Structure", SDMX_NS)

                structure_id = ""
                if struct_ref is not None:
                    structure_id = struct_ref.get("id", "")

                dataflows.append({
                    "id": df_id,
                    "name": name,
                    "version": version,
                    "agency": agency,
                    "structure_id": structure_id,
                })

        except ET.ParseError as e:
            logger.error(f"Failed to parse dataflows XML: {e}")

        return dataflows

    async def fetch_datastructure(self, structure_id: str) -> dict[str, Any]:
        """Fetch the structure definition for a dataset.

        Args:
            structure_id: Structure ID (e.g., "ECB_ICP1")

        Returns:
            Dict with dimensions and their codelist references
        """
        url = f"/datastructure/ECB/{structure_id}"
        params = {"references": "children"}

        try:
            response = await self.client.get(
                url,
                params=params,
                headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
            )
            response.raise_for_status()

            return self._parse_datastructure_xml(response.text, structure_id)

        except httpx.TimeoutException:
            raise ECBConnectorError("ECB API request timed out")
        except httpx.RequestError as e:
            raise ECBConnectorError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch datastructure {structure_id}: {e}")
            raise ECBConnectorError(f"Failed to fetch structure: {e}")

    def _parse_datastructure_xml(self, xml_text: str, structure_id: str) -> dict[str, Any]:
        """Parse datastructure XML response."""
        dimensions = []
        codelist_refs = {}
        codelists = {}

        try:
            root = ET.fromstring(xml_text)

            # Find DataStructure element
            ds_elem = root.find(".//str:DataStructure", SDMX_NS)
            if ds_elem is None:
                return {"id": structure_id, "dimensions": [], "codelist_refs": {}, "codelists": {}}

            # Find DimensionList
            dim_list = ds_elem.find(".//str:DataStructureComponents/str:DimensionList", SDMX_NS)
            if dim_list is not None:
                for dim_elem in dim_list.findall("str:Dimension", SDMX_NS):
                    dim_id = dim_elem.get("id", "")
                    position = int(dim_elem.get("position", 0))

                    # Get codelist reference from LocalRepresentation/Enumeration
                    codelist_id = ""
                    enum_elem = dim_elem.find(".//str:LocalRepresentation/str:Enumeration/Ref", SDMX_NS)
                    if enum_elem is not None:
                        codelist_id = enum_elem.get("id", "")

                    dimensions.append({
                        "id": dim_id,
                        "position": position,
                        "codelist": codelist_id,
                    })
                    if codelist_id:
                        codelist_refs[dim_id] = codelist_id

            # Sort by position
            dimensions.sort(key=lambda x: x["position"])

            # Parse inline codelists if present
            for cl_elem in root.findall(".//str:Codelist", SDMX_NS):
                cl_id = cl_elem.get("id", "")
                codes = {}
                for code_elem in cl_elem.findall("str:Code", SDMX_NS):
                    code_id = code_elem.get("id", "")
                    name_elem = code_elem.find("com:Name", SDMX_NS)
                    code_name = name_elem.text if name_elem is not None else code_id
                    if code_id:
                        codes[code_id] = code_name
                if cl_id and codes:
                    codelists[cl_id] = codes

        except ET.ParseError as e:
            logger.error(f"Failed to parse datastructure XML: {e}")

        return {
            "id": structure_id,
            "dimensions": dimensions,
            "codelist_refs": codelist_refs,
            "codelists": codelists,
        }

    async def fetch_codelist(self, codelist_id: str) -> dict[str, str]:
        """Fetch a codelist (valid values for a dimension).

        Args:
            codelist_id: Codelist ID (e.g., "CL_AREA", "CL_FREQ")

        Returns:
            Dict mapping code -> description
        """
        url = f"/codelist/ECB/{codelist_id}"

        try:
            response = await self.client.get(
                url,
                headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
            )
            response.raise_for_status()

            return self._parse_codelist_xml(response.text)

        except httpx.TimeoutException:
            raise ECBConnectorError("ECB API request timed out")
        except httpx.RequestError as e:
            raise ECBConnectorError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch codelist {codelist_id}: {e}")
            return {}

    def _parse_codelist_xml(self, xml_text: str) -> dict[str, str]:
        """Parse codelist XML response."""
        codes = {}

        try:
            root = ET.fromstring(xml_text)

            # Find Codelist element
            cl_elem = root.find(".//str:Codelist", SDMX_NS)
            if cl_elem is None:
                return codes

            for code_elem in cl_elem.findall("str:Code", SDMX_NS):
                code_id = code_elem.get("id", "")
                name_elem = code_elem.find("com:Name", SDMX_NS)
                code_name = name_elem.text if name_elem is not None else code_id
                if code_id:
                    codes[code_id] = code_name

        except ET.ParseError as e:
            logger.error(f"Failed to parse codelist XML: {e}")

        return codes

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
