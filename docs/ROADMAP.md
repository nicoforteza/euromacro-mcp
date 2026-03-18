# ROADMAP

## Philosophy
Build in layers: first something that works with a real agent (Claude Desktop), then expand sources, then monetize. Each milestone must ship something usable.

---

## Milestone 1 — ECB Euro Area MVP
**Goal:** Working MCP server with Euro Area data from ECB.
**Estimate:** 1–2 weeks

### Project setup
- [ ] `uv init`, `pyproject.toml` with deps: `fastmcp`, `httpx`, `pandas`, `diskcache`
- [ ] Directory structure per `CLAUDE.md`
- [ ] `.env.example`, `.gitignore`
- [ ] GitHub Actions: lint + tests

### ECB connector
- [ ] `BaseConnector` ABC: `fetch_series()`, `get_metadata()`, `test_connection()`
- [ ] `ECBConnector(BaseConnector)`:
  - [ ] Parse SDMX-JSON response
  - [ ] Normalize to DataFrame (date, value, series_id)
  - [ ] Error handling (HTTP 429, 503, timeout)
  - [ ] Tests with fixtures (no real API calls in CI)

### Cache
- [ ] `SQLiteCache` with configurable TTL
- [ ] Cache key: `(source, series_key, start_date, end_date)`
- [ ] `invalidate_recent()` for last-month data

### Catalog (Nico defines the series)
- [ ] Select ~25 priority ECB series covering:
  - Inflation (HICP headline, core, energy, food)
  - GDP Euro Area (levels, growth rates)
  - ECB policy rates (DFR, MRO, MLF)
  - Monetary aggregates (M1, M2, M3)
  - Credit to households and NFC
  - Unemployment rate
  - Business / consumer confidence
- [ ] `src/eurodata_mcp/catalog/series/ecb_euro_area.json`

### MCP Tools
- [ ] `search_series(query)` — text search over name, description, tags; return top 10
- [ ] `get_series(id, start, end)` — fetch from API or cache; return `{date, value}[]`
- [ ] `describe_series(id)` — full metadata + latest observation
- [ ] `list_categories()` — available categories with series count

### MCP Server
- [ ] `server.py` with FastMCP, register all 4 tools
- [ ] stdio mode (Claude Desktop + Claude Code compatible)
- [ ] Structured logging

### End-to-end test
- [ ] Install in Claude Desktop locally
- [ ] Verify: *"What is the current inflation rate in the Euro Area?"*
- [ ] Verify: *"Show me ECB deposit rate evolution since 2022"*

---

## Milestone 2 — Eurostat (EU countries)
**Goal:** Country-level data from Eurostat.
**Estimate:** 1 week

- [ ] `EurostatConnector(BaseConnector)` — different API than ECB
- [ ] `eurostat_countries.json` catalog: ES, DE, FR, IT, PT
- [ ] Extend `search_series` to filter by country
- [ ] New tool: `compare_countries(series_id, countries, start, end)`

---

## Milestone 3 — INE Spain
**Goal:** Spanish data with regional granularity (CCAA).
**Estimate:** 1 week

- [ ] `INEConnector(BaseConnector)` — JSON-stat API
- [ ] `ine_spain.json` catalog: CPI regional, EPA, GDP by CCAA
- [ ] New tool: `get_regional_data(series_id, region)`

---

## Milestone 4 — Public REST API
**Goal:** Expose the same data via REST for non-MCP clients.
**Estimate:** 1–2 weeks

- [ ] FastAPI on top of the same query engine
- [ ] API key authentication
- [ ] Rate limiting
- [ ] Auto OpenAPI docs
- [ ] Deploy: Railway or Fly.io

---

## Milestone 5 — Product & distribution
**Goal:** First paying customers.

- [ ] Landing page
- [ ] Pricing: Free (1-day delay) / Pro ($X/month, real-time + more series)
- [ ] Publish to [MCP server registry](https://github.com/modelcontextprotocol/servers)
- [ ] Publish to PyPI as installable package
- [ ] Outreach: economists/analysts using Claude Pro, European fintechs, bank research teams

---

## Open technical decisions

| Decision | Options | Status |
|---|---|---|
| Local storage | SQLite vs DuckDB | Open — DuckDB better for analytical queries |
| Semantic search | TF-IDF vs embeddings | Start with TF-IDF, upgrade if needed |
| Remote MCP | SSE vs stdio | SSE for remote, stdio for local |
| REST auth | Simple API keys vs JWT | API keys to start |

---

## Key resources

### MCP
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP: https://github.com/jlowin/fastmcp
- MCP Spec: https://spec.modelcontextprotocol.io
- Reference servers: https://github.com/modelcontextprotocol/servers

### Data APIs
- ECB SDMX: https://data.ecb.europa.eu/help/api/data
- ECB Data Portal: https://data.ecb.europa.eu
- Eurostat API: https://wikis.ec.europa.eu/display/EUROSTATHELP/API+Statistics+-+data+query
- INE API: https://www.ine.es/dyngs/DataLab/manual.html?cid=1259945948443

### Reference projects
- financialdatasets.ai MCP: https://github.com/virattt/financial-datasets-mcp
- ECB Python wrapper (unofficial): https://github.com/ecb-sdw/ecbdata
