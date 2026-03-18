"""MCP tools for series search, fetch, and description."""

from .series import (
    describe_series,
    get_series,
    list_categories,
    search_series,
)

__all__ = [
    "search_series",
    "get_series",
    "describe_series",
    "list_categories",
]
