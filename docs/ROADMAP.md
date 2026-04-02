# ROADMAP

## Philosophy
Build in layers: first something that works with a real agent (Claude Desktop), then expand sources, then monetize. Each milestone must ship something usable.

**Architecture principle:** Multi-provider system. Each provider (ECB, BIS, IMF, FRED) follows the same pattern — guide, examples, aliases, `catalog_dir` pointing to `catalog/{id}/`. Ingestion scripts write there; the MCP server reads from there at runtime.

---

## Milestone 1 — ECB Euro Area ✅
**Goal:** Working MCP server with Euro Area data from ECB.
**Status:** COMPLETE

### Completed
- [x] Project setup with uv, pyproject.toml
- [x] `BaseConnector` ABC with `fetch_series()`, `get_metadata()`, `test_connection()`
- [x] `ECBConnector` with SDMX-JSON parsing and error handling
- [x] Curated catalog — 25 ECB series with bilingual names, tags, series keys
- [x] MCP tools: `search_series`, `get_series`, `describe_series`, `list_categories`
- [x] FastMCP server with stdio mode

### Dynamic exploration
- [x] SDMX structure ingestion — `scripts/ingest_ecb_structures.py`
  - Fetches 100 ECB datasets from SDMX 2.1 API
  - Extracts dimensions (ordered), valid codes, attributes
  - Writes to `catalog/ecb/structures/{ID}.json`
  - Rerun-safe (7-day cache), rate-limited (500ms), resilient
- [x] Semantic enrichment — `scripts/enrich_ecb_catalog.py`
  - Generates plain-English descriptions, analyst concepts, use-case questions
  - Writes to `catalog/ecb/enriched/{ID}.json` + `catalog_enriched.json`
- [x] `explore_datasets(provider_id, query)` — catalog-first, no network
- [x] `explore_dimensions(provider_id, dataset)` — reads inline from structures
- [x] `explore_codes(provider_id, dataset, dimension_id)` — inline codes, filterable
- [x] `build_series(provider_id, dataset, dimensions)` — validates key order, returns data URL

### Provider system
- [x] `BaseProvider` with `catalog_dir`, `get_enriched_catalog()`, `get_dataset_structure()`
- [x] `ProviderRegistry` for managing providers
- [x] `ECBProvider` — `catalog_dir` points to `catalog/ecb/` (repo root, single source of truth)
- [x] Provider guide system (guide.md, examples.json, aliases.json)
- [x] Provider tools: `list_providers`, `get_provider_guide`, `find_provider`

### Two-layer catalog search
- [x] `SeriesEntry` — curated series with instant lookup
- [x] `DatasetEntry` — enriched dataset metadata with scored full-text search
- [x] `search_series` — Layer 1 (curated) + Layer 2 fallback (dataset hints)
- [x] `search_series` filters: `provider`, `frequency`, `geo_coverage`

### Tests
- [x] 110 tests, no network required
- [x] 65 natural-language scenario tests across 12 topics (exchange rates, inflation, interest rates, real estate, BOP, money supply, yield curve, financial stress, surveys, fiscal, catalog discovery)

---

## Milestone 2 — BIS (Bank for International Settlements) 🔜
**Goal:** Global banking and credit statistics from BIS.

### Why BIS
- Cross-border banking statistics (locational, consolidated)
- Global credit to households and non-financial corporations
- Property prices (long history back to 1970s)
- Debt securities statistics
- Foreign exchange turnover
- Complements ECB with global perspective

### Tasks
- [ ] `BISConnector(BaseConnector)` — SDMX API
- [ ] `BISProvider(BaseProvider)` — `catalog_dir` → `catalog/bis/`
- [ ] `scripts/ingest_bis_structures.py`
- [ ] Curated series catalog (`catalog/series/bis_global.json`):
  - Total credit to private sector (% GDP)
  - Credit-to-GDP gap (BIS early warning indicator)
  - Cross-border banking claims
  - Residential property prices (real, long series)
  - Debt securities outstanding
- [ ] Integration tests

### API
- BIS Statistics Warehouse: https://stats.bis.org
- BIS SDMX API: https://stats.bis.org/api/v1

---

## Milestone 3 — IMF (International Monetary Fund) 🔜
**Goal:** Global economic indicators from IMF data.

### Why IMF
- World Economic Outlook (WEO) projections — 195 countries, 2 years ahead
- International Financial Statistics (IFS) — broad macro
- Balance of Payments (BOPS)
- Government Finance Statistics (GFS)
- Direction of Trade Statistics (DOTS)

### Tasks
- [ ] `IMFConnector(BaseConnector)` — SDMX + DataMapper JSON
- [ ] `IMFProvider(BaseProvider)` — `catalog_dir` → `catalog/imf/`
- [ ] `scripts/ingest_imf_structures.py`
- [ ] Curated series catalog (`catalog/series/imf_global.json`):
  - WEO GDP growth projections (world, major economies)
  - WEO inflation projections
  - Current account balances (% GDP)
  - Government debt to GDP
  - Foreign reserves (months of imports)
- [ ] Integration tests

### API
- IMF SDMX: https://sdmxcentral.imf.org
- IMF DataMapper: https://www.imf.org/external/datamapper/api/v1/

---

