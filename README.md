# eurodata-mcp

> Structured European macroeconomic data for AI agents.

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that gives AI agents clean, semantic access to European macro time series — starting with ECB data for the Euro Area.

## The problem

European statistical data (ECB, Eurostat, INE) is free and public — but:
- Hidden behind cryptic codes like `ICP.M.U2.N.000000.4.INX`
- Fragmented across different APIs and formats
- Not agent-friendly: no semantic layer, no natural language search

## The solution

A curated catalog maintained by domain experts (economists), turning:

```
ICP.M.U2.N.000000.4.INX
```
into:
```json
{
  "id": "ecb_hicp_ea_yoy",
  "name": "HICP Inflation Rate, Euro Area (YoY %)",
  "frequency": "monthly",
  "latest_value": 2.3,
  "unit": "% year-on-year"
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_series(query)` | Find series by natural language |
| `get_series(id, start, end)` | Fetch time series data |
| `describe_series(id)` | Full metadata for a series |
| `list_categories(topic)` | Browse available topics |

## Data sources

| Source | Coverage | Status |
|--------|----------|--------|
| ECB SDMX API | Euro Area macro aggregates | ✅ M1 — active |
| Eurostat | EU27 country-level data | 🔜 M2 |
| INE Spain | Spain + regional data | 🔜 M3 |

## Quick start

```bash
git clone https://github.com/your-username/eurodata-mcp
cd eurodata-mcp
uv sync
uv run python -m eurodata_mcp.server
```

See `CLAUDE.md` for Claude Desktop integration.

## Why this exists

The B2A (Business-to-Agent) market is emerging. AI agents increasingly need structured data to answer questions like:

> *"How has Euro Area inflation evolved since the ECB started hiking rates?"*
> *"Compare Spanish GDP growth vs the Euro Area average over the last 5 years."*

No service provides structured European macroeconomic data in an agent-friendly format. This is that service.

## License

MIT. Underlying data from ECB/Eurostat/INE is public under their respective terms.
