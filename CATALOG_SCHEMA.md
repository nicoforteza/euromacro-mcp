# CATALOG SCHEMA

The curated catalog is the **core IP** of eurodata-mcp. It is a deliberate selection of the ~100–300 series that a European macro economist actually uses — not an index of all available data.

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
| `source` | enum | ✅ | `ecb` \| `eurostat` \| `ine` |
| `dataset` | string | ✅ | Dataset code at source (e.g. `ICP`, `FM`, `BSI`) |
| `series_key` | string | ✅ | SDMX key or equivalent for the API call |

### Names & descriptions
| Field | Type | Required | Notes |
|---|---|---|---|
| `name_en` | string | ✅ | Short English name, max 80 chars |
| `name_es` | string | ✅ | Short Spanish name, max 80 chars |
| `description_en` | string | ✅ | Full description with economic context |
| `description_es` | string | ⬜ | Spanish description |
| `notes` | string | ⬜ | Nico's domain notes: methodology caveats, policy relevance, etc. |

### Series properties
| Field | Type | Required | Notes |
|---|---|---|---|
| `frequency` | enum | ✅ | `daily` \| `monthly` \| `quarterly` \| `annual` |
| `unit` | string | ✅ | e.g. `% year-on-year`, `EUR millions`, `index 2015=100` |
| `seasonal_adjustment` | enum | ⬜ | `not_adjusted` \| `seasonally_adjusted` \| `working_day_adjusted` |

### Geography
| Field | Type | Required | Notes |
|---|---|---|---|
| `geography` | string | ✅ | Human-readable: `euro_area`, `spain`, `germany` |
| `geography_code` | string | ✅ | ISO/SDMX code: `U2`, `ES`, `DE` |
| `geography_level` | enum | ✅ | `supranational` \| `country` \| `regional` |

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
interest_rates      → ECB rates, Euribor, money markets
monetary            → M1, M2, M3, credit aggregates
gdp_growth          → GDP, economic activity
labor_market        → Unemployment, employment, wages
trade               → Trade balance, exports, imports
fiscal              → Public debt, deficit, government spending
financial_stability → Sovereign spreads, CDS, banking indicators
surveys             → PMI, ESI, consumer/business confidence
housing             → House prices, mortgages
```

---

## How Nico adds series to the catalog

1. Find the series on [ECB Data Portal](https://data.ecb.europa.eu) — verify data availability and history depth (min. 5 years)
2. Copy the exact `series_key` from the portal URL
3. Add JSON entry following this schema
4. Include all search terms an economist would use in `tags` (include synonyms in EN and ES)
5. Set `priority: 1` only for series any Euro Area macro analysis needs — be strict, max 15–20 series at this level
6. Add at least one `related_series` when logical — helps agents navigate the catalog

## Catalog validation

```python
REQUIRED_FIELDS = [
    "id", "source", "dataset", "series_key",
    "name_en", "frequency", "unit",
    "geography", "geography_code", "geography_level",
    "tags", "category", "priority"
]
```
