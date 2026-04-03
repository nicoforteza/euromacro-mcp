"""OECD SDMX API connector."""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx
import pandas as pd

from .base import BaseConnector

logger = logging.getLogger(__name__)

# SDMX XML namespaces (same as ECB)
SDMX_NS = {
    "mes": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}


class OECDConnectorError(Exception):
    """Error from OECD API."""

    pass


class OECDConnector(BaseConnector):
    """Connector for OECD Statistical Data via SDMX API.

    API Documentation: https://sdmx.oecd.org/public/rest/

    The OECD SDMX API provides:
    - Data: /data/{agency},{dataflow},{version}/{filter}
    - Dataflows: /dataflow/{agency}
    - Data structures: /datastructure/{agency}/{structure_id}/{version}
    - Codelists: /codelist/{agency}/{codelist_id}/{version}

    Key differences from ECB:
    - Agency IDs are hierarchical (e.g., OECD.SDD.STES)
    - Dataflow IDs can contain @ (e.g., DSD_STES@DF_CLI)
    - Rate limit: 60 requests per hour
    - Supports both API v1 and v2 (we use v1 for consistency)
    """

    OECD_SDMX_BASE = "https://sdmx.oecd.org/public/rest"

    def __init__(self):
        super().__init__(self.OECD_SDMX_BASE)

    # -------------------------------------------------------------------------
    # HTTP helpers
    # -------------------------------------------------------------------------

    async def _request(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        context: str = "",
    ) -> httpx.Response:
        """Make HTTP request with unified error handling.

        Args:
            url: Request URL path
            params: Query parameters
            headers: Request headers
            context: Context string for error messages

        Returns:
            httpx.Response on success

        Raises:
            OECDConnectorError: On any HTTP or network error
        """
        try:
            response = await self.client.get(url, params=params, headers=headers)

            if response.status_code == 404:
                raise OECDConnectorError(f"Not found: {context or url}")
            if response.status_code == 422:
                raise OECDConnectorError(f"Invalid query: {context or url}")
            if response.status_code == 429:
                raise OECDConnectorError(
                    "Rate limited by OECD API (60 requests/hour). Try again later."
                )
            if response.status_code >= 500:
                raise OECDConnectorError(f"OECD API error: {response.status_code}")

            response.raise_for_status()
            return response

        except httpx.TimeoutException:
            raise OECDConnectorError("OECD API request timed out")
        except httpx.RequestError as e:
            raise OECDConnectorError(f"Network error: {e}")

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
        """Fetch a time series from OECD by dataset and series key.

        Args:
            dataset: Full dataset identifier in format "agency,dataflow,version"
                     e.g., "OECD.SDD.STES,DSD_STES@DF_CLI,4.1"
            series_key: Series key with dimension values separated by dots
                     e.g., "USA.M.LI.IX._Z.AA...H"
            start_period: Start period in ISO format (e.g., "2020-01")
            end_period: End period in ISO format (e.g., "2024-12")

        Returns:
            DataFrame with columns: date, value
        """
        url = f"/data/{dataset}/{series_key}"
        params: dict[str, str] = {}

        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period

        response = await self._request(
            url,
            params=params,
            headers={"Accept": "application/json"},
            context=f"{dataset}/{series_key}",
        )
        data = response.json()
        return self._parse_sdmx_json(data)

    def _parse_sdmx_json(self, data: dict) -> pd.DataFrame:
        """Parse SDMX-JSON response into DataFrame.

        OECD uses the same SDMX-JSON structure as ECB:
        {
            "dataSets": [{
                "series": {
                    "0:0:0:...": {
                        "observations": {
                            "0": [value, status],
                            "1": [value, status],
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
            raise OECDConnectorError(f"Failed to parse OECD response: {e}")

    async def get_metadata(self, dataset: str, series_key: str) -> dict:
        """Get metadata for a series from OECD."""
        url = f"/data/{dataset}/{series_key}"
        params = {"lastNObservations": "1"}

        try:
            response = await self._request(
                url,
                params=params,
                headers={"Accept": "application/json"},
                context=f"metadata/{dataset}/{series_key}",
            )
            data = response.json()

            structure = data.get("structure", {})
            dimensions = structure.get("dimensions", {})

            return {
                "dataset": dataset,
                "series_key": series_key,
                "source": "oecd",
                "dimensions": dimensions.get("series", []),
            }
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return {"dataset": dataset, "series_key": series_key, "source": "oecd"}

    # -------------------------------------------------------------------------
    # Metadata / Structure fetching
    # -------------------------------------------------------------------------

    async def fetch_dataflows(self, agency: str = "") -> list[dict[str, Any]]:
        """Fetch available dataflows (datasets).

        Args:
            agency: Optional agency filter (e.g., "OECD.SDD.STES").
                    If empty, fetches all OECD dataflows.

        Returns:
            List of dataflows with id, name, agency, and version
        """
        # If no agency specified, fetch from all OECD agencies
        url = f"/dataflow/{agency}" if agency else "/dataflow"

        response = await self._request(
            url,
            headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
            context=f"dataflows/{agency or 'all'}",
        )
        return self._parse_dataflows_xml(response.text)

    def _parse_dataflows_xml(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse dataflows XML response."""
        dataflows = []

        try:
            root = ET.fromstring(xml_text)

            for df_elem in root.findall(".//str:Dataflow", SDMX_NS):
                df_id = df_elem.get("id", "")
                version = df_elem.get("version", "")
                agency = df_elem.get("agencyID", "")

                # Skip non-OECD dataflows
                if not agency.startswith("OECD"):
                    continue

                # Get name (prefer English)
                name = ""
                for name_elem in df_elem.findall("com:Name", SDMX_NS):
                    lang = name_elem.get("{http://www.w3.org/XML/1998/namespace}lang", "")
                    if lang == "en" or not name:
                        name = name_elem.text or df_id

                # Get structure reference
                struct_ref = df_elem.find(".//str:Structure/Ref", SDMX_NS)
                if struct_ref is None:
                    struct_ref = df_elem.find(".//str:Structure", SDMX_NS)

                structure_id = ""
                structure_version = ""
                if struct_ref is not None:
                    structure_id = struct_ref.get("id", "")
                    structure_version = struct_ref.get("version", "")

                dataflows.append({
                    "id": df_id,
                    "name": name,
                    "version": version,
                    "agency": agency,
                    "structure_id": structure_id,
                    "structure_version": structure_version,
                })

        except ET.ParseError as e:
            logger.error(f"Failed to parse dataflows XML: {e}")

        return dataflows

    async def fetch_datastructure(
        self, agency: str, structure_id: str, version: str = "latest"
    ) -> dict[str, Any]:
        """Fetch the structure definition for a dataset.

        Args:
            agency: Agency ID (e.g., "OECD.SDD.STES")
            structure_id: Structure ID (e.g., "DSD_STES")
            version: Structure version (e.g., "4.1" or "latest")

        Returns:
            Dict with dimensions and their codelist references
        """
        url = f"/datastructure/{agency}/{structure_id}/{version}"
        params = {"references": "children"}

        try:
            response = await self._request(
                url,
                params=params,
                headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
                context=f"structure/{agency}/{structure_id}",
            )
            return self._parse_datastructure_xml(response.text, structure_id)
        except OECDConnectorError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch datastructure {structure_id}: {e}")
            raise OECDConnectorError(f"Failed to fetch structure: {e}")

    def _parse_datastructure_xml(
        self, xml_text: str, structure_id: str
    ) -> dict[str, Any]:
        """Parse datastructure XML response."""
        dimensions = []
        codelist_refs = {}
        codelists = {}

        try:
            root = ET.fromstring(xml_text)

            ds_elem = root.find(".//str:DataStructure", SDMX_NS)
            if ds_elem is None:
                return {
                    "id": structure_id,
                    "dimensions": [],
                    "codelist_refs": {},
                    "codelists": {},
                }

            dim_list = ds_elem.find(
                ".//str:DataStructureComponents/str:DimensionList", SDMX_NS
            )
            if dim_list is not None:
                for dim_elem in dim_list.findall("str:Dimension", SDMX_NS):
                    dim_id = dim_elem.get("id", "")
                    position = int(dim_elem.get("position", 0))

                    # Get codelist reference
                    codelist_id = ""
                    enum_elem = dim_elem.find(
                        ".//str:LocalRepresentation/str:Enumeration/Ref", SDMX_NS
                    )
                    if enum_elem is not None:
                        codelist_id = enum_elem.get("id", "")

                    dimensions.append({
                        "id": dim_id,
                        "position": position,
                        "codelist": codelist_id,
                    })
                    if codelist_id:
                        codelist_refs[dim_id] = codelist_id

            dimensions.sort(key=lambda x: x["position"])

            # Parse inline codelists if present
            for cl_elem in root.findall(".//str:Codelist", SDMX_NS):
                cl_id = cl_elem.get("id", "")
                codes = {}
                for code_elem in cl_elem.findall("str:Code", SDMX_NS):
                    code_id = code_elem.get("id", "")
                    # Prefer English name
                    code_name = ""
                    for name_elem in code_elem.findall("com:Name", SDMX_NS):
                        lang = name_elem.get(
                            "{http://www.w3.org/XML/1998/namespace}lang", ""
                        )
                        if lang == "en" or not code_name:
                            code_name = name_elem.text or code_id
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

    async def fetch_codelist(
        self, agency: str, codelist_id: str, version: str = "latest"
    ) -> dict[str, str]:
        """Fetch a codelist (valid values for a dimension).

        Args:
            agency: Agency ID (e.g., "OECD")
            codelist_id: Codelist ID (e.g., "CL_AREA")
            version: Codelist version (default: "latest")

        Returns:
            Dict mapping code -> description
        """
        url = f"/codelist/{agency}/{codelist_id}/{version}"

        try:
            response = await self._request(
                url,
                headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"},
                context=f"codelist/{agency}/{codelist_id}",
            )
            return self._parse_codelist_xml(response.text)
        except OECDConnectorError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch codelist {codelist_id}: {e}")
            return {}

    def _parse_codelist_xml(self, xml_text: str) -> dict[str, str]:
        """Parse codelist XML response."""
        codes = {}

        try:
            root = ET.fromstring(xml_text)

            cl_elem = root.find(".//str:Codelist", SDMX_NS)
            if cl_elem is None:
                return codes

            for code_elem in cl_elem.findall("str:Code", SDMX_NS):
                code_id = code_elem.get("id", "")
                # Prefer English name
                code_name = ""
                for name_elem in code_elem.findall("com:Name", SDMX_NS):
                    lang = name_elem.get(
                        "{http://www.w3.org/XML/1998/namespace}lang", ""
                    )
                    if lang == "en" or not code_name:
                        code_name = name_elem.text or code_id
                if code_id:
                    codes[code_id] = code_name

        except ET.ParseError as e:
            logger.error(f"Failed to parse codelist XML: {e}")

        return codes

    async def test_connection(self) -> bool:
        """Test OECD API connectivity with a known series."""
        try:
            # Test with CLI data for USA
            df = await self.fetch_series(
                dataset="OECD.SDD.STES,DSD_STES@DF_CLI,4.1",
                series_key="USA.M.LI.IX._Z.AA...H",
                start_period="2024-01",
            )
            return len(df) > 0
        except Exception as e:
            logger.error(f"OECD connection test failed: {e}")
            return False
