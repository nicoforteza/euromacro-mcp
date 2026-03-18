# catalog/ecb — ECB Dataset Catalog

Single source of truth for ECB dataset metadata. Written by ingestion scripts, read directly by the MCP server at runtime.

## Directory layout

```
catalog/ecb/
├── README.md               # This file
├── catalog_base.json       # Ingestion index: all datasets, status, dimension counts
├── catalog_enriched.json   # 100 datasets with semantic metadata (runtime input)
├── enriched/               # Per-dataset semantic metadata
│   ├── EXR.json            # Exchange Rates — concepts, use_cases, frequency, coverage
│   ├── HICP.json           # Harmonised Index of Consumer Prices
│   └── ...                 # One file per dataset (100 total)
├── structures/             # Per-dataset SDMX structure
│   ├── EXR.json            # Dimensions (ordered), inline codes, attributes
│   ├── HICP.json
│   └── ...                 # One file per dataset (100 total)
└── errors/                 # Failed fetches (transient — retry with ingest script)
    └── {DATASET_ID}.json   # Error detail
```

## How to regenerate

```bash
# Fetch all ECB dataset structures (respects 7-day cache — skips fresh files)
uv run python scripts/ingest_ecb_structures.py

# Force a full re-fetch
uv run python scripts/ingest_ecb_structures.py --force

# Debug a single dataset
uv run python scripts/ingest_ecb_structures.py --dataset EXR

# Re-enrich semantic metadata (runs locally, no API key needed with LLM in context)
uv run python scripts/enrich_ecb_catalog.py

# Enrich specific datasets only
uv run python scripts/enrich_ecb_catalog.py --dataset EXR ICP HICP
```

## structures/{ID}.json schema

```json
{
  "dataset_id": "EXR",
  "structure_id": "ECB_EXR1",
  "fetched_at": "2026-03-18T18:59:48Z",
  "dimensions": [
    {
      "position": 1,
      "id": "FREQ",
      "name": "Frequency",
      "codelist_id": "CL_FREQ",
      "codes": {
        "A": "Annual",
        "Q": "Quarterly",
        "M": "Monthly",
        "D": "Daily",
        "B": "Daily - businessweek"
      }
    },
    {
      "position": 2,
      "id": "CURRENCY",
      "name": "Currency",
      "codelist_id": "CL_CURRENCY",
      "codes": {
        "USD": "US dollar",
        "GBP": "Pound sterling",
        "JPY": "Japanese yen"
      }
    }
  ],
  "attributes": [
    {
      "id": "DECIMALS",
      "name": "Decimals",
      "assignment": "Mandatory"
    }
  ],
  "example_key_pattern": "FREQ.CURRENCY.CURRENCY_DENOM.EXR_TYPE.EXR_SUFFIX",
  "_stats": {
    "n_dimensions": 5,
    "n_attributes": 12,
    "total_codes": 790
  }
}
```

### Fields

| Field | Description |
|---|---|
| `dataset_id` | ECB dataset identifier (e.g. `EXR`) |
| `structure_id` | ECB internal structure ID (e.g. `ECB_EXR1`) |
| `fetched_at` | ISO 8601 timestamp of last fetch |
| `dimensions` | Ordered list — **position matters** for building series keys |
| `dimensions[].position` | 1-based position in the series key |
| `dimensions[].id` | Dimension identifier (e.g. `FREQ`) |
| `dimensions[].name` | Human-readable name from ECB concept scheme |
| `dimensions[].codelist_id` | SDMX codelist ID (e.g. `CL_FREQ`) |
| `dimensions[].codes` | Map of valid code → description (inline) |
| `attributes` | Series attributes — not part of the key |
| `example_key_pattern` | Template: `DIM1.DIM2.DIM3...` |
| `_stats` | Quick-inspection counts |

## enriched/{ID}.json schema

```json
{
  "id": "EXR",
  "name": "Exchange Rates",
  "description_short": "Official ECB exchange rates for the euro against all major currencies, available at daily, monthly, quarterly, and annual frequency.",
  "concepts": [
    "exchange rate", "EUR", "FX", "forex", "currency", "bilateral rate",
    "effective exchange rate", "EER", "EUR/USD", "EUR/GBP", "EUR/JPY",
    "nominal exchange rate", "real exchange rate", "currency basket"
  ],
  "use_cases": [
    "What is the current EUR/USD exchange rate?",
    "How has the euro depreciated against the dollar this year?",
    "What is the nominal effective exchange rate of the euro?"
  ],
  "primary_frequency": "D",
  "geographic_coverage": "global",
  "key_dimensions": ["CURRENCY", "CURRENCY_DENOM", "EXR_TYPE", "EXR_SUFFIX"],
  "enriched_at": "2026-03-18T00:00:00Z"
}
```

## catalog_enriched.json schema

Runtime input for `explore_datasets` and `search_series` (Layer 2 fallback).

```json
{
  "generated_at": "2026-03-18T00:00:00Z",
  "ecb_api_base": "https://data-api.ecb.europa.eu/service",
  "total_datasets": 100,
  "datasets": [
    { ...full enriched schema for each dataset... }
  ]
}
```

## catalog_base.json schema

Ingestion run index — useful for monitoring and debugging.

```json
{
  "generated_at": "2026-03-18T18:59:48Z",
  "total_datasets": 93,
  "successful": 77,
  "cached": 3,
  "failed": 13,
  "datasets": [
    {
      "dataset_id": "EXR",
      "status": "ok",
      "n_dimensions": 5,
      "n_attributes": 12,
      "total_codes": 790
    }
  ]
}
```

Status values: `ok` (freshly fetched), `cached` (served from local file), `error` (fetch failed — see `errors/`).

## How to build a valid series key

1. Look up `structures/{DATASET_ID}.json`
2. Sort dimensions by `position`
3. For each dimension, pick a valid code from `codes`
4. Join with `.` — e.g. `M.USD.EUR.SP00.A` for EXR

Or use the MCP tool:

```
build_series(provider_id="ecb", dataset="EXR", dimensions={
    "FREQ": "M",
    "CURRENCY": "USD",
    "CURRENCY_DENOM": "EUR",
    "EXR_TYPE": "SP00",
    "EXR_SUFFIX": "A"
})
→ series_key: "M.USD.EUR.SP00.A"
→ data_url: "https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?format=jsondata"
```

## Data source

ECB SDMX 2.1 REST API:

```
# Structure (used by ingest_ecb_structures.py)
GET https://data-api.ecb.europa.eu/service/datastructure/ECB/{DATASET_ID}
    ?references=all&detail=full
Accept: application/vnd.sdmx.structure+xml;version=2.1

# Data (used at runtime by ECBConnector)
GET https://data-api.ecb.europa.eu/service/data/{DATASET_ID}/{SERIES_KEY}
    ?format=jsondata&startPeriod={YYYY-MM}
```
