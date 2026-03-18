"""Curated series catalog management."""

from .loader import CatalogLoader, SeriesEntry, get_catalog, load_catalog

__all__ = ["CatalogLoader", "SeriesEntry", "get_catalog", "load_catalog"]
