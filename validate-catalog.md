# /validate-catalog

Validate all catalog JSON files against the schema defined in `docs/CATALOG_SCHEMA.md`.

## Usage
```
/validate-catalog
```

## Steps Claude should follow

1. Find all catalog files:
   ```bash
   find src/eurodata_mcp/catalog/series -name "*.json"
   ```

2. For each file, validate:
   - Valid JSON syntax
   - All required fields present per entry (see `REQUIRED_FIELDS` in `docs/CATALOG_SCHEMA.md`)
   - No duplicate `id` values within or across files
   - `source` matches the filename convention
   - `frequency` is one of: `daily`, `monthly`, `quarterly`, `annual`
   - `geography_level` is one of: `supranational`, `country`, `regional`
   - `priority` is 1, 2, or 3
   - `tags` is a non-empty array of strings
   - `category` is one of the valid categories

3. Report:
   - Total series count per source
   - Any validation errors with line/entry references
   - Priority distribution (how many P1, P2, P3)
   - Categories covered

4. If errors found, offer to fix them interactively
