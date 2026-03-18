"""Catalog loader for curated series definitions."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CATALOG_DIR = Path(__file__).parent / "series"


@dataclass
class SeriesEntry:
    """A curated series entry from the catalog."""

    id: str
    source: str
    dataset: str
    series_key: str
    name_en: str
    name_es: str
    description_en: str
    frequency: str
    unit: str
    geography: str
    geography_code: str
    geography_level: str
    tags: list[str]
    category: str
    priority: int
    subcategory: str = ""
    seasonal_adjustment: str = "not_adjusted"
    notes: str = ""
    availability: dict = field(default_factory=dict)
    related_series: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SeriesEntry":
        """Create SeriesEntry from a dict, handling optional fields."""
        return cls(
            id=data["id"],
            source=data["source"],
            dataset=data["dataset"],
            series_key=data["series_key"],
            name_en=data["name_en"],
            name_es=data.get("name_es", data["name_en"]),
            description_en=data["description_en"],
            frequency=data["frequency"],
            unit=data["unit"],
            geography=data.get("geography", ""),
            geography_code=data.get("geography_code", ""),
            geography_level=data.get("geography_level", ""),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            priority=data.get("priority", 3),
            subcategory=data.get("subcategory", ""),
            seasonal_adjustment=data.get("seasonal_adjustment", "not_adjusted"),
            notes=data.get("notes", ""),
            availability=data.get("availability", {}),
            related_series=data.get("related_series", []),
        )

    def to_search_result(self) -> dict:
        """Convert to search result format."""
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_es": self.name_es,
            "category": self.category,
            "frequency": self.frequency,
            "geography": self.geography,
            "priority": self.priority,
            "description_en": self.description_en,
        }

    def to_full_metadata(self) -> dict:
        """Convert to full metadata format."""
        return {
            "id": self.id,
            "source": self.source,
            "dataset": self.dataset,
            "series_key": self.series_key,
            "name_en": self.name_en,
            "name_es": self.name_es,
            "description_en": self.description_en,
            "frequency": self.frequency,
            "unit": self.unit,
            "geography": self.geography,
            "geography_code": self.geography_code,
            "geography_level": self.geography_level,
            "tags": self.tags,
            "category": self.category,
            "subcategory": self.subcategory,
            "priority": self.priority,
            "seasonal_adjustment": self.seasonal_adjustment,
            "notes": self.notes,
            "availability": self.availability,
            "related_series": self.related_series,
        }


class CatalogLoader:
    """Loads and searches the curated series catalog."""

    def __init__(self):
        self._catalog: dict[str, SeriesEntry] = {}
        self._categories: dict[str, list[str]] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all catalog files from the series directory."""
        if not CATALOG_DIR.exists():
            logger.warning(f"Catalog directory not found: {CATALOG_DIR}")
            return

        for path in CATALOG_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                series_list = data.get("series", [])
                for entry_data in series_list:
                    entry = SeriesEntry.from_dict(entry_data)
                    self._catalog[entry.id] = entry

                    if entry.category not in self._categories:
                        self._categories[entry.category] = []
                    self._categories[entry.category].append(entry.id)

                logger.info(f"Loaded {len(series_list)} series from {path.name}")
            except Exception as e:
                logger.error(f"Failed to load catalog {path}: {e}")

    def get(self, series_id: str) -> SeriesEntry | None:
        """Get a series by ID."""
        return self._catalog.get(series_id)

    def get_all(self) -> list[SeriesEntry]:
        """Get all series in the catalog."""
        return list(self._catalog.values())

    def search(self, query: str, limit: int = 10) -> list[SeriesEntry]:
        """Search for series matching a query.

        Searches across name, description, and tags.
        Results are scored and sorted by relevance, with priority as tiebreaker.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching SeriesEntry objects
        """
        query_lower = query.lower()
        query_terms = query_lower.split()
        scored: list[tuple[int, SeriesEntry]] = []

        for entry in self._catalog.values():
            score = 0

            name_lower = entry.name_en.lower()
            desc_lower = entry.description_en.lower()
            name_es_lower = entry.name_es.lower()

            for term in query_terms:
                if term in name_lower:
                    score += 15
                if term in name_es_lower:
                    score += 12
                if term in desc_lower:
                    score += 5
                for tag in entry.tags:
                    if term in tag.lower():
                        score += 8
                if term == entry.category.lower():
                    score += 10
                if term in entry.id.lower():
                    score += 5

            if score > 0:
                final_score = score * 10 - entry.priority
                scored.append((final_score, entry))

        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def list_categories(self) -> dict[str, int]:
        """List all categories with their series count."""
        return {cat: len(series) for cat, series in self._categories.items()}

    def get_by_category(self, category: str) -> list[SeriesEntry]:
        """Get all series in a category."""
        series_ids = self._categories.get(category, [])
        return [self._catalog[sid] for sid in series_ids if sid in self._catalog]

    def __len__(self) -> int:
        return len(self._catalog)


_catalog_instance: CatalogLoader | None = None


def get_catalog() -> CatalogLoader:
    """Get the singleton catalog instance."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = CatalogLoader()
    return _catalog_instance


def load_catalog(name: str = "ecb_euro_area") -> list[dict]:
    """Legacy function: Load a catalog file by name.

    Deprecated: Use get_catalog() instead.
    """
    catalog_file = CATALOG_DIR / f"{name}.json"
    if not catalog_file.exists():
        return []
    with open(catalog_file) as f:
        data = json.load(f)
        return data.get("series", data if isinstance(data, list) else [])
