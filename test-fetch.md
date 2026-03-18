# /test-fetch

Fetch a series directly from the ECB API and display the result. Useful for validating a series key before adding it to the catalog.

## Usage
```
/test-fetch <series_id_or_ecb_key>
```

Examples:
```
/test-fetch ecb_hicp_ea_yoy
/test-fetch ICP/M.U2.N.000000.4.INX
```

## Steps Claude should follow

1. Determine if input is an internal catalog ID or a raw ECB series key:
   - If it contains a `/`, treat as raw ECB key (dataset/series format)
   - Otherwise, look up in the catalog to get the ECB key

2. Run a test fetch using the ECB connector:
   ```bash
   uv run python -c "
   import asyncio
   from eurodata_mcp.connectors.ecb import ECBConnector
   
   async def test():
       conn = ECBConnector()
       result = await conn.fetch_series('DATASET', 'SERIES_KEY', start='2020-01')
       print(f'Observations: {len(result)}')
       print(f'Latest 5: {result.tail()}')
   
   asyncio.run(test())
   "
   ```

3. Display:
   - Number of observations returned
   - Date range (first and last observation)
   - Last 3 values with dates
   - Any errors or warnings

4. If the fetch fails, diagnose the issue:
   - Invalid series key format
   - Series not available for the requested period
   - API connectivity issue
   - Suggest corrections if possible
