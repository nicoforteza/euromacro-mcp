"""Base provider class and registry."""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Abstract base class for data providers.

    Each provider (ECB, BIS, IMF, FRED, etc.) must implement this interface.
    Providers are responsible for:
    - Connecting to their data source API
    - Providing a guide for AI agents
    - Offering examples and aliases for common queries
    - Fetching and normalizing data
    """

    # Provider identification
    id: str = ""  # e.g., "ecb", "bis", "imf", "fred"
    name: str = ""  # e.g., "European Central Bank"
    description: str = ""
    base_url: str = ""

    # Coverage metadata
    coverage: dict[str, Any] = {
        "geography": [],  # e.g., ["euro_area", "eu", "global"]
        "topics": [],  # e.g., ["inflation", "interest_rates", "gdp"]
        "frequency": [],  # e.g., ["daily", "monthly", "quarterly"]
    }

    # Keywords for aggregator routing
    keywords: list[str] = []

    def __init__(self):
        self._guide: str | None = None
        self._examples: list[dict] | None = None
        self._aliases: dict[str, str] | None = None
        self._provider_dir = Path(__file__).parent / self.id

    # -------------------------------------------------------------------------
    # Guide and documentation
    # -------------------------------------------------------------------------

    def get_guide(self) -> str:
        """Get the provider's guide for AI agents."""
        if self._guide is None:
            guide_path = self._provider_dir / "guide.md"
            if guide_path.exists():
                self._guide = guide_path.read_text()
            else:
                self._guide = self._generate_default_guide()
        return self._guide

    def _generate_default_guide(self) -> str:
        """Generate a default guide if none exists."""
        return f"""# {self.name} Data Guide

## About
{self.description}

## Coverage
- Geography: {', '.join(self.coverage.get('geography', []))}
- Topics: {', '.join(self.coverage.get('topics', []))}
- Frequency: {', '.join(self.coverage.get('frequency', []))}

## API Documentation
{self.base_url}
"""

    def get_examples(self) -> list[dict]:
        """Get example queries for this provider."""
        if self._examples is None:
            examples_path = self._provider_dir / "examples.json"
            if examples_path.exists():
                self._examples = json.loads(examples_path.read_text())
            else:
                self._examples = []
        return self._examples

    def get_aliases(self) -> dict[str, str]:
        """Get natural language to code aliases."""
        if self._aliases is None:
            aliases_path = self._provider_dir / "aliases.json"
            if aliases_path.exists():
                self._aliases = json.loads(aliases_path.read_text())
            else:
                self._aliases = {}
        return self._aliases

    def resolve_alias(self, text: str) -> str:
        """Resolve a natural language term to its code."""
        aliases = self.get_aliases()
        text_lower = text.lower().strip()

        # Direct match
        if text_lower in aliases:
            return aliases[text_lower]

        # Partial match
        for alias, code in aliases.items():
            if alias in text_lower or text_lower in alias:
                return code

        return text

    # -------------------------------------------------------------------------
    # Data fetching (to be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for series matching a query."""
        pass

    @abstractmethod
    async def fetch_series(
        self,
        series_id: str,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> dict:
        """Fetch time series data."""
        pass

    @abstractmethod
    async def get_series_metadata(self, series_id: str) -> dict:
        """Get metadata for a series."""
        pass

    # -------------------------------------------------------------------------
    # Provider info
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Shipped catalog access (no network required)
    # -------------------------------------------------------------------------

    @property
    def catalog_dir(self) -> Path:
        """Directory containing this provider's shipped catalog files."""
        return self._provider_dir / "catalog"

    def get_enriched_catalog(self) -> list[dict]:
        """Load the consolidated enriched catalog for this provider."""
        path = self.catalog_dir / "catalog_enriched.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("datasets", [])

    def get_dataset_enriched(self, dataset_id: str) -> dict | None:
        """Load enriched metadata for a single dataset."""
        path = self.catalog_dir / "enriched" / f"{dataset_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get_dataset_structure(self, dataset_id: str) -> dict | None:
        """Load the SDMX structure for a single dataset."""
        path = self.catalog_dir / "structures" / f"{dataset_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # Provider info
    # -------------------------------------------------------------------------

    def get_info(self) -> dict:
        """Get provider information summary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "base_url": self.base_url,
            "coverage": self.coverage,
            "keywords": self.keywords,
            "has_guide": (self._provider_dir / "guide.md").exists(),
            "has_examples": (self._provider_dir / "examples.json").exists(),
            "has_aliases": (self._provider_dir / "aliases.json").exists(),
            "dataset_count": len(self.get_enriched_catalog()),
        }

    def matches_query(self, query: str) -> float:
        """Score how well this provider matches a query (0-1)."""
        query_lower = query.lower()
        score = 0.0
        matches = 0

        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in query_lower:
                score += 0.3
                matches += 1

        # Check coverage topics
        for topic in self.coverage.get("topics", []):
            if topic.lower() in query_lower:
                score += 0.2
                matches += 1

        # Check geography
        for geo in self.coverage.get("geography", []):
            if geo.lower() in query_lower:
                score += 0.2
                matches += 1

        # Check provider name
        if self.name.lower() in query_lower or self.id in query_lower:
            score += 0.5

        return min(score, 1.0)


class ProviderRegistry:
    """Registry of available data providers.

    Manages provider instances and routes queries to appropriate providers.
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider) -> None:
        """Register a provider."""
        self._providers[provider.id] = provider
        logger.info(f"Registered provider: {provider.id} ({provider.name})")

    def get(self, provider_id: str) -> BaseProvider | None:
        """Get a provider by ID."""
        return self._providers.get(provider_id)

    def list_providers(self) -> list[dict]:
        """List all registered providers."""
        return [p.get_info() for p in self._providers.values()]

    def find_best_provider(self, query: str) -> BaseProvider | None:
        """Find the best provider for a query."""
        best_provider = None
        best_score = 0.0

        for provider in self._providers.values():
            score = provider.matches_query(query)
            if score > best_score:
                best_score = score
                best_provider = provider

        return best_provider if best_score > 0.1 else None

    def find_providers(self, query: str, min_score: float = 0.1) -> list[tuple[BaseProvider, float]]:
        """Find all providers matching a query, sorted by score."""
        matches = []
        for provider in self._providers.values():
            score = provider.matches_query(query)
            if score >= min_score:
                matches.append((provider, score))

        matches.sort(key=lambda x: -x[1])
        return matches


# Global registry instance
_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        # Register available providers
        from .ecb import ECBProvider
        _registry.register(ECBProvider())
    return _registry
