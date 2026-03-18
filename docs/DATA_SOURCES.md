# DATA SOURCES

APIs for each data provider in the eurodata-mcp roadmap.

## Provider roadmap

| Priority | Provider | API Type | Status |
|----------|----------|----------|--------|
| M1 | ECB | SDMX 2.1 | ✅ Complete |
| M2 | BIS | SDMX | 🔜 Next |
| M3 | IMF | SDMX + JSON | 🔜 Planned |
| M4 | FRED | REST JSON | 🔜 Planned |

---

## 1. ECB — European Central Bank ✅

**Status:** Complete (Milestone 1) — 100 datasets ingested, enriched, and wired into MCP tools.

**Base URL:** `https://data-api.ecb.europa.eu/service`

### Endpoints used

#### Data (SDMX-JSON)
```
GET /data/{DATASET_ID}/{SERIES_KEY}?format=jsondata&startPeriod=YYYY-MM&endPeriod=YYYY-MM
```

Example — Euro Area HICP inflation:
```
https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.INX?format=jsondata&startPeriod=2020-01
```

#### Dataflow list (used by ingestion script)
```
GET /dataflow/ECB/{DATASET_ID}
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

#### Structure with codelists (used by ingestion script)
```
GET /datastructure/ECB/{DATASET_ID}?references=all&detail=full
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

The `references=all` parameter inlines all codelists and concept schemes in a single response — no follow-up requests needed.

### Key datasets (100 total — see `catalog/ecb/catalog_enriched.json`)

| Dataset | Code | Description |
|---------|------|-------------|
| Inflation (HICP) | `ICP` / `HICP` | Harmonised Index of Consumer Prices |
| Financial Markets | `FM` | Interest rates, Euribor, monetary policy rates |
| Balance Sheet Items | `BSI` | Monetary aggregates M1/M2/M3, credit |
| Exchange Rates | `EXR` | EUR vs other currencies — 369 currencies |
| MFI Interest Rates | `MIR` | Bank lending and deposit rates |
| Bank Lending Survey | `BLS` | Qualitative credit conditions |
| Balance of Payments | `BOP` | Current account, financial account |
| €STR | `EST` | Euro Short-Term Rate (overnight) |
| Yield Curve | `YC` | AAA-rated euro area government bonds |
| CISS | `CISS` | Composite Indicator of Systemic Stress |
| Public Debt Dynamics | `PDD` | Government debt, deficit, financing |
| Residential Property | `RPP` | Residential property prices |

### Series key format

Each dataset has its own dimension order. Always use `explore_dimensions(provider_id="ecb", dataset="{ID}")` to get the correct format. Example for EXR:

```
<FREQ>.<CURRENCY>.<CURRENCY_DENOM>.<EXR_TYPE>.<EXR_SUFFIX>
M     .USD      .EUR             .SP00      .A
```

### API notes
- No authentication required
- Data endpoint: JSON (`format=jsondata`)
- Structure endpoints: XML only (SDMX 2.1)
- Rate limit: ~1 req/sec recommended (ingestion script uses 500ms delay)
- Monthly data published ~3 weeks after period end

---

## 2. BIS — Bank for International Settlements 🔜

**Status:** Next milestone (M2)

**Base URL:** `https://stats.bis.org/api/v1/`

### Endpoints

#### Data
```
GET /data/{flowRef}/{key}?startPeriod=YYYY&endPeriod=YYYY
Accept: application/vnd.sdmx.data+json;version=1.0.0
```

#### Dataflow list
```
GET /dataflow/BIS
Accept: application/vnd.sdmx.structure+json;version=1.0.0
```

### Key datasets

| Dataset | Code | Description |
|---------|------|-------------|
| Credit to private sector | `TOTAL_CREDIT` | Households + non-financial corporations |
| Property prices | `LONG_PP` | Residential and commercial (back to 1970s) |
| Debt securities | `SEC_ALL` | Outstanding and issuance |
| Locational banking | `LBS` | Cross-border banking claims |
| Consolidated banking | `CBS` | Banking claims by nationality |
| Effective exchange rates | `EER` | Nominal and real |
| Consumer prices | `CPI` | Inflation (long history) |

### Priority series for M2

