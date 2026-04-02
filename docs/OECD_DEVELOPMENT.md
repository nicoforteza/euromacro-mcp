# OECD MCP Provider Development Guide

## Overview

The OECD (Organisation for Economic Co-operation and Development) provides macroeconomic data for OECD member countries and selected non-member economies through a RESTful SDMX API.

**Good news**: OECD uses SDMX standard (same as ECB!), so we can reuse significant infrastructure.

---

## API Technical Specifications

### Base URLs

| Version | Endpoint |
|---------|----------|
| SDMX v1 | `https://sdmx.oecd.org/public/rest/` |
| SDMX v2 | `https://sdmx.oecd.org/public/rest/v2/` |
| Legacy (deprecated) | `https://stats.oecd.org/SDMX-JSON/` |

### Authentication
- **None required** (anonymous access)
- Free of charge (subject to OECD Terms and Conditions)

### Rate Limits
- **60 data downloads per hour**
- VPN/anonymized traffic not allowed
- Max 1,000,000 observations per response
- Max URL length: 1,000 characters

### Supported Formats
- SDMX-JSON v1 and v2
- SDMX-ML v2.1 and v3 (experimental)
- SDMX-CSV v1 and v2
- Use `Accept` header or `format` URL parameter

---

## Query Syntax

### Data Queries

**SDMX API v1:**
```
https://sdmx.oecd.org/public/rest/data/{agency},{dataflow},{version}/{filter}[?params]
```

**SDMX API v2:**
```
https://sdmx.oecd.org/public/rest/v2/data/dataflow/{agency}/{dataflow}/{version}/{filter}[?params]
```

### Structure Queries

**SDMX API v1:**
```
https://sdmx.oecd.org/public/rest/dataflow/{agency}/{dataflow}/{version}?references=all&detail=referencepartial
```

**SDMX API v2:**
```
https://sdmx.oecd.org/public/rest/v2/structure/dataflow/{agency}/{dataflow}/{version}?references=all&detail=referencepartial
```

### Filter Expression

**v1 syntax:**
- Dimensions separated by `.`
- Multiple values per dimension separated by `+`
- Empty = all values
- `all` keyword for unfiltered

**v2 syntax:**
- Same as v1 but:
- Use `*` for wildcards (not empty string)
- Each dimension can only have one value (use wildcards for multiple)

### Query Parameters

| Parameter | Version | Description |
|-----------|---------|-------------|
| `startPeriod` | v1 | Start date (inclusive) |
| `endPeriod` | v1 | End date (inclusive) |
| `c[TIME_PERIOD]` | v2 | Time filter: `ge:2018+le:2024` |
| `lastNObservations` | both | Last N observations per series |
| `dimensionAtObservation` | both | Grouping dimension or `AllDimensions` |
| `detail` | v1 | `Full`, `DataOnly`, `SeriesKeysOnly`, `NoData` |
| `attributes` | v2 | `all`, `none`, `dsd`, `msd` |
| `measures` | v2 | `all`, `none` |
| `updatedAfter` | both | For incremental updates |

---

## Key Differences from ECB

| Aspect | ECB | OECD |
|--------|-----|------|
| Agency ID | `ECB` | Hierarchical: `OECD.ENV.EPI`, `OECD.ELS.SPD` |
| Dataflow ID | `EXR`, `ICP` | Contains `@`: `DSD_ECH@EXT_DROUGHT` |
| Base URL | `data-api.ecb.europa.eu/service` | `sdmx.oecd.org/public/rest` |
| Rate limit | Not specified | 60/hour |
| API version | v1 only | v1 and v2 |

---

## Example Queries

### Get Data (v1)
```
https://sdmx.oecd.org/public/rest/data/OECD.ENV.EPI,DSD_ECH@EXT_DROUGHT,1.0/AFG+BFA.A.ED_CROP_IND.....?startPeriod=1981&endPeriod=2021
```

### Get Data (v2)
```
https://sdmx.oecd.org/public/rest/v2/data/dataflow/OECD.ENV.EPI/DSD_ECH@EXT_DROUGHT/1.0/AFG.A.ED_CROP_IND.*.*.*.*.*?c[TIME_PERIOD]=ge:1981+le:2021
```

### Get Structure
```
https://sdmx.oecd.org/public/rest/dataflow/OECD.ENV.EPI/DSD_ECH@EXT_DROUGHT/1.0?references=all&detail=referencepartial
```

### Content Constraint (check last update)
```
https://sdmx.oecd.org/public/rest/contentconstraint/OECD.ELS.SPD/CR_A_DSD_SOCX_AGG@DF_SOCX_AGG/
```

---

## Implementation Plan

### 1. Create OECDConnector

```python
class OECDConnector(BaseConnector):
    """OECD SDMX API connector."""

    BASE_URL = "https://sdmx.oecd.org/public/rest"

    # Key differences from ECB:
    # - Agency IDs are hierarchical (OECD.ENV.EPI)
    # - Dataflow IDs contain @ symbol
    # - Need to handle both v1 and v2 API
    # - Rate limiting: 60 requests/hour
```

### 2. Create OECDProvider

```python
class OECDProvider(BaseProvider):
    """OECD data provider."""

    provider_id = "oecd"
    name = "Organisation for Economic Co-operation and Development"

    @property
    def catalog_dir(self) -> Path:
        return Path(__file__).parents[3] / "catalog" / "oecd"
```

### 3. Ingestion Scripts

Create `scripts/ingest_oecd_structures.py`:
- Fetch available dataflows from OECD
- Extract dimensions, codes, and attributes
- Write to `catalog/oecd/structures/`
- Rate limit: 60 requests/hour (sleep 60s between batches)

### 4. Curated Series Catalog

Priority datasets for `catalog/series/oecd_global.json`:

| Series | Description | Dataset |
|--------|-------------|---------|
| GDP growth | Real GDP growth rate | QNA |
| Unemployment | Unemployment rate | MEI_CLI |
| Inflation | CPI inflation | PRICES_CPI |
| Trade balance | Current account % GDP | MEI_BOP6 |
| Government debt | General government debt % GDP | GOV_DEBT |
| Leading indicators | CLI composite | MEI_CLI |
| House prices | Real house price index | HOUSE_PRICES |
| Productivity | Labour productivity | PDB_LV |

---

## Why OECD

1. **38 member countries** including all major economies (US, EU, Japan, etc.)
2. **Economic Outlook projections** - forward-looking forecasts
3. **Composite Leading Indicators (CLI)** - early warning system
4. **Comparable cross-country data** - standardized definitions
5. **Long time series** - many indicators back to 1960s
6. **Quality metadata** - detailed methodological notes

---

## Resources

- [OECD Data Explorer](https://data-explorer.oecd.org/)
- [API Documentation (PDF)](https://gitlab.algobank.oecd.org/public-documentation/dotstat-migration/-/raw/main/OECD_Data_API_documentation.pdf)
- [API Best Practices](https://www.oecd.org/en/data/insights/data-explainers/2024/11/Api-best-practices-and-recommendations.html)
- [Legacy SDMX-JSON Docs](https://data.oecd.org/api/sdmx-json-documentation/)
- [SDMX Standard](https://sdmx.org/)

---

## Notes

- **Caching is critical**: OECD recommends caching locally to avoid hitting rate limits
- Use `contentconstraint` query to check if data has been updated before re-fetching
- Most OECD datasets update infrequently (1-2 times per year)
- The legacy `stats.oecd.org` API is being deprecated; use `sdmx.oecd.org`
