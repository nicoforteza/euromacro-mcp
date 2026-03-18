# DATA SOURCES

This document covers the APIs for each data provider in the eurodata-mcp roadmap.

## Provider roadmap

| Priority | Provider | API Type | Status |
|----------|----------|----------|--------|
| M1 | ECB | SDMX | ✅ Complete |
| M2 | BIS | SDMX | 🔜 Next |
| M3 | IMF | SDMX | 🔜 Planned |
| M4 | FRED | REST JSON | 🔜 Planned |

---

## 1. ECB — European Central Bank ✅

**Status:** Complete (Milestone 1)

**Base URL:** `https://data.ecb.europa.eu/data-api/v1/`

### Endpoints

#### Data (SDMX-JSON)
```
GET /data/{flowRef}/{key}?startPeriod=YYYY-MM&endPeriod=YYYY-MM&format=jsondata
```

Example — Euro Area HICP inflation:
```
https://data.ecb.europa.eu/data-api/v1/data/ICP/M.U2.N.000000.4.INX?startPeriod=2020-01&format=jsondata
```

#### Structure (SDMX-XML)
```
GET /data-structure/{structure_id}
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

#### Codelists (SDMX-XML)
```
GET /codelist/{codelist_id}
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

### Key datasets

| Dataset | Code | Description |
|---------|------|-------------|
| Inflation | `ICP` | HICP price indices |
| Financial markets | `FM` | Interest rates, Euribor |
| Balance sheet items | `BSI` | Monetary aggregates, credit |
| National accounts | `MNA` | GDP, components |
| Labour force | `LFSI` | Unemployment, employment |
| Exchange rates | `EXR` | EUR vs other currencies |

### Series key format
```
{FREQ}.{REF_AREA}.{ADJUSTMENT}.{ITEM}.{UNIT}.{SUFFIX}
```

### API notes
- No authentication required
- Data endpoint: JSON, Structure endpoints: XML only
- Rate limit: ~1 req/sec is safe
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
| Credit to private sector | `TOTAL_CREDIT` | Credit to households and NFCs |
| Property prices | `LONG_PP` | Residential and commercial |
| Debt securities | `SEC_ALL` | Outstanding and issuance |
| Locational banking | `LBS` | Cross-border banking |
| Consolidated banking | `CBS` | Banking claims by nationality |
| Effective exchange rates | `EER` | Nominal and real |
| Consumer prices | `CPI` | Inflation (long history) |

### Priority series for M2

| Series | Description |
|--------|-------------|
| Credit-to-GDP gap | Early warning indicator |
| Total credit to private sector | % of GDP |
| House prices | Real, long series |
| Cross-border claims | On banks and non-banks |

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
- JSON: `https://www.imf.org/external/datamapper/api/v1/`

### Key datasets

| Dataset | Code | Description |
|---------|------|-------------|
| World Economic Outlook | `WEO` | GDP, inflation projections |
| International Financial Statistics | `IFS` | Broad macro indicators |
| Balance of Payments | `BOP` | External accounts |
| Government Finance Statistics | `GFS` | Fiscal data |
| Direction of Trade | `DOT` | Bilateral trade |

### Priority series for M3

| Series | Description |
|--------|-------------|
| WEO GDP growth | Projections for 195 countries |
| WEO inflation | CPI projections |
| Current account | % of GDP |
| Government debt | % of GDP |
| Foreign reserves | Months of imports |

### Endpoints

#### Data (SDMX)
```
GET /data/{flowRef}/{key}
Accept: application/vnd.sdmx.data+json
```

#### DataMapper (simpler JSON)
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
GET /series/observations?series_id={id}&api_key={key}&file_type=json
```

#### Series search
```
GET /series/search?search_text={query}&api_key={key}&file_type=json
```

#### Series info
```
GET /series?series_id={id}&api_key={key}&file_type=json
```

### Key series for M4

| Series ID | Description |
|-----------|-------------|
| `FEDFUNDS` | Federal Funds Rate |
| `DFF` | Fed Funds Daily |
| `CPIAUCSL` | CPI All Urban Consumers |
| `CPILFESL` | Core CPI (ex food & energy) |
| `PCEPI` | PCE Price Index |
| `PCEPILFE` | Core PCE |
| `PAYEMS` | Non-farm payrolls |
| `UNRATE` | Unemployment rate |
| `GDP` | Gross Domestic Product |
| `DGS10` | 10-Year Treasury |
| `DGS2` | 2-Year Treasury |
| `T10Y2Y` | 10Y-2Y spread |

### API notes
- API key required (free)
- 120 requests per minute limit
- 100,000+ series available
- Daily updates for market data
- Weekly/monthly for economic indicators

### Python example
```python
import httpx

FRED_API_KEY = "your_key_here"
FRED_BASE = "https://api.stlouisfed.org/fred"

async def fetch_fred_series(series_id: str, start: str, end: str):
    url = f"{FRED_BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
```

---

## Provider comparison

| | ECB | BIS | IMF | FRED |
|---|---|---|---|---|
| Geographic scope | Euro Area | Global | Global | USA |
| Granularity | Macro aggregates | Global aggregates | Country-level | US detailed |
| API type | SDMX | SDMX | SDMX + JSON | REST JSON |
| Auth required | No | No | No | Yes (free) |
| Rate limit | ~1/sec | Unknown | Unknown | 120/min |
| Update frequency | Monthly | Quarterly | Monthly | Daily-Monthly |
| Historical depth | ~1994 | ~1940s | ~1948 | ~1776 |

---

## Future providers (not in current roadmap)

### European national sources
- **Eurostat** — EU27 country-level data
- **INE Spain** — Spanish data with CCAA granularity
- **Destatis** — German statistics
- **INSEE** — French statistics

### Global sources
- **World Bank** — Development indicators
- **OECD** — Economic outlook, leading indicators
- **UN Statistics** — SDG indicators
