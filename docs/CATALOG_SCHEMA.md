# Catalog Schema

Each series in the catalog follows this schema:

```json
{
  "id": "source:short_name",
  "name": "Human Readable Name",
  "description": "Detailed description of the series",
  "source": "ecb|eurostat|ine",
  "series_key": "Original API series key",
  "frequency": "daily|weekly|monthly|quarterly|annual",
  "unit": "percent|index|millions_eur|...",
  "tags": ["tag1", "tag2"]
}
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| id | Yes | Unique identifier: `source:short_name` |
| name | Yes | Human-readable name (< 80 chars) |
| description | Yes | Full description |
| source | Yes | Data source identifier |
| series_key | Yes | Original API key for fetching |
| frequency | Yes | Data frequency |
| unit | Yes | Unit of measurement |
| tags | Yes | Searchable tags |

## Example Series (MVP Candidates)

### Inflation
- HICP headline
- HICP core (ex food & energy)
- PPI

### Interest Rates
- ECB main refinancing rate
- EONIA/ESTR
- 10Y government bond yields

### Real Economy
- GDP growth
- Industrial production
- Unemployment rate

### Money & Credit
- M3 growth
- Bank lending to households
- Bank lending to corporations
