# DATA SOURCES

## 1. ECB — European Central Bank SDMX API

**Base URL:** `https://sdw-wsrest.ecb.europa.eu/service/`

### Fetch series data
```
GET /data/{flowRef}/{key}?startPeriod=YYYY-MM&endPeriod=YYYY-MM&format=jsondata
```

Example — Euro Area HICP inflation:
```
https://sdw-wsrest.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.INX?startPeriod=2020-01&format=jsondata
```

### SDMX key format (for ICP dataset)
```
{FREQ}.{REF_AREA}.{ADJUSTMENT}.{ITEM}.{TRANSFORMATION}.{INDEX_TYPE}
```
- `FREQ`: M=monthly, Q=quarterly, A=annual
- `REF_AREA`: U2=Euro Area, DE, ES, FR, IT...
- `ITEM`: 000000=all items, 010000=food, 040000=housing, 000000XE=core (excl. energy+food)
- `TRANSFORMATION`: 4=annual rate of change, 1=index level

### Curated series — Euro Area MVP catalog

#### Inflation
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_hicp_ea_yoy` | `ICP/M.U2.N.000000.4.INX` | HICP headline, YoY % |
| `ecb_hicp_ea_core_yoy` | `ICP/M.U2.N.000000XE.4.INX` | HICP core (excl. energy & food) |
| `ecb_hicp_ea_energy_yoy` | `ICP/M.U2.N.040000.4.INX` | HICP energy |
| `ecb_hicp_ea_food_yoy` | `ICP/M.U2.N.010000.4.INX` | HICP food |

#### ECB policy rates
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_rate_dfr` | `FM/B.U2.EUR.4F.KR.DFR.LEV` | Deposit Facility Rate |
| `ecb_rate_mro` | `FM/B.U2.EUR.4F.KR.MRO.LEV` | Main Refinancing Operations Rate |
| `ecb_rate_mlf` | `FM/B.U2.EUR.4F.KR.MLFR.LEV` | Marginal Lending Facility Rate |

#### Market rates
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_euribor_3m` | `FM/M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA` | Euribor 3-month |
| `ecb_euribor_12m` | `FM/M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA` | Euribor 12-month |

#### Monetary aggregates
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_m1_ea_yoy` | `BSI/M.U2.Y.V.M10.X.I.U2.2300.Z01.E` | M1, annual growth |
| `ecb_m3_ea_yoy` | `BSI/M.U2.Y.V.M30.X.I.U2.2300.Z01.E` | M3, annual growth |

#### GDP & activity
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_gdp_ea_qoq` | `MNA/Q.Y.I8.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY` | GDP Euro Area, QoQ % |
| `ecb_gdp_ea_yoy` | `MNA/Q.Y.I8.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N12` | GDP Euro Area, YoY % |

#### Labour market
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_unemployment_ea` | `LFSI/M.I8.S.UNEHRT.TOTAL0.15_74.T` | Unemployment rate, Euro Area |

#### Credit
| Internal ID | ECB key | Description |
|---|---|---|
| `ecb_loans_nfc_ea_yoy` | `BSI/M.U2.Y.U.A20.A.I.U2.2240.Z01.E` | Loans to non-financial corporations |
| `ecb_loans_hh_ea_yoy` | `BSI/M.U2.Y.U.A20.A.I.U2.2250.Z01.E` | Loans to households |

### Python fetch example
```python
import httpx

ECB_BASE = "https://sdw-wsrest.ecb.europa.eu/service"

async def fetch_ecb_series(dataset: str, series_key: str, start: str, end: str):
    url = f"{ECB_BASE}/data/{dataset}/{series_key}"
    params = {"startPeriod": start, "endPeriod": end, "format": "jsondata"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
```

### ECB API notes
- No authentication required
- Implicit rate limit: ~1 req/sec is safe
- Response format: SDMX-JSON — parse `dataSets[0].series` and `structure.dimensions`
- Missing values: `null` in JSON
- Most monthly series available from ~1994
- Monthly data published ~3 weeks after period end

---

## 2. Eurostat API (Milestone 2)

**Base URL:** `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/`

```
GET /{dataset_code}?geo={country}&format=JSON&lang=EN
```

Example:
```
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr?geo=ES&format=JSON
```

### Key datasets for M2
| Dataset | Code | Description |
|---|---|---|
| HICP by country | `prc_hicp_manr` | Inflation per country |
| GDP per capita | `nama_10_pc` | GDP per capita |
| Unemployment monthly | `une_rt_m` | Unemployment rate |
| Government debt | `gov_10dd_edpt1` | Debt & deficit (Maastricht) |

### Differences vs ECB
- Better for cross-country comparisons
- Response format: JSON-stat (not SDMX-JSON)
- More frequent revisions
- Broader coverage (EU27+)

---

## 3. INE Spain (Milestone 3)

**Base URL:**
```
https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{series_id}?nult={n}
```

### Key series for M3
| INE ID | Description |
|---|---|
| `IPC251449` | CPI general, Spain |
| `IPC251447` | CPI core, Spain |
| Table `30678` | EPA — Activity/employment/unemployment by CCAA |
| `CNTR4559` | Quarterly GDP, Spain |

### INE notes
- Older, less documented API
- Regional data (CCAA) available for CPI, EPA, GDP
- Some endpoints return only last N observations
- Docs: https://www.ine.es/dyngs/DataLab/manual.html?cid=1259945948443

---

## Source comparison

| | ECB | Eurostat | INE |
|---|---|---|---|
| Geographic scope | Euro Area / ECB | EU27+ | Spain |
| Granularity | Macro aggregates | Country | Country + CCAA |
| API quality | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Auth required | No | No | No |
| Dev priority | M1 ← now | M2 | M3 |
