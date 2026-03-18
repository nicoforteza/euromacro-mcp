# ECB Data Guide

## Overview

The **European Central Bank (ECB)** publishes macroeconomic statistics for the Euro Area through its Statistical Data Warehouse (SDW). This is the primary source for Euro Area monetary policy, inflation, interest rates, exchange rates, banking data, and economic activity.

**100 datasets available. 300,000+ series.**

---

## Key Concepts

### Dataset (Dataflow)
A **dataset** is a collection of thematically related series. Each has a short code (e.g. `EXR`, `ICP`, `BSI`).

| Dataset | Code | What it contains |
|---------|------|-----------------|
| Exchange Rates | **EXR** | EUR vs 369 currencies — daily, monthly, quarterly |
| Inflation (HICP) | **ICP** / **HICP** | Harmonised consumer prices by country and item |
| Financial Markets | **FM** | ECB policy rates, Euribor, money market rates |
| Balance Sheet Items | **BSI** | M1, M2, M3 aggregates, credit to private sector |
| MFI Interest Rates | **MIR** | Bank lending and deposit rates by country |
| Bank Lending Survey | **BLS** | Qualitative credit conditions (quarterly) |
| Balance of Payments | **BOP** | Current account, financial account |
| Euro Short-Term Rate | **EST** | €STR overnight rate (replaces EONIA) |
| Yield Curve | **YC** | AAA-rated euro area government bonds |
| National Accounts | **MNA** | GDP, components (data in AME dataset too) |
| Labour Force | **LFSI** | Unemployment, employment |
| Residential Property | **RPP** | House prices by country |
| CISS | **CISS** | Composite Indicator of Systemic Stress |
| SPF | **SPF** | Survey of Professional Forecasters |
| SAFE | **SAFE** | Survey on Access to Finance of Enterprises |

### Series Key
Each series has a unique **series key** — dimension values separated by dots. The order of dimensions is fixed per dataset.

Example for `ICP` (inflation):
```
M    .U2      .N          .000000   .4              .INX
│     │        │           │         │               │
FREQ  REF_AREA ADJUSTMENT  ICP_ITEM  STS_INSTITUTION ICP_SUFFIX
Month Euro Area No adjust.  All items ECB             Index
```

### Common Dimensions

| Dimension | Description | Common values |
|-----------|-------------|---------------|
| **FREQ** | Temporal frequency | A=Annual, Q=Quarterly, M=Monthly, D=Daily, B=Business day |
| **REF_AREA** | Geographic area | U2=Euro Area, DE=Germany, ES=Spain, FR=France, IT=Italy |
| **ADJUSTMENT** | Seasonal adjustment | N=Not adjusted, Y=Adjusted, S=SWDA |

### Country codes (REF_AREA)

| Code | Country |
|------|---------|
| U2 / I8 | Euro Area aggregate |
| DE | Germany |
| ES | Spain |
| FR | France |
| IT | Italy |
| NL | Netherlands |
| BE | Belgium |
| AT | Austria |
| PT | Portugal |
| IE | Ireland |
| GR | Greece |
| FI | Finland |

---

## Most Requested Data

### 1. Inflation (HICP)
- **Dataset**: `ICP` or `HICP`
- **Euro Area headline**: `M.U2.N.000000.4.INX`
- **Core (ex energy & food)**: `M.U2.N.XEF000.4.INX`
- **By country**: replace U2 with country code (e.g. `M.DE.N.000000.4.INX` for Germany)

### 2. ECB Policy Rates
- **Dataset**: `FM`
- **Deposit Facility Rate (DFR)**: `B.U2.EUR.4F.KR.DFR.LEV` — main rate since 2022 hiking cycle
- **Main Refinancing Operations (MRO)**: `B.U2.EUR.4F.KR.MRO.LEV`
- **Marginal Lending Facility**: `B.U2.EUR.4F.KR.MLFR.LEV`

### 3. Euribor
- **Dataset**: `FM`
- **3-month**: `M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA`
- **12-month**: `M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`

### 4. €STR (Euro Short-Term Rate)
- **Dataset**: `EST`
- Daily overnight rate, replacing EONIA since 2022

### 5. Money Supply (M3)
- **Dataset**: `BSI`
- **M3 Euro Area**: `M.U2.Y.V.M30.X.I.U2.2300.Z01.E`
- **M1 Euro Area**: `M.U2.Y.V.M10.X.I.U2.2300.Z01.E`

### 6. EUR/USD Exchange Rate
- **Dataset**: `EXR`
- **Monthly**: `M.USD.EUR.SP00.A`
- **Daily**: `D.USD.EUR.SP00.A`

### 7. Unemployment
- **Dataset**: `LFSI`
- **Euro Area total**: `M.I8.S.UNEHRT.TOTAL0.15_74.T`

---

## How to Use the Tools

### Step 1 — Discover datasets
```
explore_datasets(provider_id="ecb", query="inflation")
→ Returns ICP, HICP, and related datasets with descriptions
```

### Step 2 — Explore dimensions
```
explore_dimensions(provider_id="ecb", dataset="EXR")
→ Returns: <FREQ>.<CURRENCY>.<CURRENCY_DENOM>.<EXR_TYPE>.<EXR_SUFFIX>
→ Shows dimension names and code counts
```

### Step 3 — Find valid codes
```
explore_codes(provider_id="ecb", dataset="EXR", dimension_id="CURRENCY", query="swiss")
→ Returns: CHF = Swiss franc
```

### Step 4 — Build the series key and URL
```
build_series(
    provider_id="ecb",
    dataset="EXR",
    dimensions={
        "FREQ": "M",
        "CURRENCY": "USD",
        "CURRENCY_DENOM": "EUR",
        "EXR_TYPE": "SP00",
        "EXR_SUFFIX": "A"
    }
)
→ series_key: "M.USD.EUR.SP00.A"
→ data_url: "https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?format=jsondata"
```

### Step 5 — Fetch data
```
get_series("ecb_hicp_ea_yoy")                    # from curated catalog
get_series("ecb:EXR:M.USD.EUR.SP00.A")           # direct series key
```

### Shortcut — Curated catalog
For common series, skip Steps 1–4 entirely:
```
search_series("euro area inflation")
→ Returns ecb_hicp_ea_yoy with ready-to-use series key
```

---

## Tips

1. **Curated series first**: For common macro questions, `search_series()` and `get_series()` use the curated catalog with simple IDs like `ecb_hicp_ea_yoy` — no need to build keys manually.

2. **Wildcards**: In `build_series`, omit a dimension (empty string) to get all values for that position. Useful for fetching all countries at once.

3. **Frequencies**: Most macro data is monthly (M) or quarterly (Q). ECB policy rates are daily (B/D) but have monthly aggregates.

4. **Seasonal adjustment**: Use `N` (not adjusted) for official unadjusted data, `Y` or `S` for seasonally adjusted.

5. **Data lags**: Inflation ~3 weeks after period end, GDP ~45 days, BOP ~3 months.

6. **Euro Area codes**: `U2` is the standard Euro Area aggregate code in most datasets. Some datasets use `I8` (same area, different vintage).

---

## Useful Links
- Data portal: https://data.ecb.europa.eu
- API documentation: https://data.ecb.europa.eu/help/api/data
- Series explorer: https://data.ecb.europa.eu/data/datasets
- SDMX 2.1 spec: https://sdmx.org/?page_id=5008
