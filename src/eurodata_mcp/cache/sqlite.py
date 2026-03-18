"""SQLite-based cache for time series data."""

from pathlib import Path
from typing import Any

import diskcache


class CacheManager:
    """Manages caching of time series data using diskcache."""

    def __init__(self, cache_dir: str | Path | None = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "eurodata-mcp"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(self.cache_dir))

    def get(self, key: str) -> Any | None:
        """Get a cached value by key."""
        return self._cache.get(key)

    def set(self, key: str, value: Any, expire: int | None = None) -> None:
        """Set a cached value with optional expiration (seconds)."""
        self._cache.set(key, value, expire=expire)

    def delete(self, key: str) -> bool:
        """Delete a cached value."""
        return self._cache.delete(key)

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def close(self) -> None:
        """Close the cache."""
        self._cache.close()
