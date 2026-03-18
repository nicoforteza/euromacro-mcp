# CATALOG SCHEMA

The catalog has two layers, serving different purposes:

- **Layer 1 — Curated series** (`SeriesEntry`): ~25 hand-picked ECB series with exact series keys. Instant answers to common macro questions.
- **Layer 2 — Enriched datasets** (`DatasetEntry`): 100 ECB datasets with semantic metadata. Enables natural language discovery and exploration of the full 300k+ series warehouse.

> The curated series list is the IP. Anyone can write an ECB API connector; not everyone knows which 25 ECB series you need to understand the European business cycle.

---

## Layer 1 — SeriesEntry schema

```json
{
  "id": "ecb_hicp_ea_yoy",
  "source": "ecb",
  "dataset": "ICP",
  "series_key": "M.U2.N.000000.4.INX",

  "name_en": "HICP Inflation Rate, Euro Area (YoY %)",
  "name_es": "Tasa de inflación IAPC, Área Euro (% interanual)",
  "description_en": "Harmonised Index of Consumer Prices, all items, Euro Area. Year-on-year rate of change. ECB's primary inflation measure for monetary policy decisions.",
  "description_es": "Índice Armonizado de Precios al Consumo, todos los artículos, Área Euro. Tasa de variación anual. Medida principal de inflación del BCE.",

  "frequency": "monthly",
  "unit": "% year-on-year",
  "seasonal_adjustment": "not_adjusted",

  "geography": "euro_area",
  "geography_code": "U2",
  "geography_level": "supranational",

  "tags": ["inflation", "prices", "hicp", "cpi", "euro area", "monetary policy", "iapc"],
  "category": "prices",
  "subcategory": "consumer_prices",

  "priority": 1,
  "notes": "ECB inflation target: 2% symmetric (since 2021 strategy review).",

  "availability": {
    "start_period": "1997-01",
    "update_lag_days": 20,
    "update_frequency": "monthly"
  },

  "related_series": ["ecb_hicp_ea_core_yoy", "ecb_hicp_ea_energy_yoy", "ecb_rate_dfr"]
}
```

### SeriesEntry field reference

#### Identification
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | ✅ | Unique ID. Format: `{source}_{topic}_{area}_{transformation}` |
| `source` | enum | ✅ | `ecb` \| `bis` \| `imf` \| `fred` |
| `dataset` | string | ✅ | Dataset code at source (e.g. `ICP`, `FM`, `BSI`) |
| `series_key` | string | ✅ | SDMX key or series ID for the API call |

#### Names & descriptions
| Field | Type | Required | Notes |
|---|---|---|---|
| `name_en` | string | ✅ | Short English name, max 80 chars |
| `name_es` | string | ✅ | Short Spanish name, max 80 chars |
| `description_en` | string | ✅ | Full description with economic context |
| `description_es` | string | ⬜ | Spanish description |
| `notes` | string | ⬜ | Methodology caveats, policy relevance |

#### Series properties
| Field | Type | Required | Notes |
|---|---|---|---|
| `frequency` | enum | ✅ | `daily` \| `monthly` \| `quarterly` \| `annual` |
| `unit` | string | ✅ | e.g. `% year-on-year`, `EUR millions`, `index 2015=100` |
| `seasonal_adjustment` | enum | ⬜ | `not_adjusted` \| `seasonally_adjusted` \| `working_day_adjusted` |

#### Geography
| Field | Type | Required | Notes |
|---|---|---|---|
| `geography` | string | ✅ | Human-readable: `euro_area`, `spain`, `united_states` |
| `geography_code` | string | ✅ | ISO/SDMX code: `U2`, `ES`, `US` |
| `geography_level` | enum | ✅ | `supranational` \| `country` \| `regional` \| `global` |

#### Classification & search
| Field | Type | Required | Notes |
|---|---|---|---|
| `tags` | string[] | ✅ | Search keywords, include EN and ES synonyms |
| `category` | enum | ✅ | See categories below |
| `priority` | int | ✅ | 1=essential, 2=important, 3=supplementary |

### Available categories

```
prices              → Inflation, CPI, deflators
interest_rates      → Central bank rates, money markets
monetary            → M1, M2, M3, credit aggregates
gdp_growth          → GDP, economic activity
labor_market        → Unemployment, employment, wages
trade               → Trade balance, exports, imports
fiscal              → Public debt, deficit, government spending
financial_stability → Sovereign spreads, CDS, banking indicators
surveys             → PMI, ESI, consumer/business confidence
housing             → House prices, mortgages
banking             → Cross-border claims, credit to private sector
external            → Balance of payments, current account
```

