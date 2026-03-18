# ROADMAP

## Philosophy
Build in layers: first something that works with a real agent (Claude Desktop), then expand sources, then monetize. Each milestone must ship something usable.

**Architecture principle:** Multi-provider system with aggregator layer. Each provider (ECB, BIS, IMF, FRED) follows the same pattern with guide, examples, and aliases. The aggregator routes queries to the appropriate provider(s).

---

## Milestone 1 — ECB Euro Area MVP ✅
**Goal:** Working MCP server with Euro Area data from ECB.
**Status:** COMPLETED

### Completed
- [x] Project setup with uv, pyproject.toml
- [x] Directory structure per CLAUDE.md
- [x] `BaseConnector` ABC with `fetch_series()`, `get_metadata()`, `test_connection()`
- [x] `ECBConnector` with SDMX-JSON parsing and error handling
- [x] Curated catalog with ~25 ECB series
- [x] MCP tools: `search_series`, `get_series`, `describe_series`, `list_categories`
- [x] FastMCP server with stdio mode
- [x] Tested in Claude Desktop

### Dynamic Exploration (Extended)
- [x] Metadata caching (dataflows, structures, codelists)
- [x] Dynamic exploration tools: `explore_datasets`, `explore_dimensions`, `explore_codes`
- [x] `build_series` tool for constructing any ECB series
- [x] Bootstrap script for metadata population

### Provider System
- [x] `BaseProvider` abstract class
- [x] `ProviderRegistry` for managing providers
- [x] `ECBProvider` implementation
- [x] Provider guide system (guide.md, examples.json, aliases.json)
- [x] Provider tools: `list_providers`, `get_provider_guide`, `find_provider`

---

## Milestone 2 — BIS (Bank for International Settlements)
**Goal:** Global banking and credit statistics from BIS.

### Why BIS
- Cross-border banking statistics (locational, consolidated)
- Global credit to households and non-financial corporations
- Property prices
- Debt securities statistics
- Foreign exchange turnover
- Complements ECB with global perspective

### Tasks
- [ ] Research BIS API structure (SDMX-based)
- [ ] `BISConnector(BaseConnector)` implementation
- [ ] `BISProvider(BaseProvider)` with guide, examples, aliases
- [ ] Priority series catalog:
  - Total credit to private sector (% GDP)
  - Cross-border banking claims
  - Property prices (residential, commercial)
  - Debt securities outstanding
- [ ] Integration tests

### API Resources
- BIS Statistics Warehouse: https://stats.bis.org
- BIS API: https://stats.bis.org/api/v1

---

## Milestone 3 — IMF (International Monetary Fund)
**Goal:** Global economic indicators from IMF data.

### Why IMF
- World Economic Outlook (WEO) projections
- International Financial Statistics (IFS)
- Balance of Payments (BOPS)
- Government Finance Statistics (GFS)
- Direction of Trade Statistics (DOTS)
- Global macro coverage that ECB/BIS don't have

### Tasks
- [ ] Research IMF SDMX API
- [ ] `IMFConnector(BaseConnector)` implementation
- [ ] `IMFProvider(BaseProvider)` with guide, examples, aliases
- [ ] Priority series catalog:
  - WEO GDP growth projections (world, major economies)
  - WEO inflation projections
  - Current account balances
  - Government debt to GDP
  - Foreign reserves
- [ ] Integration tests

### API Resources
- IMF Data API: https://datahelp.imf.org/knowledgebase/articles/667681
- IMF SDMX: https://sdmxcentral.imf.org

---

## Milestone 4 — FRED (Federal Reserve St. Louis)
**Goal:** US economic data from FRED.

### Why FRED
- Most comprehensive US economic database
- Fed policy rates
- US labor market (payrolls, unemployment)
- US inflation (CPI, PCE)
- Treasury yields
- Leading indicators
- Essential for US macro coverage

### Tasks
- [ ] Get FRED API key
- [ ] `FREDConnector(BaseConnector)` — REST API (not SDMX)
- [ ] `FREDProvider(BaseProvider)` with guide, examples, aliases
- [ ] Priority series catalog:
  - Federal Funds Rate
  - US CPI, Core CPI
  - PCE, Core PCE (Fed's preferred inflation measure)
  - Non-farm payrolls
  - US unemployment rate
  - 10Y Treasury yield
  - US GDP growth
- [ ] Integration tests

### API Resources
- FRED API: https://fred.stlouisfed.org/docs/api/fred/

---

## Milestone 5 — Aggregator Layer
**Goal:** Unified interface across all providers.

### Features
- [ ] `smart_search(query)` — searches across all providers
- [ ] `smart_fetch(query)` — auto-routes to best provider
- [ ] Query understanding with NLP
- [ ] Cross-provider comparisons (e.g., "compare US vs Euro Area inflation")
- [ ] Provider recommendations based on query

### Architecture
```
User Query: "What is US inflation?"
    ↓
Aggregator: find_provider("US inflation") → FRED
    ↓
FREDProvider.fetch_series("CPIAUCSL")
    ↓
Normalized Response
```

---

## Milestone 6 — Public REST API
**Goal:** Expose the same data via REST for non-MCP clients.

- [ ] FastAPI wrapper over query engine
- [ ] API key authentication
- [ ] Rate limiting
- [ ] OpenAPI documentation
- [ ] Deploy to Railway or Fly.io

---

## Milestone 7 — Product & Distribution
**Goal:** First paying customers.

- [ ] Landing page
- [ ] Pricing: Free tier / Pro tier
- [ ] Publish to MCP server registry
- [ ] Publish to PyPI
- [ ] Outreach to economists, analysts, fintechs

---

## Future Milestones (TBD)

### European National Sources
- Eurostat (EU country-level data)
- INE Spain (Spanish data with regional granularity)
- Destatis (German statistics)
- INSEE (French statistics)

### Additional Global Sources
- World Bank
- OECD
- UN Statistics

---

## Open Technical Decisions

| Decision | Options | Status |
|---|---|---|
| Local storage | SQLite vs DuckDB | SQLite for now |
| Semantic search | TF-IDF vs embeddings | TF-IDF, upgrade if needed |
| Remote MCP | SSE vs stdio | SSE for remote, stdio for local |
| REST auth | API keys vs JWT | API keys to start |
| Provider routing | Keyword matching vs ML | Keyword matching first |

---

## Key Resources

### MCP
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP: https://github.com/jlowin/fastmcp
- MCP Spec: https://spec.modelcontextprotocol.io

### Data APIs
- ECB SDMX: https://data.ecb.europa.eu/help/api/data
- BIS Statistics: https://stats.bis.org/api/v1
- IMF SDMX: https://sdmxcentral.imf.org
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
