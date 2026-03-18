# CATALOG SCHEMA

The curated catalog is the **core IP** of eurodata-mcp. It is a deliberate selection of the ~100–300 series per provider that a macro economist actually uses — not an index of all available data.

> Anyone can write an ECB API connector. Not everyone knows which 25 ECB series you need to understand the European business cycle.

---

## Series JSON schema

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
  "notes": "ECB inflation target: 2% symmetric (since 2021 strategy review). Key series for any Euro Area macro analysis.",

  "availability": {
    "start_period": "1997-01",
    "update_lag_days": 20,
    "update_frequency": "monthly"
  },

  "related_series": ["ecb_hicp_ea_core_yoy", "ecb_hicp_ea_energy_yoy", "ecb_rate_dfr"]
}
```

---

## Fields reference

### Identification
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | ✅ | Unique internal ID. Format: `{source}_{topic}_{area}_{transformation}` |
| `source` | enum | ✅ | `ecb` \| `bis` \| `imf` \| `fred` |
| `dataset` | string | ✅ | Dataset code at source (e.g. `ICP`, `FM`, `BSI`, `WEO`) |
| `series_key` | string | ✅ | SDMX key or series ID for the API call |

### Names & descriptions
| Field | Type | Required | Notes |
|---|---|---|---|
| `name_en` | string | ✅ | Short English name, max 80 chars |
| `name_es` | string | ✅ | Short Spanish name, max 80 chars |
| `description_en` | string | ✅ | Full description with economic context |
| `description_es` | string | ⬜ | Spanish description |
| `notes` | string | ⬜ | Domain notes: methodology caveats, policy relevance, etc. |

### Series properties
| Field | Type | Required | Notes |
|---|---|---|---|
| `frequency` | enum | ✅ | `daily` \| `monthly` \| `quarterly` \| `annual` |
| `unit` | string | ✅ | e.g. `% year-on-year`, `EUR millions`, `index 2015=100` |
| `seasonal_adjustment` | enum | ⬜ | `not_adjusted` \| `seasonally_adjusted` \| `working_day_adjusted` |

### Geography
| Field | Type | Required | Notes |
|---|---|---|---|
| `geography` | string | ✅ | Human-readable: `euro_area`, `spain`, `united_states`, `global` |
| `geography_code` | string | ✅ | ISO/SDMX code: `U2`, `ES`, `US`, `W1` |
| `geography_level` | enum | ✅ | `supranational` \| `country` \| `regional` \| `global` |

### Classification & search
| Field | Type | Required | Notes |
|---|---|---|---|
| `tags` | string[] | ✅ | Search keywords, include EN and ES synonyms |
| `category` | enum | ✅ | See categories below |
| `priority` | int | ✅ | 1=essential, 2=important, 3=supplementary. Affects search ranking. |

### Availability
| Field | Type | Required | Notes |
|---|---|---|---|
| `availability.start_period` | string | ✅ | First available observation (YYYY-MM) |
| `availability.update_lag_days` | int | ⬜ | Days from period end to publication |

---

## Available categories

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

---

## Source-specific conventions

### ECB
- `id`: `ecb_{topic}_{area}_{transformation}`
- `dataset`: ECB dataflow code (ICP, FM, BSI, MNA, LFSI, EXR)
- `series_key`: SDMX key (e.g., `M.U2.N.000000.4.INX`)

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
- `series_key`: FRED series ID (e.g., `CPIAUCSL`, `FEDFUNDS`)

---

## Adding series to the catalog

1. Identify the series on the provider's data portal
2. Verify data availability and history depth (min. 5 years)
3. Copy the exact `series_key` from the portal
4. Add JSON entry following this schema
5. Include all search terms an economist would use in `tags` (EN and ES)
6. Set `priority: 1` only for essential series — be strict, max 15–20 per provider
7. Add at least one `related_series` when logical
8. Run validation: `uv run python -c "from eurodata_mcp.catalog import get_catalog; get_catalog()"`

---

## Catalog validation

```python
REQUIRED_FIELDS = [
    "id", "source", "dataset", "series_key",
    "name_en", "frequency", "unit",
    "geography", "geography_code", "geography_level",
    "tags", "category", "priority"
]

VALID_SOURCES = ["ecb", "bis", "imf", "fred"]

VALID_FREQUENCIES = ["daily", "monthly", "quarterly", "annual"]

VALID_GEOGRAPHY_LEVELS = ["supranational", "country", "regional", "global"]
```

---

## File organization

```
catalog/
├── loader.py              # CatalogLoader singleton
└── series/
    ├── ecb_euro_area.json # ECB curated series
    ├── bis_global.json    # BIS curated series (M2)
    ├── imf_global.json    # IMF curated series (M3)
    └── fred_us.json       # FRED curated series (M4)
```