### File location

```
src/eurodata_mcp/catalog/series/
├── ecb_euro_area.json    # ECB curated series (current)
├── bis_global.json       # BIS curated series (M2)
├── imf_global.json       # IMF curated series (M3)
└── fred_us.json          # FRED curated series (M4)
```

### Adding a curated series

1. Identify the series on the provider's data portal
2. Verify availability and history depth (min. 5 years preferred)
3. Copy the exact `series_key` from the portal or from `catalog/ecb/structures/{DATASET}.json`
4. Add JSON entry following this schema
5. Include all search terms an economist would use in `tags` (EN and ES)
6. Set `priority: 1` only for essential series — max 15–20 per provider
7. Add at least one `related_series` when logical
8. Run: `uv run python -c "from eurodata_mcp.catalog import get_catalog; get_catalog()"`

---

## Layer 2 — DatasetEntry schema

Stored in `catalog/ecb/enriched/{ID}.json` (one per dataset) and consolidated in `catalog/ecb/catalog_enriched.json`.

```json
{
  "id": "EXR",
  "name": "Exchange Rates",
  "description_short": "Official ECB exchange rates for the euro against all major currencies, available at daily, monthly, quarterly, and annual frequency.",
  "concepts": [
    "exchange rate", "EUR", "FX", "forex", "currency",
    "bilateral rate", "effective exchange rate", "EER",
    "EUR/USD", "EUR/GBP", "EUR/JPY", "EUR/CHF",
    "nominal exchange rate", "real exchange rate", "currency basket"
  ],
  "use_cases": [
    "What is the current EUR/USD exchange rate?",
    "How has the euro depreciated against the dollar this year?",
    "What is the nominal effective exchange rate of the euro?",
    "How does the euro compare to a basket of trading partner currencies?"
  ],
  "primary_frequency": "D",
  "geographic_coverage": "global",
  "key_dimensions": ["CURRENCY", "CURRENCY_DENOM", "EXR_TYPE", "EXR_SUFFIX"],
  "enriched_at": "2026-03-18T00:00:00Z"
}
```

### DatasetEntry field reference

| Field | Type | Notes |
|---|---|---|
| `id` | string | ECB dataset code (e.g. `EXR`, `HICP`, `BLS`) |
| `name` | string | Official ECB dataset name |
| `description_short` | string | 1-2 sentences in plain English for an economist |
| `concepts` | string[] | 12-20 keywords mixing acronyms and full forms |
| `use_cases` | string[] | 4-6 concrete questions this dataset can answer |
| `primary_frequency` | enum | `A`, `Q`, `M`, `D`, or `MIXED` |
| `geographic_coverage` | enum | `euro_area_only`, `euro_area_and_countries`, `eu_wide`, `global` |
| `key_dimensions` | string[] | Most analytically important dimension IDs (not FREQ) |
| `enriched_at` | ISO 8601 | Timestamp of enrichment run |

### Regenerating the enriched catalog

```bash
# Re-fetch all SDMX structures from ECB (respects 7-day cache)
uv run python scripts/ingest_ecb_structures.py

# Force re-fetch a single dataset
uv run python scripts/ingest_ecb_structures.py --dataset EXR

# Re-enrich all datasets (requires ANTHROPIC_API_KEY or runs locally)
uv run python scripts/enrich_ecb_catalog.py

# Re-enrich specific datasets
uv run python scripts/enrich_ecb_catalog.py --dataset EXR ICP HICP

# Force re-enrich (ignore existing files)
uv run python scripts/enrich_ecb_catalog.py --force
```

---

## Source-specific SeriesEntry conventions

### ECB
- `id`: `ecb_{topic}_{area}_{transformation}`
- `dataset`: ECB dataflow code (ICP, FM, BSI, EXR, MIR, LFSI...)
- `series_key`: SDMX key (e.g. `M.U2.N.000000.4.INX`)
- Series keys can be verified against `catalog/ecb/structures/{DATASET}.json`

### BIS
- `id`: `bis_{topic}_{area}_{transformation}`
- `dataset`: BIS dataflow code (TOTAL_CREDIT, LONG_PP, LBS, CBS)
- `series_key`: SDMX key

### IMF
- `id`: `imf_{topic}_{area}_{transformation}`
- `dataset`: IMF database code (WEO, IFS, BOP, GFS)
- `series_key`: Indicator code

### FRED
- `id`: `fred_{topic}_{transformation}`
- `dataset`: Category or N/A
- `series_key`: FRED series ID (e.g. `CPIAUCSL`, `FEDFUNDS`)
