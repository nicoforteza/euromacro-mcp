"""ECB metadata cache for dataflows, structures, and codelists."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

METADATA_DIR = Path(__file__).parent / "data"


class MetadataCache:
    """Cache for ECB metadata (dataflows, structures, codelists).

    Stores metadata on disk as JSON files for fast access.
    The cache is populated by the bootstrap script or on-demand.

    Directory structure:
        metadata/data/
        ├── dataflows.json           # All ECB datasets
        ├── structures/
        │   ├── ECB_ICP1.json       # Structure for ICP dataset
        │   ├── ECB_FM1.json        # Structure for FM dataset
        │   └── ...
        └── codelists/
            ├── CL_AREA.json        # Country/area codes
            ├── CL_FREQ.json        # Frequency codes
            └── ...
    """

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or METADATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "structures").mkdir(exist_ok=True)
        (self.cache_dir / "codelists").mkdir(exist_ok=True)

        self._dataflows: list[dict] | None = None
        self._dataflow_index: dict[str, dict] | None = None
        self._structures: dict[str, dict] = {}
        self._codelists: dict[str, dict[str, str]] = {}

    # -------------------------------------------------------------------------
    # Dataflows
    # -------------------------------------------------------------------------

    def get_dataflows(self) -> list[dict]:
        """Get all cached dataflows."""
        if self._dataflows is None:
            self._load_dataflows()
        return self._dataflows or []

    def get_dataflow(self, dataflow_id: str) -> dict | None:
        """Get a specific dataflow by ID."""
        if self._dataflow_index is None:
            self._load_dataflows()
        return (self._dataflow_index or {}).get(dataflow_id)

    def search_dataflows(self, query: str, limit: int = 20) -> list[dict]:
        """Search dataflows by name or ID."""
        query_lower = query.lower()
        dataflows = self.get_dataflows()

        results = []
        for df in dataflows:
            name = df.get("name", "")
            df_id = df.get("id", "")
            if query_lower in name.lower() or query_lower in df_id.lower():
                results.append(df)
                if len(results) >= limit:
                    break

        return results

    def save_dataflows(self, dataflows: list[dict]) -> None:
        """Save dataflows to cache."""
        cache_file = self.cache_dir / "dataflows.json"
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(dataflows),
            "dataflows": dataflows,
        }
        cache_file.write_text(json.dumps(data, indent=2))
        self._dataflows = dataflows
        self._dataflow_index = {df["id"]: df for df in dataflows}
        logger.info(f"Saved {len(dataflows)} dataflows to cache")

    def _load_dataflows(self) -> None:
        """Load dataflows from cache file."""
        cache_file = self.cache_dir / "dataflows.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                self._dataflows = data.get("dataflows", [])
                self._dataflow_index = {df["id"]: df for df in self._dataflows}
                logger.info(f"Loaded {len(self._dataflows)} dataflows from cache")
            except Exception as e:
                logger.error(f"Failed to load dataflows: {e}")
                self._dataflows = []
                self._dataflow_index = {}
        else:
            self._dataflows = []
            self._dataflow_index = {}

    # -------------------------------------------------------------------------
    # Structures
    # -------------------------------------------------------------------------

    def get_structure(self, structure_id: str) -> dict | None:
        """Get a cached data structure."""
        if structure_id in self._structures:
            return self._structures[structure_id]

        cache_file = self.cache_dir / "structures" / f"{structure_id}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                self._structures[structure_id] = data
                return data
            except Exception as e:
                logger.error(f"Failed to load structure {structure_id}: {e}")

        return None

    def save_structure(self, structure_id: str, structure: dict) -> None:
        """Save a data structure to cache."""
        cache_file = self.cache_dir / "structures" / f"{structure_id}.json"
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **structure,
        }
        cache_file.write_text(json.dumps(data, indent=2))
        self._structures[structure_id] = data
        logger.info(f"Saved structure {structure_id} to cache")

    def list_cached_structures(self) -> list[str]:
        """List all cached structure IDs."""
        structures_dir = self.cache_dir / "structures"
        return [f.stem for f in structures_dir.glob("*.json")]

    # -------------------------------------------------------------------------
    # Codelists
    # -------------------------------------------------------------------------

    def get_codelist(self, codelist_id: str) -> dict[str, str] | None:
        """Get a cached codelist."""
        if codelist_id in self._codelists:
            return self._codelists[codelist_id]

        cache_file = self.cache_dir / "codelists" / f"{codelist_id}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                codes = data.get("codes", {})
                self._codelists[codelist_id] = codes
                return codes
            except Exception as e:
                logger.error(f"Failed to load codelist {codelist_id}: {e}")

        return None

    def search_codelist(
        self, codelist_id: str, query: str, limit: int = 20
    ) -> list[dict]:
        """Search within a codelist by code or description."""
        codes = self.get_codelist(codelist_id)
        if not codes:
            return []

        query_lower = query.lower()
        results = []

        for code, description in codes.items():
            if query_lower in code.lower() or query_lower in description.lower():
                results.append({"code": code, "description": description})
                if len(results) >= limit:
                    break

        return results

    def save_codelist(self, codelist_id: str, codes: dict[str, str]) -> None:
        """Save a codelist to cache."""
        cache_file = self.cache_dir / "codelists" / f"{codelist_id}.json"
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "codelist_id": codelist_id,
            "count": len(codes),
            "codes": codes,
        }
        cache_file.write_text(json.dumps(data, indent=2))
        self._codelists[codelist_id] = codes
        logger.info(f"Saved codelist {codelist_id} with {len(codes)} codes")

    def list_cached_codelists(self) -> list[str]:
        """List all cached codelist IDs."""
        codelists_dir = self.cache_dir / "codelists"
        return [f.stem for f in codelists_dir.glob("*.json")]

    # -------------------------------------------------------------------------
    # Series key building
    # -------------------------------------------------------------------------

    def build_series_key(
        self, structure_id: str, dimension_values: dict[str, str]
    ) -> str | None:
        """Build a series key from dimension values.

        Args:
            structure_id: The data structure ID
            dimension_values: Dict mapping dimension ID to value

        Returns:
            Series key string (e.g., "M.U2.N.000000.4.INX") or None if invalid
        """
        structure = self.get_structure(structure_id)
        if not structure:
            logger.error(f"Structure {structure_id} not found in cache")
            return None

        dimensions = structure.get("dimensions", [])
        if not dimensions:
            logger.error(f"No dimensions found in structure {structure_id}")
            return None

        key_parts = []
        for dim in dimensions:
            dim_id = dim["id"]
            value = dimension_values.get(dim_id, "")
            key_parts.append(value)

        return ".".join(key_parts)

    # -------------------------------------------------------------------------
    # Cache status
    # -------------------------------------------------------------------------

    def get_cache_status(self) -> dict[str, Any]:
        """Get status of the metadata cache."""
        dataflows_file = self.cache_dir / "dataflows.json"
        dataflows_updated = None
        dataflows_count = 0

        if dataflows_file.exists():
            try:
                data = json.loads(dataflows_file.read_text())
                dataflows_updated = data.get("updated_at")
                dataflows_count = data.get("count", 0)
            except Exception:
                pass

        return {
            "cache_dir": str(self.cache_dir),
            "dataflows": {
                "count": dataflows_count,
                "updated_at": dataflows_updated,
            },
            "structures": {
                "count": len(self.list_cached_structures()),
            },
            "codelists": {
                "count": len(self.list_cached_codelists()),
            },
        }


# Singleton instance
_metadata_cache: MetadataCache | None = None


def get_metadata_cache() -> MetadataCache:
    """Get the singleton metadata cache instance."""
    global _metadata_cache
    if _metadata_cache is None:
        _metadata_cache = MetadataCache()
    return _metadata_cache
