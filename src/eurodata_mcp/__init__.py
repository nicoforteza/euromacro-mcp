"""eurodata-mcp: MCP server for European macroeconomic data."""

__version__ = "0.1.0"

from .catalog import CatalogLoader, DatasetEntry, get_catalog
from .connectors import BaseConnector, ECBConnector
from .server import mcp

__all__ = [
    "mcp",
    "CatalogLoader",
    "DatasetEntry",
    "get_catalog",
    "BaseConnector",
    "ECBConnector",
]
