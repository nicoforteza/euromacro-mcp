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
1. Create `providers/{id}/` directory
2. Implement `{Id}Provider(BaseProvider)` in `provider.py`
3. Create `guide.md` with conceptual documentation
4. Create `examples.json` with common queries
5. Create `aliases.json` with natural language mappings
6. Implement `{Id}Connector(BaseConnector)` in `connectors/{id}.py`
7. Register in `providers/base.py` `get_registry()`

### Commit conventions
- `feat:` new features
- `fix:` bug fixes
- `refactor:` code restructuring
- `docs:` documentation changes
- `chore:` maintenance tasks
- `test:` test additions/changes

## Current status
**Milestone 1 — ECB Euro Area MVP: COMPLETED**

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
│                        MCP SERVER                                    │
│                     server.py (FastMCP)                              │
│                                                                      │
│  11 Tools:                                                           │
│  · Catalog: search_series, get_series, describe_series, list_categories
│  · Explore: explore_datasets, explore_dimensions, explore_codes, build_series
│  · Provider: list_providers, get_provider_guide, find_provider      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      PROVIDER REGISTRY                               │
│  ECBProvider ✅ · BISProvider 🔜 · IMFProvider 🔜 · FREDProvider 🔜  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   Connectors            Catalog            Metadata Cache
   (API clients)     (curated series)    (dataflows, codelists)
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
eurodata-mcp/
├── CLAUDE.md                 # This file — Claude Code instructions
├── README.md                 # Project overview
├── pyproject.toml
├── .mcp.json
├── .claude/
│   ├── settings.json
│   ├── commands/             # Slash commands
│   ├── agents/               # Sub-agents
│   └── skills/               # Reusable skills
├── src/eurodata_mcp/
│   ├── server.py             # FastMCP entry point (11 tools)
│   ├── tools/                # Tool implementations
│   │   ├── series.py         # Catalog tools
│   │   └── explore.py        # Exploration tools
│   ├── providers/            # Multi-source provider system
│   │   ├── base.py           # BaseProvider + ProviderRegistry
│   │   └── ecb/              # ECB provider
│   │       ├── provider.py   # ECBProvider class
│   │       ├── guide.md      # ECB data guide
│   │       ├── examples.json # Common queries
│   │       └── aliases.json  # Natural language mappings
│   ├── connectors/           # API clients
│   │   ├── base.py           # BaseConnector ABC
│   │   └── ecb.py            # ECBConnector (SDMX)
│   ├── catalog/              # Curated series catalog
│   │   ├── loader.py         # CatalogLoader singleton
│   │   └── series/           # JSON series files
│   ├── metadata/             # Metadata caching
│   │   └── cache.py          # MetadataCache
│   └── cache/                # Data caching
├── scripts/
│   └── bootstrap_metadata.py # Populate metadata cache
├── tests/
└── docs/
    ├── ROADMAP.md            # Development roadmap
    ├── ARCHITECTURE.md       # Technical architecture
    ├── DATA_SOURCES.md       # API documentation
    └── CATALOG_SCHEMA.md     # Series JSON schema
```

## Run locally
```bash
uv sync
uv run python -m eurodata_mcp.server   # stdio MCP server
uv run pytest                           # tests
```

## Add to Claude Desktop
```json
{
  "mcpServers": {
    "eurodata": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/repo", "python", "-m", "eurodata_mcp.server"]
    }
  }
}
```

## Core principles
1. **Catalog-first** — the curated series list is the IP; code is secondary
2. **Semantic over cryptic** — every series has human-readable names, descriptions, tags
3. **Provider pattern** — new data sources extend `BaseProvider` and `BaseConnector`
4. **Guide-driven** — each provider has documentation for AI agents
5. **Cache aggressively** — historical data never changes; only refresh recent months
6. **Fail gracefully** — if API is down, serve cached data with staleness warning

## Key files to understand
- `src/eurodata_mcp/server.py` — MCP tool definitions
- `src/eurodata_mcp/providers/base.py` — Provider architecture
- `src/eurodata_mcp/providers/ecb/guide.md` — ECB data guide
- `src/eurodata_mcp/connectors/ecb.py` — ECB API client
- `src/eurodata_mcp/catalog/series/ecb_euro_area.json` — Curated ECB series
