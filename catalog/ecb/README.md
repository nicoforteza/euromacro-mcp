# catalog/ecb — ECB Dataset Structure Catalog

This directory contains the machine-readable structure of every active ECB dataset,
extracted from the ECB's SDMX 2.1 API.

## Directory layout

```
catalog/ecb/
├── README.md              # This file
├── catalog_base.json      # Summary index: all datasets, status, dimension counts
├── structures/
│   ├── EXR.json           # Full structure for the Exchange Rates dataset
│   ├── ICP.json           # Full structure for HICP (inflation)
│   └── ...                # One file per dataset
└── errors/
    └── {DATASET_ID}.json  # Error detail when a fetch failed (transient — retry)
```

## How to regenerate

```bash
# Fetch all ~95 datasets (respects 7-day cache — skips fresh files)
uv run python scripts/ingest_ecb_structures.py

# Force a full re-fetch
uv run python scripts/ingest_ecb_structures.py --force

# Debug a single dataset
uv run python scripts/ingest_ecb_structures.py --dataset EXR
```

## Structure file schema

Each `structures/{ID}.json` follows this schema:

```json
{
  "dataset_id": "EXR",
  "fetched_at": "2025-01-15T10:30:00Z",
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
        "B": "Business"
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
  "notes": "",
  "_stats": {
    "n_dimensions": 5,
    "n_attributes": 12,
    "total_codes": 4350
  }
}
```

### Fields

| Field | Description |
|---|---|
| `dataset_id` | ECB dataset identifier (e.g., `EXR`) |
| `fetched_at` | ISO 8601 timestamp of when the structure was fetched |
| `dimensions` | Ordered list of key dimensions (position matters for building series keys) |
| `dimensions[].position` | 1-based position in the series key |
| `dimensions[].id` | Dimension identifier (e.g., `FREQ`) |
| `dimensions[].name` | Human-readable name from the ECB concept scheme |
| `dimensions[].codelist_id` | SDMX codelist ID (e.g., `CL_FREQ`) |
| `dimensions[].codes` | Map of valid code values to their descriptions |
| `attributes` | Series and observation attributes (not part of the series key) |
| `attributes[].assignment` | `Mandatory` or `Conditional` |
| `example_key_pattern` | Template showing the key structure: `DIM1.DIM2.DIM3...` |
| `_stats` | Counts for quick inspection without parsing the full structure |

## catalog_base.json schema

```json
{
  "generated_at": "2025-01-15T10:35:00Z",
  "total_datasets": 95,
  "successful": 92,
  "failed": 3,
  "datasets": [
    {
      "dataset_id": "EXR",
      "status": "ok",
      "n_dimensions": 5,
      "n_attributes": 12,
      "total_codes": 4350
    }
  ]
}
```

Status values: `ok` (freshly fetched), `cached` (served from local cache), `error` (fetch failed).

## How to build a valid series key

1. Look up `structures/{DATASET_ID}.json`
2. Sort dimensions by `position`
3. For each dimension, choose a valid code from `codes`
4. Join with `.` → `A.USD.EUR.SP00.A` (example for EXR)

## Data source

ECB SDMX 2.1 REST API — structure endpoint:

```
GET https://data-api.ecb.europa.eu/service/datastructure/ECB/{DATASET_ID}
    ?references=all&detail=full
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

The `references=all` parameter instructs the API to inline all referenced codelists
and concept schemes in a single response, avoiding the need for follow-up requests.
