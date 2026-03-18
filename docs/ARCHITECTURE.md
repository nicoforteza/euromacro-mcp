# ARCHITECTURE

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                    │
│           Claude Desktop · Claude Code · REST API (future)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP Protocol (stdio / SSE)
┌────────────────────────────▼────────────────────────────────────────┐
│                        MCP SERVER (server.py / FastMCP)              │
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
│  Manages providers and routes queries to appropriate source.         │
│  · get(provider_id) → Provider                                       │
│  · find_best_provider(query) → Provider                              │
│  · list_providers() → [info dicts]                                   │
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
│               │   │                │   │               │
│ catalog_dir   │   │ catalog_dir    │   │ catalog_dir   │
│ → catalog/ecb/│   │ → catalog/bis/ │   │ →catalog/fred/│
└───────┬───────┘   └────────────────┘   └───────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────┐
│                      TWO-LAYER CATALOG                             │
│                                                                    │
│  Layer 1 — Curated Series (CatalogLoader / SeriesEntry)           │
│  · 25 hand-picked ECB series with bilingual names and series keys │
│  · Instant answers to common macro questions                      │
│  · src/eurodata_mcp/catalog/series/ecb_euro_area.json             │
│                                                                    │
│  Layer 2 — Enriched Dataset Catalog (CatalogLoader / DatasetEntry)│
│  · 100 ECB datasets with semantic concepts and use-case examples  │
│  · Enables exploration of any of the 300k+ ECB series             │
│  · catalog/ecb/enriched/{ID}.json + catalog_enriched.json         │
└───────┬───────────────────────────────────────────────────────────┘
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
│                     METADATA CACHE (fallback)                      │
│                                                                    │
│  MetadataCache — used when structure not in shipped catalog        │
│  · Dataflows (available datasets from live ECB API)               │
│  · Data structures (dimensions per dataset)                        │
│  · Codelists (valid values per dimension)                          │
└───────────────────────────────────────────────────────────────────┘

↗ = future milestone
```

---

## Catalog Data Flow

The explore tools follow a **catalog-first, live-fallback** pattern:

```
explore_dimensions(provider_id="ecb", dataset="EXR")
    │
    ├─► ECBProvider.get_dataset_structure("EXR")
    │       └─► reads catalog/ecb/structures/EXR.json  (no network)
    │           returns dimensions + inline codes
    │
    └─► [fallback] MetadataCache.get_structure("EXR")
            └─► HTTP GET ECB SDMX API  (only if structure file missing)
```

```
search_series("exchange rate")
    │
    ├─► Layer 1: CatalogLoader.search()  →  SeriesEntry matches
    │       fast text search over 25 curated series
    │
    └─► if < 3 results: Layer 2: CatalogLoader.search_datasets()
            scored search over 100 DatasetEntry objects
            returns dataset hints with explore_dimensions() pointer
```

---

## Provider Pattern

Each data source is encapsulated in a **Provider**:

```
providers/
├── base.py              # BaseProvider ABC + ProviderRegistry
└── ecb/
    ├── provider.py      # ECBProvider(BaseProvider)
    ├── guide.md         # Conceptual documentation for AI agents
    ├── examples.json    # Common query patterns
    └── aliases.json     # Natural language → code mappings

catalog/                 # Single source of truth — written by scripts
└── ecb/
    ├── catalog_enriched.json
    ├── enriched/{ID}.json   (100 files)
    └── structures/{ID}.json (100 files)
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
        "geography": ["euro_area", "germany", ...],
        "topics":    ["inflation", "interest_rates", "gdp", ...],
        "frequency": ["daily", "monthly", "quarterly"],
    }
    keywords: list[str] = ["ecb", "euro", "hicp", "euribor", ...]

    # Catalog access — points to catalog/{id}/ at repo root
    @property
    def catalog_dir(self) -> Path: ...

    def get_enriched_catalog(self) -> list[dict]          # 100 datasets
    def get_dataset_enriched(self, dataset_id) -> dict    # single dataset
    def get_dataset_structure(self, dataset_id) -> dict   # SDMX structure

    # Documentation
    def get_guide(self) -> str
    def get_examples(self) -> list[dict]
    def get_aliases(self) -> dict

    # Query matching (for aggregator)
    def matches_query(self, query: str) -> float          # 0.0–1.0

    # Data operations (abstract)
    async def search(self, query, limit) -> list[dict]
    async def fetch_series(self, series_id, start, end) -> dict
    async def get_series_metadata(self, series_id) -> dict
