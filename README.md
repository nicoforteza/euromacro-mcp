# eurodata-mcp

> Structured macroeconomic data for AI agents.

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that gives AI agents clean, semantic access to macroeconomic time series from the ECB — with BIS, IMF, and FRED coming next.

## The problem

Macroeconomic data is free and public — but:
- Hidden behind cryptic codes like `ICP.M.U2.N.000000.4.INX`
- Fragmented across different APIs and formats (SDMX, JSON-stat, REST)
- Not agent-friendly: no semantic layer, no natural language search

## The solution

A two-layer catalog system on top of ECB's SDMX API:

1. **Curated series** — ~25 essential ECB series with bilingual names, tags, and direct series keys (instant answers to common questions)
2. **Enriched dataset catalog** — 100 ECB datasets with plain-English descriptions, analyst search concepts, and use-case examples (enables exploration of any series in the ECB warehouse)

## MCP Tools (11 total)

### Catalog tools
| Tool | Description |
|------|-------------|
| `search_series(query, provider?, frequency?, geo_coverage?)` | Find series or datasets by natural language |
| `get_series(id, start?, end?)` | Fetch time series data |
| `describe_series(id)` | Full metadata for a curated series |
| `list_categories()` | Browse available topics |

### Exploration tools
| Tool | Description |
|------|-------------|
| `explore_datasets(provider_id, query?, limit?)` | List available datasets for a provider |
| `explore_dimensions(provider_id, dataset)` | Show dimensions and series key format |
| `explore_codes(provider_id, dataset, dimension_id, query?, limit?)` | Valid codes for a dimension |
| `build_series(provider_id, dataset, dimensions, start_period?, end_period?)` | Construct any series key and API URL |

### Provider tools
| Tool | Description |
|------|-------------|
| `list_providers()` | Show available data providers |
| `get_provider_guide(provider_id)` | Get documentation for a provider |
| `find_provider(query)` | Route query to best provider |

## Data providers

| Provider | Coverage | Status |
|----------|----------|--------|
| **ECB** | Euro Area macro — 100 datasets, 300k+ series | ✅ Complete |
| **BIS** | Global banking, credit, property prices | 🔜 Next |
| **IMF** | World economic indicators, WEO projections | 🔜 Planned |
| **FRED** | US macro (Fed rates, CPI, payrolls, yields) | 🔜 Planned |

## Quick start

```bash
git clone https://github.com/nicoforteza/euromacro-mcp
cd euromacro-mcp
uv sync
uv run python -m eurodata_mcp.server
```

### Add to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run python -m eurodata_mcp.server
```

Open `http://localhost:5173` for a browser UI with all tools.

## Example queries

Once connected, ask Claude:

> "What is the current inflation rate in the Euro Area?"

> "Show me ECB deposit rate evolution since 2022"

> "Get monthly EUR/USD exchange rate since 2020"

> "What datasets does the ECB have about bank lending?"

> "Show me the dimensions of the HICP dataset and build a series for Spain"

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENTS                          │
│         Claude Desktop · Claude Code · AI agents        │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP Protocol (stdio)
┌──────────────────────▼──────────────────────────────────┐
│                    MCP SERVER                           │
│             server.py (FastMCP) — 11 tools              │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 PROVIDER REGISTRY                       │
│      ECBProvider ✅  ·  BIS/IMF/FRED 🔜                 │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Connectors     Two-layer       Metadata Cache
   (SDMX API)     Catalog         (fallback)
                  ├─ SeriesEntry   (25 curated)
                  └─ DatasetEntry  (100 enriched)
```

### Two-layer catalog

```
catalog/ecb/
├── catalog_enriched.json      ← 100 datasets with semantic metadata
├── enriched/{ID}.json         ← per-dataset: concepts, use_cases, frequency
└── structures/{ID}.json       ← per-dataset: dimensions, codes (from SDMX)
```

`search_series` first searches curated series (instant). If fewer than 3 matches, it falls through to the enriched dataset catalog and returns exploration hints.

## Development

```bash
uv sync                        # Install dependencies
uv run pytest                  # 110 tests (no network required)
uv run python -m eurodata_mcp.server  # Start server

# Catalog ingestion (run once, or to refresh)
uv run python scripts/ingest_ecb_structures.py   # Fetch SDMX structures
uv run python scripts/enrich_ecb_catalog.py      # Generate semantic metadata
```

## Documentation

- [ROADMAP.md](docs/ROADMAP.md) — Development milestones
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Technical design
- [DATA_SOURCES.md](docs/DATA_SOURCES.md) — API documentation
- [CATALOG_SCHEMA.md](docs/CATALOG_SCHEMA.md) — Series and dataset JSON schemas
- [catalog/ecb/README.md](catalog/ecb/README.md) — ECB catalog reference

## License

MIT. Underlying data from ECB is public under the ECB's open data terms.