## Milestone 4 — FRED (Federal Reserve St. Louis) 🔜
**Goal:** US economic data from FRED.

### Why FRED
- Most comprehensive US economic database (100k+ series)
- Fed policy rates
- US labor market (payrolls, unemployment)
- US inflation (CPI, PCE — the Fed's preferred measure)
- Treasury yields
- Essential for US vs Euro Area comparisons

### Tasks
- [ ] `FREDConnector(BaseConnector)` — REST JSON (not SDMX)
- [ ] `FREDProvider(BaseProvider)` — `catalog_dir` → `catalog/fred/`
- [ ] Curated series catalog (`catalog/series/fred_us.json`):
  - Federal Funds Rate (FEDFUNDS)
  - US CPI, Core CPI (CPIAUCSL, CPILFESL)
  - PCE, Core PCE (PCEPI, PCEPILFE)
  - Non-farm payrolls (PAYEMS)
  - US unemployment rate (UNRATE)
  - 10Y Treasury yield (DGS10)
  - US GDP growth (GDP)
- [ ] Integration tests

### API
- FRED API: https://fred.stlouisfed.org/docs/api/fred/ (free API key required)

---

## Milestone 5 — OECD (Organisation for Economic Co-operation and Development) 🔜
**Goal:** Cross-country comparable economic data from OECD.

### Why OECD
- 38 member countries with standardized, comparable indicators
- Economic Outlook projections (forward-looking forecasts)
- Composite Leading Indicators (CLI) — early warning system
- Long time series back to 1960s for many indicators
- Quality metadata with detailed methodological notes
- SDMX standard (same as ECB!) — reuses existing infrastructure

### Tasks
- [ ] `OECDConnector(BaseConnector)` — SDMX API (v1 and v2)
- [ ] `OECDProvider(BaseProvider)` — `catalog_dir` → `catalog/oecd/`
- [ ] `scripts/ingest_oecd_structures.py`
- [ ] Handle OECD-specific quirks:
  - Hierarchical agency IDs (`OECD.ENV.EPI`, `OECD.ELS.SPD`)
  - Dataflow IDs with `@` symbol (`DSD_ECH@EXT_DROUGHT`)
  - Rate limiting: 60 requests/hour
- [ ] Curated series catalog (`catalog/series/oecd_global.json`):
  - Real GDP growth (QNA)
  - Unemployment rate (MEI_CLI)
  - CPI inflation (PRICES_CPI)
  - Current account % GDP (MEI_BOP6)
  - Government debt % GDP (GOV_DEBT)
  - Composite Leading Indicators (MEI_CLI)
  - Real house prices (HOUSE_PRICES)
  - Labour productivity (PDB_LV)
- [ ] Integration tests

### API
- OECD SDMX API: https://sdmx.oecd.org/public/rest/
- Data Explorer: https://data-explorer.oecd.org/
- API Documentation: See `docs/OECD_DEVELOPMENT.md`

### Rate Limiting Strategy
- 60 data downloads/hour limit
- Use `contentconstraint` query to check last update before re-fetching
- Implement aggressive caching (most datasets update 1-2x/year)
- Batch requests with 60s sleep between batches during ingestion

---

## Milestone 6 — Cross-provider aggregator
**Goal:** Unified query interface across all providers.

### Features
- [ ] `smart_search(query)` — searches across all providers simultaneously
- [ ] `smart_fetch(query)` — auto-routes to best provider
- [ ] Cross-provider comparisons ("compare US vs Euro Area inflation")
- [ ] Provider recommendations in `search_series` results

---

## Milestone 7 — Public REST API
**Goal:** Expose the same data via REST for non-MCP clients.

- [ ] FastAPI wrapper over query engine
- [ ] API key authentication
- [ ] Rate limiting
- [ ] OpenAPI documentation
- [ ] Deploy to Railway or Fly.io

---

## Milestone 8 — Product & Distribution
**Goal:** First paying customers.

- [ ] Landing page
- [ ] Pricing: Free tier / Pro tier
- [ ] Publish to MCP server registry
- [ ] Publish to PyPI
- [ ] Outreach to economists, analysts, fintechs

---

## Future Milestones (TBD)

### European national sources
- Eurostat (EU country-level data, large coverage)
- INE Spain (Spanish data with regional granularity)
- Destatis (German statistics)
- INSEE (French statistics)

### Additional global sources
- World Bank (development indicators)
- UN Statistics (SDG indicators)

---

## Open Technical Decisions

| Decision | Current | Future option |
|---|---|---|
| Local storage | SQLite (diskcache) | DuckDB for analytics |
| Catalog search | Scored keyword matching | Embeddings / BM25 |
| Remote MCP | stdio (local only) | SSE for remote hosting |
| REST auth | N/A | API keys |
| Provider routing | Keyword matching | ML classifier |
| Catalog enrichment | LLM (one-off script) | Auto-refresh on new datasets |

---

## Key Resources

### MCP
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP: https://github.com/jlowin/fastmcp
- MCP Spec: https://spec.modelcontextprotocol.io

### Data APIs
- ECB SDMX: https://data-api.ecb.europa.eu/service
- BIS Statistics: https://stats.bis.org/api/v1
- IMF SDMX: https://sdmxcentral.imf.org
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
- OECD SDMX: https://sdmx.oecd.org/public/rest/
