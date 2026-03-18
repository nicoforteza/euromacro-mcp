# /add-series

Add a new series to the curated catalog.

## Usage
```
/add-series
```
Claude will ask you for the series details and add it to the appropriate catalog JSON file.

## Steps Claude should follow

1. Ask the user:
   - ECB/Eurostat/INE series key or URL from the data portal
   - Which catalog file it belongs to (ECB, Eurostat, INE)
   - Confirm the human-readable name and description

2. Read the existing catalog file:
   `src/eurodata_mcp/catalog/series/{source}_*.json`

3. Verify the series key format is valid for the source (see `docs/DATA_SOURCES.md`)

4. Generate the full JSON entry following the schema in `docs/CATALOG_SCHEMA.md`:
   - Generate a unique `id` following the `{source}_{topic}_{area}_{transformation}` convention
   - Include both `name_en` and `name_es`
   - Add relevant `tags` including synonyms in EN and ES
   - Set `priority` based on how essential the series is (1=essential, 2=important, 3=supplementary)
   - Suggest `related_series` from existing catalog entries

5. Ask the user to confirm the entry before writing

6. Append the entry to the catalog JSON file maintaining valid JSON structure

7. Run catalog validation:
   ```bash
   uv run python -c "from eurodata_mcp.catalog.loader import validate_catalog; validate_catalog()"
   ```

8. Confirm the series was added successfully