```

### Adding a New Provider

1. Create `providers/{id}/` with `provider.py`, `guide.md`, `examples.json`, `aliases.json`
2. Override `catalog_dir` to point to `catalog/{id}/` (walk up to repo root using `pyproject.toml`)
3. Create ingestion script `scripts/ingest_{id}_structures.py`
4. Run ingestion → writes to `catalog/{id}/structures/` and `catalog/{id}/enriched/`
5. Implement `{Id}Connector(BaseConnector)` in `connectors/{id}.py`
6. Register in `providers/base.py` `get_registry()`
7. Add curated series to `src/eurodata_mcp/catalog/series/{id}_*.json`

---

## Catalog Schema

### Layer 1 — SeriesEntry (curated)

```python
@dataclass
class SeriesEntry:
    id: str              # "ecb_hicp_ea_yoy"
    source: str          # "ecb"
    dataset: str         # "ICP"
    series_key: str      # "M.U2.N.000000.4.INX"
    name_en: str
    name_es: str
    description_en: str
    frequency: str       # "monthly"
    unit: str
    geography: str       # "euro_area"
    geography_code: str  # "U2"
    tags: list[str]
    category: str        # "prices"
    priority: int        # 1 = essential
```

### Layer 2 — DatasetEntry (enriched)

```python
@dataclass
class DatasetEntry:
    id: str                   # "EXR"
    provider_id: str          # "ecb"
    name: str                 # "Exchange Rates"
    description_short: str    # plain-English description
    concepts: list[str]       # ["exchange rate", "EUR", "FX", ...]
    use_cases: list[str]      # ["What is EUR/USD?", ...]
    primary_frequency: str    # "D"
    geographic_coverage: str  # "global"
    key_dimensions: list[str] # ["CURRENCY", "CURRENCY_DENOM", ...]
```

---

## Data Flow Examples

### 1. Curated series: `get_series("ecb_hicp_ea_yoy")`

```
1. CatalogLoader.get("ecb_hicp_ea_yoy")
   → {source: "ecb", dataset: "ICP", key: "M.U2.N.000000.4.INX"}
2. ECBConnector.fetch_series("ICP", "M.U2.N.000000.4.INX")
   → HTTP GET ECB SDMX API
   → Parse SDMX-JSON → DataFrame[date, value]
3. Return SeriesData
```

### 2. Dynamic exploration: `explore_dimensions("ecb", "EXR")`

```
1. ECBProvider.get_dataset_structure("EXR")
   → reads catalog/ecb/structures/EXR.json  (no network)
2. Return dimensions + series_key_format: "<FREQ>.<CURRENCY>.<CURRENCY_DENOM>.<EXR_TYPE>.<EXR_SUFFIX>"
```

### 3. Build any series: `build_series("ecb", "EXR", {"FREQ":"M","CURRENCY":"USD",...})`

```
1. Load dimension order from catalog/ecb/structures/EXR.json
2. Join values in position order → "M.USD.EUR.SP00.A"
3. Return series key + data URL:
   https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?format=jsondata
```

### 4. Provider routing: `find_provider("US inflation")`

```
1. ProviderRegistry.find_providers("US inflation")
2. Each provider scores the query:
   - ECBProvider: 0.1 (no "US" in coverage)
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
        end_period: str | None = None,
    ) -> pd.DataFrame:
        """Returns DataFrame with columns: date (str), value (float)"""

    @abstractmethod
    async def get_metadata(self, dataset: str, series_key: str) -> dict:
        """Returns dict with series metadata from the source"""

    async def test_connection(self) -> bool:
        """Verify API is reachable."""
```

---

## Cache Strategy

| Series frequency | Cache TTL | Rationale |
|-----------------|-----------|-----------|
| Monthly         | 7 days    | Published once/month, stable |
| Quarterly       | 30 days   | Revised rarely |
| Annual          | 90 days   | Historical, very stable |
| Daily           | 1 day     | Market rates change daily |

Recent data (last 2 months) is always re-fetched regardless of TTL, since preliminary figures get revised.

Catalog files (`catalog/ecb/structures/`, `catalog/ecb/enriched/`) are static — regenerate with ingestion scripts, never at runtime.
