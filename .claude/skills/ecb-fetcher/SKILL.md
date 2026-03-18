# SKILL: ecb-fetcher

Reusable patterns and reference for fetching and parsing ECB SDMX-JSON data.

## When to use this skill
Load this skill when working on anything involving the ECB connector: implementing, debugging, extending, or writing tests for ECB data fetching.

---

## ECB SDMX-JSON response structure

The ECB API returns SDMX-JSON. The structure is non-obvious. Always follow this parsing pattern:

```python
import httpx
import pandas as pd

ECB_BASE = "https://sdw-wsrest.ecb.europa.eu/service"

async def fetch_and_parse(dataset: str, series_key: str, start: str, end: str = None) -> pd.DataFrame:
    url = f"{ECB_BASE}/data/{dataset}/{series_key}"
    params = {"startPeriod": start, "format": "jsondata"}
    if end:
        params["endPeriod"] = end

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    # Parse time dimension
    obs_dim = data["structure"]["dimensions"]["observation"][0]
    time_periods = [v["id"] for v in obs_dim["values"]]

    # Parse observations
    records = []
    for series_data in data["dataSets"][0]["series"].values():
        for obs_idx, obs_values in series_data["observations"].items():
            value = obs_values[0]  # None if missing
            if value is not None:
                records.append({
                    "date": time_periods[int(obs_idx)],
                    "value": float(value)
                })

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return df
```

---

## Common error patterns

### HTTP 404 — Series not found
The series key is wrong or the dataset code is incorrect. Check against ECB Data Portal.

### HTTP 400 — Bad request
Usually a malformed key. ECB keys are dot-separated: `M.U2.N.000000.4.INX` — check all dimensions are present.

### Empty observations
Series exists but no data for the requested period. Try a wider `startPeriod`.

### Slow response
ECB API can be slow (~5–10s for long series). Always set `timeout=30`. Do not set `timeout=5`.

---

## Rate limiting strategy

```python
import asyncio

class ECBConnector:
    _last_request_time = 0.0
    _min_interval = 1.0  # seconds between requests

    async def _rate_limited_get(self, url, params):
        now = asyncio.get_event_loop().time()
        wait = self._min_interval - (now - self._last_request_time)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_time = asyncio.get_event_loop().time()
        # ... make request
```

---

## Date formats by frequency

| Frequency | ECB format | Example |
|---|---|---|
| Monthly | `YYYY-MM` | `2024-03` |
| Quarterly | `YYYY-Qn` | `2024-Q1` |
| Annual | `YYYY` | `2024` |
| Daily | `YYYY-MM-DD` | `2024-03-15` |

---

## Test fixture pattern

```python
# tests/fixtures/ecb_hicp_response.json
# Capture a real response and save as fixture for CI tests

import json
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def ecb_hicp_fixture():
    with open("tests/fixtures/ecb_hicp_response.json") as f:
        return json.load(f)

async def test_ecb_connector_parses_hicp(ecb_hicp_fixture):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: ecb_hicp_fixture
        )
        # ... test your connector
```
