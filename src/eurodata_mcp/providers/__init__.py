"""Data providers for eurodata-mcp.

Each provider represents a data source (ECB, BIS, IMF, FRED, etc.)
and includes:
- Connector: API client for fetching data
- Guide: Conceptual documentation for AI agents
- Examples: Common query patterns
- Aliases: Natural language to code mappings

The aggregator layer uses these providers to route queries
to the appropriate data source.
"""

from .base import BaseProvider, ProviderRegistry
from .ecb import ECBProvider

__all__ = [
    "BaseProvider",
    "ProviderRegistry",
    "ECBProvider",
]
