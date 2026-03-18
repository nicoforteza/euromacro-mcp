# eurodata-mcp

> Structured macroeconomic data for AI agents.

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that gives AI agents clean, semantic access to macroeconomic time series from multiple sources — ECB, BIS, IMF, and FRED.

## The problem

Macroeconomic data is free and public — but:
- Hidden behind cryptic codes like `ICP.M.U2.N.000000.4.INX`
- Fragmented across different APIs and formats (SDMX, JSON-stat, REST)
- Not agent-friendly: no semantic layer, no natural language search

## The solution

A multi-provider system with:
1. **Curated catalog** of ~100-300 essential series per source
2. **Dynamic exploration** of all available data (~300k+ series)
3. **Provider guides** explaining each source to AI agents
4. **Aggregator layer** routing queries to the right provider

## MCP Tools (11 total)

### Catalog tools
| Tool | Description |
|------|-------------|
| `search_series(query)` | Find series by natural language |
| `get_series(id, start, end)` | Fetch time series data |
| `describe_series(id)` | Full metadata for a series |
| `list_categories()` | Browse available topics |

### Exploration tools
| Tool | Description |
|------|-------------|
| `explore_datasets(query)` | List available datasets |
| `explore_dimensions(dataset)` | Show dimensions for a dataset |
| `explore_codes(codelist)` | Valid codes for a dimension |
| `build_series(dataset, dimensions)` | Construct any series dynamically |

### Provider tools
| Tool | Description |
|------|-------------|
| `list_providers()` | Show available data providers |
| `get_provider_guide(provider)` | Get documentation for a provider |
| `find_provider(query)` | Route query to best provider |

## Data providers

| Provider | Coverage | Status |
|----------|----------|--------|
| **ECB** | Euro Area macro (inflation, rates, M3, GDP) | ✅ Complete |
| **BIS** | Global banking, credit, property prices | 🔜 Next |
| **IMF** | World economic indicators, WEO projections | 🔜 Planned |
| **FRED** | US macro (Fed rates, CPI, payrolls, yields) | 🔜 Planned |

## Quick start

```bash
git clone https://github.com/your-org/eurodata-mcp
cd eurodata-mcp
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
      "args": ["run", "--directory", "/path/to/eurodata-mcp", "python", "-m", "eurodata_mcp.server"]
    }
  }
}
```

## Example queries

Once connected, ask Claude:

> "What is the current inflation rate in the Euro Area?"

> "Show me ECB deposit rate evolution since 2022"

> "Compare German and Spanish unemployment rates"

> "Get Euribor 12-month rates for the last 2 years"

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENTS                          │
│         Claude Desktop · Claude Code · AI agents        │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP Protocol
┌──────────────────────▼──────────────────────────────────┐
│                    MCP SERVER                           │
│                 11 tools registered                     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 PROVIDER REGISTRY                       │
│   ECBProvider · BISProvider · IMFProvider · FREDProvider│
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Connectors      Catalog     Metadata Cache
   (API clients)   (curated)   (exploration)
```

## Why this exists

The B2A (Business-to-Agent) market is emerging. AI agents increasingly need structured data to answer questions like:

> *"How has Euro Area inflation evolved since the ECB started hiking rates?"*

> *"Compare US vs Euro Area monetary policy stance"*

No service provides structured macroeconomic data in an agent-friendly format with semantic search across multiple central banks. This is that service.

## Development

```bash
uv sync              # Install dependencies
uv run pytest        # Run tests
uv run python -m eurodata_mcp.server  # Start server
```

See `CLAUDE.md` for development protocols.

## Documentation

- [ROADMAP.md](docs/ROADMAP.md) — Development milestones
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Technical design
- [DATA_SOURCES.md](docs/DATA_SOURCES.md) — API documentation
- [CATALOG_SCHEMA.md](docs/CATALOG_SCHEMA.md) — Series JSON schema

## License

MIT. Underlying data from ECB/BIS/IMF/FRED is public under their respective terms.
