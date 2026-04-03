# CLAUDE.md — eurodata-mcp

## What this is
An MCP server exposing curated macroeconomic time series to AI agents. The value is **not** the data (public) — it's the semantic catalog and multi-provider infrastructure built on top of it.

## Development protocols

### Language
- **Code**: Always English (variables, functions, comments, docstrings)
- **Documentation**: Always English (README, docs/, inline comments)
- **Git commits**: Always English
- **Catalog entries**: Bilingual (name_en, name_es, description_en, description_es)

### Code style
- Use `uv` for package management
- Follow existing patterns in codebase
- Type hints required for all public functions
- Async/await for all I/O operations
- No personal names or attributions in code or docs

### Provider pattern
When adding new data sources, follow the established pattern:
1. Create `providers/{id}/` directory with `provider.py`, `guide.md`, `examples.json`, `aliases.json`
2. Override `catalog_dir` to point to `catalog/{id}/` at the repo root
3. Override `data_api_url` property with the provider's API base URL
4. Override `get_connector_class()` to return the connector class
5. Run ingestion script → writes to `catalog/{id}/structures/` and `catalog/{id}/enriched/`
6. Implement `{Id}Connector(BaseConnector)` in `connectors/{id}.py`
7. Register in `providers/base.py` `get_registry()`
8. (Optional) Add curated series to `src/eurodata_mcp/catalog/series/{id}_*.json`

### Commit conventions
- `feat:` new features
- `fix:` bug fixes
- `refactor:` code restructuring
- `docs:` documentation changes
- `chore:` maintenance tasks
- `test:` test additions/changes

## Current status
**Milestone 1 — ECB Euro Area: COMPLETED**
- 100 ECB datasets ingested (SDMX structures + semantic enrichment)
- Two-layer catalog: 25 curated series + 100 enriched datasets
- 11 MCP tools, fully provider-agnostic (no hard-coded provider checks)
- 120 tests passing (no network)

Next milestones:
- M2: BIS (Bank for International Settlements)
- M3: IMF (International Monetary Fund)
- M4: FRED (Federal Reserve St. Louis)

See `docs/ROADMAP.md` for full plan.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                    │
│           Claude Desktop · Claude Code · REST API (future)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP Protocol (stdio / SSE)
┌────────────────────────────▼────────────────────────────────────────┐
│                        MCP SERVER (server.py / FastMCP)              │
│                                                                      │
│  Catalog:  search_series · get_series · describe_series · list_categories
│  Explore:  explore_datasets · explore_dimensions · explore_codes · build_series
│  Provider: list_providers · get_provider_guide · find_provider      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      PROVIDER REGISTRY                               │
│  ECBProvider ✅ · BISProvider 🔜 · IMFProvider 🔜 · FREDProvider 🔜  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   Connectors         Two-layer Catalog      Metadata Cache
   (API clients)      ├─ SeriesEntry         (SDMX fallback)
                      │  (25 curated)
                      └─ DatasetEntry
                         (100 enriched)
```

## Stack
| Layer | Tech |
|---|---|
| MCP server | `fastmcp` |
| HTTP client | `httpx` (async) |
| Cache | `diskcache` + SQLite |
| Data processing | `pandas` |
| Package manager | `uv` |
| Tests | `pytest` + `pytest-asyncio` |

## Directory layout
```
euromacro-mcp/
├── CLAUDE.md                  # This file
├── README.md
├── pyproject.toml
├── .mcp.json
├── catalog/                   # Single source of truth for catalog data
│   └── ecb/                   # Written by ingestion scripts, read at runtime
│       ├── README.md
│       ├── catalog_base.json  # Ingestion index
│       ├── catalog_enriched.json  # 100 datasets with semantic metadata
│       ├── enriched/          # Per-dataset semantic JSON (100 files)
│       ├── structures/        # Per-dataset SDMX structure JSON (100 files)
│       └── errors/            # Failed fetches
├── scripts/
│   ├── ingest_ecb_structures.py   # Fetch SDMX structures from ECB API
│   └── enrich_ecb_catalog.py      # Generate semantic metadata via LLM
├── src/eurodata_mcp/
│   ├── server.py              # FastMCP entry point (11 tools)
│   ├── tools/
│   │   ├── series.py          # search_series, get_series, describe_series, list_categories
│   │   └── explore.py         # explore_datasets, explore_dimensions, explore_codes, build_series
│   ├── providers/
│   │   ├── base.py            # BaseProvider + ProviderRegistry
│   │   └── ecb/
│   │       ├── provider.py    # ECBProvider (catalog_dir → catalog/ecb/)
│   │       ├── guide.md       # ECB data guide for AI agents
│   │       ├── examples.json
│   │       └── aliases.json
│   ├── connectors/
│   │   ├── base.py            # BaseConnector ABC
│   │   └── ecb.py             # ECBConnector (SDMX)
│   ├── catalog/
│   │   ├── loader.py          # CatalogLoader: SeriesEntry + DatasetEntry
│   │   └── series/
│   │       └── ecb_euro_area.json  # 25 curated ECB series
│   ├── metadata/
│   │   └── cache.py           # MetadataCache (live SDMX fallback)
│   └── cache/
├── tests/
│   ├── test_catalog.py             # Curated series tests
│   ├── test_ecb_dataset_catalog.py # Dataset catalog + explore tools (23 tests)
│   ├── test_natural_language.py    # End-to-end NL flow tests (65 tests)
│   ├── test_tools.py               # MCP tool tests
│   └── test_ecb_connector.py       # Network tests (skipped in CI)
└── docs/
    ├── ROADMAP.md
    ├── ARCHITECTURE.md
    ├── DATA_SOURCES.md
    └── CATALOG_SCHEMA.md
```

## Run locally
```bash
uv sync
uv run python -m eurodata_mcp.server   # stdio MCP server
uv run pytest                           # 120 tests, no network needed
```

## Add to Claude Desktop
```json
{
  "mcpServers": {
    "eurodata": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/euromacro-mcp", "python", "-m", "eurodata_mcp.server"]
    }
  }
}
```

## Core principles
1. **Catalog-first** — the curated series list is the IP; code is secondary
2. **Two-layer search** — curated series (fast, precise) + enriched datasets (broad, explorable)
3. **Provider pattern** — new data sources extend `BaseProvider`; `catalog_dir` points to `catalog/{id}/`
4. **Single source of truth** — `catalog/ecb/` is written by ingestion scripts and read directly at runtime; no copies
5. **Cache aggressively** — historical data never changes; only refresh recent months
6. **Fail gracefully** — if API is down, serve cached data; MetadataCache is fallback for explore tools

## Key files to understand
- `src/eurodata_mcp/server.py` — MCP tool definitions
- `src/eurodata_mcp/catalog/loader.py` — CatalogLoader with SeriesEntry + DatasetEntry
- `src/eurodata_mcp/providers/base.py` — BaseProvider ABC with catalog_dir, data_api_url, get_connector_class(), get_enriched_catalog(), get_dataset_structure()
- `src/eurodata_mcp/providers/ecb/provider.py` — ECBProvider (overrides catalog_dir, data_api_url, get_connector_class)
- `src/eurodata_mcp/connectors/base.py` — BaseConnector ABC with fetch_series(), get_metadata()
- `src/eurodata_mcp/tools/explore.py` — explore_* tools reading from shipped catalog (provider-agnostic)
- `src/eurodata_mcp/tools/series.py` — get_series uses provider registry (provider-agnostic)
- `catalog/ecb/catalog_enriched.json` — 100 ECB datasets with semantic metadata
