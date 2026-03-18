# ARCHITECTURE

## System overview

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENTS                          │
│         Claude Desktop · Claude Code · REST API         │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP Protocol (stdio / SSE)
┌──────────────────────▼──────────────────────────────────┐
│                   MCP SERVER                            │
│                  server.py (FastMCP)                    │
│                                                         │
│  Tools registered:                                      │
│  · search_series(query) → SeriesResult[]                │
│  · get_series(id, start, end) → SeriesData              │
│  · describe_series(id) → SeriesMetadata                 │
│  · list_categories(topic?) → CategoryMap                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  QUERY ENGINE                           │
│                                                         │
│  1. Resolve series_id → (source, dataset, series_key)   │
│     via catalog lookup                                  │
│  2. Check SQLite cache                                  │
│  3. If miss → call connector                           │
│  4. Normalize → standard DataFrame schema               │
│  5. Write to cache                                      │
│  6. Return typed response                               │
└──────────┬──────────────────────┬───────────────────────┘
           │                      │
┌──────────▼──────┐    ┌──────────▼──────────────────────┐
│   CONNECTORS    │    │         CATALOG                  │
│                 │    │                                  │
│  base.py (ABC)  │    │  loader.py                       │
│  ecb.py         │    │  series/ecb_euro_area.json       │
│  eurostat.py ↗  │    │  series/eurostat_countries.json↗ │
│  ine.py ↗       │    │  series/ine_spain.json ↗         │
└─────────────────┘    └──────────────────────────────────┘
                                  │
                       ┌──────────▼──────────────────────┐
                       │          CACHE                   │
                       │  SQLiteCache (diskcache)         │
                       │  Key: (source, key, start, end)  │
                       │  TTL: configurable per frequency │
                       └─────────────────────────────────┘
```

↗ = future milestone

---

## Data flow: `get_series("ecb_hicp_ea_yoy", "2020-01", "2024-12")`

```
1. MCP tool receives call
2. QueryEngine.resolve("ecb_hicp_ea_yoy")
   → catalog lookup → {source: "ecb", dataset: "ICP", key: "M.U2.N.000000.4.INX"}
3. cache.get("ecb:ICP:M.U2.N.000000.4.INX:2020-01:2024-12")
   → MISS
4. ECBConnector.fetch_series("ICP", "M.U2.N.000000.4.INX", "2020-01", "2024-12")
   → HTTP GET to ECB SDMX API
   → Parse SDMX-JSON → DataFrame[date, value]
5. cache.set(key, df, ttl=7days)
6. Return SeriesData(id, dates[], values[], metadata)
```

---

## BaseConnector interface

```python
from abc import ABC, abstractmethod
import pandas as pd

class BaseConnector(ABC):
    
    @abstractmethod
    async def fetch_series(
        self, 
        dataset: str, 
        series_key: str, 
        start_period: str, 
        end_period: str | None = None
    ) -> pd.DataFrame:
        """Returns DataFrame with columns: date (str), value (float)"""
        ...

    @abstractmethod
    async def get_metadata(self, dataset: str, series_key: str) -> dict:
        """Returns dict with series metadata from the source"""
        ...

    async def test_connection(self) -> bool:
        """Verify API is reachable. Default: try fetching 1 observation."""
        try:
            # subclasses can override with a lighter check
            await self.fetch_series(self._test_dataset, self._test_key, start_period="2024-01")
            return True
        except Exception:
            return False
```

---

## Catalog loader

```python
# src/eurodata_mcp/catalog/loader.py

import json
from pathlib import Path
from dataclasses import dataclass

CATALOG_DIR = Path(__file__).parent / "series"

@dataclass 
class SeriesEntry:
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
    # ... optional fields

class CatalogLoader:
    def __init__(self):
        self._catalog: dict[str, SeriesEntry] = {}
        self._load_all()
    
    def _load_all(self):
        for path in CATALOG_DIR.glob("*.json"):
            data = json.loads(path.read_text())
            for entry in data["series"]:
                self._catalog[entry["id"]] = SeriesEntry(**entry)
    
    def get(self, series_id: str) -> SeriesEntry | None:
        return self._catalog.get(series_id)
    
    def search(self, query: str, limit: int = 10) -> list[SeriesEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self._catalog.values():
            score = 0
            if query_lower in entry.name_en.lower(): score += 10
            if query_lower in entry.description_en.lower(): score += 5
            for tag in entry.tags:
                if query_lower in tag: score += 3
            score -= entry.priority  # priority 1 ranks higher
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]
```

---

## MCP Tool response schemas

```python
# Tools return TypedDicts for FastMCP type hints

class SeriesPoint(TypedDict):
    date: str       # YYYY-MM or YYYY-Qn or YYYY
    value: float

class SeriesData(TypedDict):
    id: str
    name: str
    unit: str
    frequency: str
    observations: list[SeriesPoint]
    cached: bool
    cache_timestamp: str | None

class SeriesResult(TypedDict):
    id: str
    name_en: str
    name_es: str
    category: str
    frequency: str
    geography: str
    priority: int
    description_en: str
```

---

## Cache strategy

| Series frequency | Cache TTL | Rationale |
|---|---|---|
| Monthly | 7 days | Published once/month, stable |
| Quarterly | 30 days | Revised rarely |
| Annual | 90 days | Historical, very stable |
| Daily | 1 day | Market rates change daily |

Recent data (last 2 months) is always re-fetched regardless of TTL, since preliminary figures get revised.
