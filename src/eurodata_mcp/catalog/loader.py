"""Catalog loader for enriched dataset catalog."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DatasetEntry:
    """A dataset-level entry from the enriched provider catalog."""

    id: str
    provider_id: str
    name: str
    description_short: str
    concepts: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    primary_frequency: str = ""
    geographic_coverage: str = ""
    key_dimensions: list[str] = field(default_factory=list)

    def to_search_result(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider_id,
            "name": self.name,
            "description": self.description_short,
            "frequency": self.primary_frequency,
            "geographic_coverage": self.geographic_coverage,
            "key_dimensions": self.key_dimensions,
            "type": "dataset",
        }


class CatalogLoader:
    """Loads and searches the enriched dataset catalog."""

    def __init__(self):
        self._datasets: dict[str, DatasetEntry] = {}
        self._datasets_loaded: bool = False

    def _load_all_datasets(self) -> None:
        """Load enriched dataset catalog from all registered providers."""
        if self._datasets_loaded:
            return
        self._datasets_loaded = True
        try:
            from ..providers.base import get_registry  # deferred — avoids circular import
            registry = get_registry()
            for provider_info in registry.list_providers():
                provider = registry.get(provider_info["id"])
                if provider is None:
                    continue
                for d in provider.get_enriched_catalog():
                    entry = DatasetEntry(
                        id=d["id"],
                        provider_id=provider.id,
                        name=d.get("name", ""),
                        description_short=d.get("description_short", ""),
                        concepts=d.get("concepts", []),
                        use_cases=d.get("use_cases", []),
                        primary_frequency=d.get("primary_frequency", ""),
                        geographic_coverage=d.get("geographic_coverage", ""),
                        key_dimensions=d.get("key_dimensions", []),
                    )
                    self._datasets[f"{provider.id}:{entry.id}"] = entry
        except Exception:
            pass  # fail silently — catalog is best-effort

    def search_datasets(
        self,
        query: str,
        provider_id: str | None = None,
        limit: int = 10,
    ) -> list[DatasetEntry]:
        """Search dataset-level enriched catalog by concepts and use_cases."""
        self._load_all_datasets()
        query_lower = query.lower()
        terms = query_lower.split()
        scored: list[tuple[float, DatasetEntry]] = []

        for entry in self._datasets.values():
            if provider_id and entry.provider_id != provider_id:
                continue
            score = 0.0
            name_lower = entry.name.lower()
            desc_lower = entry.description_short.lower()
            for term in terms:
                if term in name_lower:
                    score += 15
                if term in desc_lower:
                    score += 5
                for concept in entry.concepts:
                    if term in concept.lower():
                        score += 8
                for use_case in entry.use_cases:
                    if term in use_case.lower():
                        score += 3
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def get_dataset(self, provider_id: str, dataset_id: str) -> DatasetEntry | None:
        """Get a single dataset entry by provider and dataset ID."""
        self._load_all_datasets()
        return self._datasets.get(f"{provider_id}:{dataset_id}")

    def list_all_datasets(self, provider_id: str | None = None) -> list[DatasetEntry]:
        """Return all loaded datasets, optionally filtered by provider."""
        self._load_all_datasets()
        if provider_id:
            return [e for e in self._datasets.values() if e.provider_id == provider_id]
        return list(self._datasets.values())

    def __len__(self) -> int:
        self._load_all_datasets()
        return len(self._datasets)


_catalog_instance: CatalogLoader | None = None


def get_catalog() -> CatalogLoader:
    """Get the singleton catalog instance."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = CatalogLoader()
    return _catalog_instance
