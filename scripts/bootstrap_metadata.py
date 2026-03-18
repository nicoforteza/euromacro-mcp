#!/usr/bin/env python3
"""Bootstrap script to populate ECB metadata cache.

This script fetches all dataflows, their structures, and commonly used codelists
from the ECB API and caches them locally for fast access.

Usage:
    uv run python scripts/bootstrap_metadata.py
    uv run python scripts/bootstrap_metadata.py --full  # Include all codelists
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eurodata_mcp.connectors.ecb import ECBConnector, ECBConnectorError
from eurodata_mcp.metadata import get_metadata_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Priority datasets to cache structures for
PRIORITY_DATASETS = [
    "ICP",   # Inflation (HICP)
    "FM",    # Financial Markets (interest rates)
    "BSI",   # Balance Sheet Items (money supply, credit)
    "MNA",   # National Accounts (GDP)
    "LFSI",  # Labour Force (unemployment)
    "EXR",   # Exchange Rates
    "STS",   # Short-Term Statistics
    "BOP",   # Balance of Payments
    "SEC",   # Securities
    "MIR",   # Interest Rates on deposits/loans
]

# Common codelists to cache
COMMON_CODELISTS = [
    "CL_AREA",        # Countries and areas
    "CL_FREQ",        # Frequencies
    "CL_UNIT",        # Units
    "CL_ADJUSTMENT",  # Seasonal adjustment
    "CL_CURRENCY",    # Currencies
]


async def bootstrap_dataflows(connector: ECBConnector, cache) -> list[dict]:
    """Fetch and cache all dataflows."""
    logger.info("Fetching dataflows...")
    try:
        dataflows = await connector.fetch_dataflows()
        cache.save_dataflows(dataflows)
        logger.info(f"Cached {len(dataflows)} dataflows")
        return dataflows
    except ECBConnectorError as e:
        logger.error(f"Failed to fetch dataflows: {e}")
        return []


async def bootstrap_structures(
    connector: ECBConnector,
    cache,
    dataflows: list[dict],
    priority_only: bool = True,
) -> int:
    """Fetch and cache data structures."""
    logger.info("Fetching data structures...")

    if priority_only:
        # Only cache priority datasets
        target_ids = set()
        for df in dataflows:
            df_id = df.get("id", "")
            if df_id in PRIORITY_DATASETS:
                structure_id = df.get("structure_id", "")
                if structure_id:
                    target_ids.add(structure_id)

        logger.info(f"Caching {len(target_ids)} priority structures")
    else:
        # Cache all structures (can be slow)
        target_ids = {df.get("structure_id", "") for df in dataflows}
        target_ids.discard("")
        logger.info(f"Caching all {len(target_ids)} structures")

    cached = 0
    for structure_id in target_ids:
        try:
            structure = await connector.fetch_datastructure(structure_id)
            cache.save_structure(structure_id, structure)
            cached += 1
            logger.info(f"  [{cached}/{len(target_ids)}] {structure_id}")
        except ECBConnectorError as e:
            logger.warning(f"  Failed to fetch {structure_id}: {e}")

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.2)

    return cached


async def bootstrap_codelists(
    connector: ECBConnector,
    cache,
    full: bool = False,
) -> int:
    """Fetch and cache codelists."""
    logger.info("Fetching codelists...")

    if full:
        # Get all codelists referenced in cached structures
        codelist_ids = set(COMMON_CODELISTS)
        for structure_id in cache.list_cached_structures():
            structure = cache.get_structure(structure_id)
            if structure:
                for dim in structure.get("dimensions", []):
                    cl_id = dim.get("codelist", "")
                    if cl_id:
                        codelist_ids.add(cl_id)
        logger.info(f"Caching {len(codelist_ids)} codelists")
    else:
        codelist_ids = set(COMMON_CODELISTS)
        logger.info(f"Caching {len(codelist_ids)} common codelists")

    cached = 0
    for codelist_id in codelist_ids:
        try:
            codes = await connector.fetch_codelist(codelist_id)
            if codes:
                cache.save_codelist(codelist_id, codes)
                cached += 1
                logger.info(f"  [{cached}/{len(codelist_ids)}] {codelist_id}: {len(codes)} codes")
        except ECBConnectorError as e:
            logger.warning(f"  Failed to fetch {codelist_id}: {e}")

        await asyncio.sleep(0.2)

    return cached


async def main(full: bool = False):
    """Run the bootstrap process."""
    cache = get_metadata_cache()

    logger.info("=" * 60)
    logger.info("ECB Metadata Bootstrap")
    logger.info("=" * 60)
    logger.info(f"Cache directory: {cache.cache_dir}")
    logger.info(f"Mode: {'Full' if full else 'Priority datasets only'}")
    logger.info("=" * 60)

    async with ECBConnector() as connector:
        # 1. Fetch dataflows
        dataflows = await bootstrap_dataflows(connector, cache)
        if not dataflows:
            logger.error("No dataflows fetched. Aborting.")
            return

        # 2. Fetch structures
        structures_cached = await bootstrap_structures(
            connector, cache, dataflows, priority_only=not full
        )

        # 3. Fetch codelists
        codelists_cached = await bootstrap_codelists(connector, cache, full=full)

    # Summary
    logger.info("=" * 60)
    logger.info("Bootstrap complete!")
    logger.info("=" * 60)
    status = cache.get_cache_status()
    logger.info(f"Dataflows: {status['dataflows']['count']}")
    logger.info(f"Structures: {status['structures']['count']}")
    logger.info(f"Codelists: {status['codelists']['count']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap ECB metadata cache")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Cache all structures and codelists (slower)",
    )
    args = parser.parse_args()

    asyncio.run(main(full=args.full))