| Series | Description |
|--------|-------------|
| Credit-to-GDP gap | BIS early warning indicator for financial crises |
| Total credit to private sector | % of GDP, all countries |
| Residential property prices | Real prices, long history |
| Cross-border banking claims | Locational and consolidated |

### API notes
- No authentication required
- SDMX-JSON and SDMX-XML supported
- Quarterly and annual data primarily
- Some series go back to 1940s

---

## 3. IMF — International Monetary Fund 🔜

**Status:** Planned (M3)

**Base URLs:**
- SDMX: `https://sdmxcentral.imf.org/ws/public/sdmxapi/rest/`
- DataMapper: `https://www.imf.org/external/datamapper/api/v1/`

### Key datasets

| Dataset | Code | Description |
|---------|------|-------------|
| World Economic Outlook | `WEO` | GDP, inflation projections — 195 countries |
| International Financial Statistics | `IFS` | Broad macro indicators |
| Balance of Payments | `BOP` | External accounts |
| Government Finance Statistics | `GFS` | Fiscal data |
| Direction of Trade | `DOT` | Bilateral trade flows |

### Priority series for M3

| Series | Description |
|--------|-------------|
| WEO GDP growth | Projections for 195 countries, 2 years ahead |
| WEO inflation | CPI projections |
| Current account | % of GDP |
| Government debt | % of GDP |
| Foreign reserves | Months of imports |

### Endpoints

#### SDMX data
```
GET /data/{flowRef}/{key}
Accept: application/vnd.sdmx.data+json
```

#### DataMapper (simpler, JSON)
```
GET /{indicator}?periods={year}
```

### API notes
- No authentication required
- WEO updated twice yearly (April, October)
- IFS updated monthly
- Coverage: 195 countries

---

## 4. FRED — Federal Reserve St. Louis 🔜

**Status:** Planned (M4)

**Base URL:** `https://api.stlouisfed.org/fred/`

### Authentication
**API key required** — Free registration at https://fred.stlouisfed.org/docs/api/api_key.html

### Endpoints

#### Series observations
```
GET /series/observations?series_id={id}&api_key={key}&file_type=json&observation_start={YYYY-MM-DD}&observation_end={YYYY-MM-DD}
```

#### Series info
```
GET /series?series_id={id}&api_key={key}&file_type=json
```

### Key series for M4

| Series ID | Description |
|-----------|-------------|
| `FEDFUNDS` | Federal Funds Rate (monthly average) |
| `DFF` | Fed Funds Rate (daily) |
| `CPIAUCSL` | CPI — All Urban Consumers |
| `CPILFESL` | Core CPI (ex food & energy) |
| `PCEPI` | PCE Price Index |
| `PCEPILFE` | Core PCE (Fed's preferred inflation measure) |
| `PAYEMS` | Non-farm payrolls |
| `UNRATE` | Unemployment rate |
| `GDP` | Gross Domestic Product |
| `DGS10` | 10-Year Treasury yield |
| `DGS2` | 2-Year Treasury yield |
| `T10Y2Y` | 10Y-2Y spread (yield curve) |

### API notes
- API key required (free)
- 120 requests per minute limit
- 100,000+ series available
- Daily updates for market data; weekly/monthly for economic indicators

---

## Provider comparison

| | ECB | BIS | IMF | FRED |
|---|---|---|---|---|
| Geographic scope | Euro Area | Global | Global (195 countries) | USA |
| Number of datasets | 100 | ~15 | ~10 | 100k+ series |
| API type | SDMX 2.1 | SDMX | SDMX + JSON | REST JSON |
| Auth required | No | No | No | Yes (free key) |
| Rate limit | ~1/sec | Unknown | Unknown | 120/min |
| Update frequency | Monthly | Quarterly | Monthly/biannual | Daily–Monthly |
| Historical depth | ~1994 | ~1940s | ~1948 | ~1776 |
| Status | ✅ Complete | 🔜 Next | 🔜 Planned | 🔜 Planned |

---

## Future providers (beyond current roadmap)

### European national sources
- **Eurostat** — EU27 country-level data, large coverage
- **INE Spain** — Spanish data with CCAA (autonomous community) granularity
- **Destatis** — German Federal Statistics Office
- **INSEE** — French national statistics

### Global sources
- **World Bank** — Development indicators (WDI)
- **OECD** — Economic outlook, leading indicators (MEI)
- **UN Statistics** — SDG indicators
