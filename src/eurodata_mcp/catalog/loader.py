"""Catalog loader for curated series definitions."""

import json
from pathlib import Path
from typing import Any


def load_catalog(name: str = "ecb_euro_area") -> list[dict[str, Any]]:
    """Load a series catalog by name.

    Args:
        name: Catalog name (without .json extension)

    Returns:
        List of series definitions
    """
    catalog_dir = Path(__file__).parent / "series"
    catalog_file = catalog_dir / f"{name}.json"

    if not catalog_file.exists():
        return []

    with open(catalog_file) as f:
        return json.load(f)
