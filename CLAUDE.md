# CLAUDE.md — eurodata-mcp

## What this is
An MCP server exposing curated European macroeconomic time series to AI agents. The value is **not** the data (public) — it's the semantic catalog and infrastructure built on top of it.

Maintained by Nico, economist with Banco de España background and deep knowledge of ECB/Eurostat/INE data.

## Current status
**Active milestone: M1 — ECB Euro Area MVP**
See `docs/ROADMAP.md` for full plan.

## Architecture
```
Claude Desktop / Claude Code / AI agents
        ↓  MCP Protocol (stdio)
    MCP Server  (FastMCP)
        ↓
  Query Engine  (Python, async)
     ↓        ↓
ECB SDMX API   SQLite cache + Curated catalog
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
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .mcp.json
├── .claude/
│   ├── settings.json
│   ├── commands/         # Slash commands → /add-series, /test-fetch, /validate-catalog
│   ├── agents/           # Sub-agents → ecb-agent, catalog-agent
│   └── skills/           # Reusable skills → ecb-fetcher
├── src/eurodata_mcp/
│   ├── server.py         # FastMCP entry point
│   ├── tools/            # search_series, get_series, describe_series, list_categories
│   ├── connectors/       # base.py + ecb.py (→ eurostat.py, ine.py later)
│   ├── catalog/          # loader.py + series/ecb_euro_area.json
│   └── cache/            # sqlite.py
└── docs/
    ├── ROADMAP.md
    ├── DATA_SOURCES.md
    └── CATALOG_SCHEMA.md
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
3. **Base class pattern** — new data sources extend `BaseConnector`, never copy-paste
4. **Cache aggressively** — historical data never changes; only refresh recent months
5. **Fail gracefully** — if API is down, serve cached data with staleness warning

## Pending decisions (Nico)
- [ ] Which 25 ECB series enter the MVP catalog → see `docs/CATALOG_SCHEMA.md`
- [ ] SQLite vs DuckDB for local storage
- [ ] Cache TTL strategy for monthly vs daily series
