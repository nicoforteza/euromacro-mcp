# ARCHITECTURE

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                    │
│           Claude Desktop · Claude Code · REST API (future)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP Protocol (stdio / SSE)
┌────────────────────────────▼────────────────────────────────────────┐
│                        MCP SERVER                                    │
│                     server.py (FastMCP)                              │
│                                                                      │
│  Catalog Tools:           Exploration Tools:     Provider Tools:     │
│  · search_series          · explore_datasets     · list_providers    │
│  · get_series             · explore_dimensions   · get_provider_guide│
│  · describe_series        · explore_codes        · find_provider     │
│  · list_categories        · build_series                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      PROVIDER REGISTRY                               │
│                                                                      │
│  Manages providers and routes queries to appropriate source          │
│  · get(provider_id) → Provider                                       │
│  · find_best_provider(query) → Provider                              │
│  · find_providers(query) → [(Provider, score)]                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌────────▼───────┐   ┌───────▼───────┐
│  ECBProvider  │   │  BISProvider ↗ │   │ FREDProvider ↗│
│               │   │                │   │               │
│ guide.md      │   │ guide.md       │   │ guide.md      │
│ examples.json │   │ examples.json  │   │ examples.json │
│ aliases.json  │   │ aliases.json   │   │ aliases.json  │
└───────┬───────┘   └────────────────┘   └───────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────┐
│                        CONNECTORS                                  │
│                                                                    │
│  BaseConnector (ABC)                                               │
│  ├── ECBConnector (SDMX-JSON + SDMX-XML)                          │
│  ├── BISConnector ↗ (SDMX)                                        │
│  ├── IMFConnector ↗ (SDMX)                                        │
│  └── FREDConnector ↗ (REST JSON)                                  │
└───────┬───────────────────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────┐
│                         CATALOG                                    │
│                                                                    │
│  CatalogLoader (singleton)                                         │
│  · Loads series/*.json files                                       │
│  · Provides search and lookup                                      │
│  · SeriesEntry dataclass with full metadata                        │
└───────────────────────────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────┐
│                     METADATA CACHE                                 │
│                                                                    │
│  MetadataCache (per-provider)                                      │
│  · Dataflows (available datasets)                                  │
│  · Data structures (dimensions per dataset)                        │
│  · Codelists (valid values per dimension)                          │
└───────────────────────────────────────────────────────────────────┘

↗ = future milestone
```

---

## Provider Pattern

Each data source is encapsulated in a **Provider** that includes:

```
providers/
├── base.py              # BaseProvider ABC + ProviderRegistry
├── __init__.py
└── ecb/
    ├── __init__.py
    ├── provider.py      # ECBProvider(BaseProvider)
    ├── guide.md         # Conceptual documentation for AI agents
    ├── examples.json    # Common query patterns
    └── aliases.json     # Natural language → code mappings
```

### BaseProvider Interface

```python
class BaseProvider(ABC):
    # Identification
    id: str               # "ecb", "bis", "imf", "fred"
    name: str             # "European Central Bank"
    description: str
    base_url: str

    # Coverage metadata (for routing)
    coverage: dict = {
        "geography": ["euro_area", "germany", "spain", ...],
        "topics": ["inflation", "interest_rates", "gdp", ...],
        "frequency": ["daily", "monthly", "quarterly"],
    }

    # Keywords for aggregator routing
    keywords: list[str] = ["ecb", "euro", "hicp", "euribor", ...]

    # Documentation
    def get_guide(self) -> str           # Load guide.md
    def get_examples(self) -> list[dict] # Load examples.json
    def get_aliases(self) -> dict        # Load aliases.json
    def resolve_alias(self, text) -> str # "germany" → "DE"

    # Query matching (for aggregator)
    def matches_query(self, query: str) -> float  # 0.0-1.0

    # Data operations (abstract)
    async def search(self, query, limit) -> list[dict]
    async def fetch_series(self, series_id, start, end) -> dict
    async def get_series_metadata(self, series_id) -> dict
```

### ProviderRegistry

```python
class ProviderRegistry:
    def register(self, provider: BaseProvider) -> None
    def get(self, provider_id: str) -> BaseProvider | None
    def list_providers(self) -> list[dict]
    def find_best_provider(self, query: str) -> BaseProvider | None
    def find_providers(self, query: str, min_score: float) -> list[tuple]
```

---

## Data Flow Examples

### 1. Catalog-based query: `get_series("ecb_hicp_ea_yoy")`

```
1. MCP tool receives call
2. CatalogLoader.get("ecb_hicp_ea_yoy")
   → {source: "ecb", dataset: "ICP", key: "M.U2.N.000000.4.INX"}
3. ECBConnector.fetch_series("ICP", "M.U2.N.000000.4.INX")
   → HTTP GET ECB SDMX API
   → Parse SDMX-JSON → DataFrame[date, value]
4. Return SeriesData
```

### 2. Dynamic exploration: `build_series(dataset="ICP", dimensions={...})`

```
1. MCP tool receives call with dimensions
2. MetadataCache.get_structure("ICP")
   → Get dimension order: [FREQ, REF_AREA, ADJUSTMENT, ...]
3. Build series key: "M.DE.N.000000.4.INX"
4. ECBConnector.fetch_series("ICP", key)
5. Return SeriesData
```

### 3. Provider routing: `find_provider("US inflation")`

```
1. Query analyzed by ProviderRegistry
2. Each provider scores the query:
   - ECBProvider: 0.0 (no "US" in coverage)
   - FREDProvider: 0.8 (matches "US" + "inflation")
3. Return ranked results with best_match="fred"
```

---

## BaseConnector Interface

```python
class BaseConnector(ABC):

    @abstractmethod
    async def fetch_series(
        self,
        dataset: str,
        series_key: str,
        start_period: str | None = None,
        end_period: str | None = None
    ) -> pd.DataFrame:
        """Returns DataFrame with columns: date (str), value (float)"""
        ...

    @abstractmethod
    async def get_metadata(self, dataset: str, series_key: str) -> dict:
        """Returns dict with series metadata from the source"""
        ...

    async def test_connection(self) -> bool:
        """Verify API is reachable."""
        ...
```

### ECBConnector Extensions

```python
class ECBConnector(BaseConnector):
    # Standard interface
    async def fetch_series(...) -> pd.DataFrame
    async def get_metadata(...) -> dict

    # ECB-specific exploration
    async def fetch_dataflows() -> list[dict]        # Available datasets
    async def fetch_datastructure(id) -> dict        # Dimensions for dataset
    async def fetch_codelist(id) -> dict[str, str]   # Valid codes
```

---

## Catalog Schema

```python
@dataclass
class SeriesEntry:
    # Identification
    id: str                    # "ecb_hicp_ea_yoy"
    source: str                # "ecb"
    dataset: str               # "ICP"
    series_key: str            # "M.U2.N.000000.4.INX"

    # Names and descriptions
    name_en: str               # "Euro Area HICP Headline (YoY)"
    name_es: str               # "IPCA Zona Euro (interanual)"
    description_en: str

    # Data characteristics
    frequency: str             # "monthly"
    unit: str                  # "percent"
    geography: str             # "Euro Area"
    geography_code: str        # "U2"
    geography_level: str       # "aggregate"

    # Organization
    tags: list[str]            # ["inflation", "prices", "hicp"]
    category: str              # "prices"
    priority: int              # 1 (higher = less important)
```

---

## Metadata Cache Structure

```
metadata/
└── data/
    ├── dataflows.json         # All available datasets
    ├── structures/
    │   ├── ECB_ICP1.json      # Dimensions for ICP
    │   ├── ECB_FM1.json       # Dimensions for FM
    │   └── ...
    └── codelists/
        ├── CL_AREA.json       # Country codes
        ├── CL_FREQ.json       # Frequency codes
        └── ...
```

---

## MCP Tool Categories

### Catalog Tools (curated series)
| Tool | Purpose |
|------|---------|
| `search_series` | Text search across curated catalog |
| `get_series` | Fetch data by catalog ID |
| `describe_series` | Full metadata for a series |
| `list_categories` | Available categories |

### Exploration Tools (dynamic access)
| Tool | Purpose |
|------|---------|
| `explore_datasets` | List all ECB datasets |
| `explore_dimensions` | Dimensions for a dataset |
| `explore_codes` | Valid codes for a dimension |
| `build_series` | Construct and fetch any series |

### Provider Tools (multi-source)
| Tool | Purpose |
|------|---------|
| `list_providers` | Available data providers |
| `get_provider_guide` | Documentation for a provider |
| `find_provider` | Route query to best provider |

---

## Cache Strategy

| Series frequency | Cache TTL | Rationale |
|-----------------|-----------|-----------|
| Monthly | 7 days | Published once/month, stable |
| Quarterly | 30 days | Revised rarely |
| Annual | 90 days | Historical, very stable |
| Daily | 1 day | Market rates change daily |

Recent data (last 2 months) is always re-fetched regardless of TTL, since preliminary figures get revised.

---

## Adding a New Provider

1. Create provider directory: `providers/{id}/`
2. Write `guide.md` - conceptual documentation
3. Write `examples.json` - common queries
4. Write `aliases.json` - natural language mappings
5. Implement `{Id}Provider(BaseProvider)` in `provider.py`
6. Implement `{Id}Connector(BaseConnector)` in `connectors/{id}.py`
7. Register in `providers/base.py` `get_registry()`
8. Add catalog entries in `catalog/series/{id}_*.json`
