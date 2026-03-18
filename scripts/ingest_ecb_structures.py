#!/usr/bin/env python3
"""Ingest ECB SDMX structure definitions for all active datasets.

Fetches the full SDMX data structure for each ECB dataset (dimensions, codelists,
attributes) and saves the parsed information as JSON for use in the catalog.

Output:
    catalog/ecb/structures/{DATASET_ID}.json   — per-dataset structure
    catalog/ecb/errors/{DATASET_ID}.json       — error detail when fetch fails
    catalog/ecb/catalog_base.json              — summary of all datasets

Usage:
    uv run python scripts/ingest_ecb_structures.py
    uv run python scripts/ingest_ecb_structures.py --dataset EXR
    uv run python scripts/ingest_ecb_structures.py --force
"""

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
STRUCTURES_DIR = REPO_ROOT / "catalog" / "ecb" / "structures"
ERRORS_DIR = REPO_ROOT / "catalog" / "ecb" / "errors"
CATALOG_BASE_PATH = REPO_ROOT / "catalog" / "ecb" / "catalog_base.json"

# ─── ECB API ──────────────────────────────────────────────────────────────────
ECB_BASE = "https://data-api.ecb.europa.eu/service"
SDMX_STRUCTURE_HEADERS = {
    "Accept": "application/vnd.sdmx.structure+xml;version=2.1",
}

# SDMX XML namespaces
SDMX_NS = {
    "mes": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}

# ─── Active datasets ──────────────────────────────────────────────────────────
ACTIVE_DATASETS = [
    "AGR", "AME", "BKN", "BLS", "BNT", "BPS", "BSI", "BSP", "CAR", "CBD2",
    "CCP", "CES", "CISS", "CLIFS", "CSEC", "DWA", "E09", "E11", "ECS", "EDP",
    "EST", "EWT", "EXR", "FM", "FVC", "FXI", "GFS", "HICP", "ICB", "ICO",
    "ICP", "IDCM", "IDCS", "IESS", "ILM", "INW", "IRS", "IVF", "JVS", "LCI",
    "LFSI", "LIG", "MFI", "MIR", "MMSR", "MNA", "MPD", "NEC", "OFI", "OMO",
    "PAY", "PCN", "PCP", "PCT", "PDD", "PEM", "PFBM", "PFBR", "PIS", "PLB",
    "PMC", "PPC", "PSN", "PST", "PTN", "PTT", "QSA", "RAI", "RAS", "RDE",
    "RDF", "RESC", "RESH", "RESR", "RESV", "RTD", "SAFE", "SEE", "SESFOD",
    "SHSS", "SPF", "SSI", "SSP", "SST", "STBS", "STP", "STS", "SUP", "SUR",
    "TGB", "TRD", "WTS", "YC",
]

# ─── Config ───────────────────────────────────────────────────────────────────
REQUEST_DELAY_S = 0.5
REQUEST_TIMEOUT_S = 30.0
CACHE_VALID_DAYS = 7


# ─── Cache helpers ────────────────────────────────────────────────────────────

def is_cache_valid(path: Path) -> bool:
    """Return True if path exists and was modified less than CACHE_VALID_DAYS ago."""
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(tz=timezone.utc) - mtime) < timedelta(days=CACHE_VALID_DAYS)


# ─── Fetch ────────────────────────────────────────────────────────────────────

def resolve_structure_id(client: httpx.Client, dataset_id: str) -> str:
    """Resolve the SDMX structure ID for a dataset via the dataflow endpoint.

    ECB dataflow IDs are not always the same as structure IDs:
      EXR  → ECB_EXR1
      AGR  → ECB_BCS1
      HICP → ECB_ICP3

    Returns the structure ID string (e.g. "ECB_EXR1").
    """
    url = f"{ECB_BASE}/dataflow/ECB/{dataset_id}"
    response = client.get(url, headers=SDMX_STRUCTURE_HEADERS, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ref = root.find(".//str:Structure/Ref", SDMX_NS)
    if ref is None:
        raise ValueError(f"No Structure/Ref found in dataflow response for {dataset_id}")
    structure_id = ref.get("id", "")
    if not structure_id:
        raise ValueError(f"Empty structure id in dataflow response for {dataset_id}")
    return structure_id


def fetch_structure_xml(client: httpx.Client, structure_id: str) -> str:
    """Fetch the full SDMX structure XML for a structure ID (includes inline codelists)."""
    url = f"{ECB_BASE}/datastructure/ECB/{structure_id}"
    params = {"references": "all", "detail": "full"}
    response = client.get(
        url,
        params=params,
        headers=SDMX_STRUCTURE_HEADERS,
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    return response.text


# ─── Parse ────────────────────────────────────────────────────────────────────

def parse_structure_xml(xml_text: str, dataset_id: str, structure_id: str = "") -> dict[str, Any]:
    """Parse SDMX structure XML and return a structured catalog entry.

    Extracts:
    - Dimensions in position order, each with human-readable name and valid codes
    - Attributes with assignment status
    - Example series key pattern (DIM1.DIM2.DIM3...)
    """
    root = ET.fromstring(xml_text)

    # 1. Build concept-id → human name map from ConceptSchemes
    concept_names: dict[str, str] = {}
    for concept_elem in root.findall(".//str:Concept", SDMX_NS):
        concept_id = concept_elem.get("id", "")
        name_elem = concept_elem.find("com:Name", SDMX_NS)
        if concept_id and name_elem is not None and name_elem.text:
            concept_names[concept_id] = name_elem.text

    # 2. Build codelist-id → {code → description} map from inline Codelists
    codelists: dict[str, dict[str, str]] = {}
    for cl_elem in root.findall(".//str:Codelist", SDMX_NS):
        cl_id = cl_elem.get("id", "")
        if not cl_id:
            continue
        codes: dict[str, str] = {}
        for code_elem in cl_elem.findall("str:Code", SDMX_NS):
            code_id = code_elem.get("id", "")
            name_elem = code_elem.find("com:Name", SDMX_NS)
            if code_id:
                codes[code_id] = (
                    name_elem.text if name_elem is not None and name_elem.text else code_id
                )
        if codes:
            codelists[cl_id] = codes

    # 3. Locate the DataStructure element
    ds_elem = root.find(".//str:DataStructure", SDMX_NS)
    if ds_elem is None:
        raise ValueError(f"No DataStructure element found in response for {dataset_id}")

    # 4. Parse dimensions
    dimensions: list[dict[str, Any]] = []
    dim_list = ds_elem.find(
        ".//str:DataStructureComponents/str:DimensionList", SDMX_NS
    )
    if dim_list is not None:
        for dim_elem in dim_list.findall("str:Dimension", SDMX_NS):
            dim_id = dim_elem.get("id", "")
            position = int(dim_elem.get("position", 0))

            # Resolve human name via ConceptIdentity reference
            concept_ref = dim_elem.find(".//str:ConceptIdentity/Ref", SDMX_NS)
            concept_id = concept_ref.get("id", dim_id) if concept_ref is not None else dim_id
            dim_name = concept_names.get(concept_id, concept_id)

            # Resolve codelist reference
            enum_ref = dim_elem.find(
                ".//str:LocalRepresentation/str:Enumeration/Ref", SDMX_NS
            )
            codelist_id = enum_ref.get("id", "") if enum_ref is not None else ""

            dimensions.append({
                "position": position,
                "id": dim_id,
                "name": dim_name,
                "codelist_id": codelist_id,
                "codes": codelists.get(codelist_id, {}),
            })

    dimensions.sort(key=lambda d: d["position"])

    # 5. Parse attributes
    attributes: list[dict[str, str]] = []
    attr_list = ds_elem.find(
        ".//str:DataStructureComponents/str:AttributeList", SDMX_NS
    )
    if attr_list is not None:
        for attr_elem in attr_list.findall("str:Attribute", SDMX_NS):
            attr_id = attr_elem.get("id", "")
            assignment = attr_elem.get("assignmentStatus", "")

            concept_ref = attr_elem.find(".//str:ConceptIdentity/Ref", SDMX_NS)
            concept_id = concept_ref.get("id", attr_id) if concept_ref is not None else attr_id
            attr_name = concept_names.get(concept_id, concept_id)

            attributes.append({
                "id": attr_id,
                "name": attr_name,
                "assignment": assignment,
            })

    # 6. Build example key pattern
    example_key_pattern = ".".join(d["id"] for d in dimensions)
    total_codes = sum(len(d["codes"]) for d in dimensions)

    return {
        "dataset_id": dataset_id,
        "structure_id": structure_id,
        "fetched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dimensions": dimensions,
        "attributes": attributes,
        "example_key_pattern": example_key_pattern,
        "notes": "",
        "_stats": {
            "n_dimensions": len(dimensions),
            "n_attributes": len(attributes),
            "total_codes": total_codes,
        },
    }


# ─── Per-dataset processing ───────────────────────────────────────────────────

def process_dataset(
    client: httpx.Client,
    dataset_id: str,
    index: int,
    total: int,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch, parse, and persist structure for one dataset.

    Returns a summary dict for catalog_base.json.
    """
    out_path = STRUCTURES_DIR / f"{dataset_id}.json"
    err_path = ERRORS_DIR / f"{dataset_id}.json"
    prefix = f"[{index:>{len(str(total))}}/{total}] {dataset_id:<8}"

    # Serve from cache when fresh enough
    if not force and is_cache_valid(out_path):
        with open(out_path, encoding="utf-8") as f:
            cached = json.load(f)
        stats = cached.get("_stats", {})
        n_dims = stats.get("n_dimensions", "?")
        n_codes = stats.get("total_codes", "?")
        print(f"{prefix} → CACHED ({n_dims} dimensions, {n_codes} codes)")
        return {
            "dataset_id": dataset_id,
            "status": "cached",
            "n_dimensions": n_dims,
            "total_codes": n_codes,
        }

    try:
        structure_id = resolve_structure_id(client, dataset_id)
        time.sleep(REQUEST_DELAY_S)
        xml_text = fetch_structure_xml(client, structure_id)
        structure = parse_structure_xml(xml_text, dataset_id, structure_id)

        STRUCTURES_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

        # Remove stale error file if it exists
        if err_path.exists():
            err_path.unlink()

        stats = structure["_stats"]
        print(
            f"{prefix} → OK "
            f"({stats['n_dimensions']} dimensions, {stats['total_codes']} codes)"
        )
        return {
            "dataset_id": dataset_id,
            "structure_id": structure_id,
            "status": "ok",
            "n_dimensions": stats["n_dimensions"],
            "n_attributes": stats["n_attributes"],
            "total_codes": stats["total_codes"],
        }

    except Exception as exc:
        error_info = {
            "dataset_id": dataset_id,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "failed_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        ERRORS_DIR.mkdir(parents=True, exist_ok=True)
        with open(err_path, "w", encoding="utf-8") as f:
            json.dump(error_info, f, indent=2)

        print(f"{prefix} → ERROR ({type(exc).__name__}: {exc})")
        return {
            "dataset_id": dataset_id,
            "status": "error",
            "error": str(exc),
        }


# ─── Catalog summary ──────────────────────────────────────────────────────────

def save_catalog_base(results: list[dict[str, Any]]) -> None:
    """Persist catalog_base.json with the run summary."""
    ok_count = sum(1 for r in results if r["status"] in ("ok", "cached"))
    err_count = sum(1 for r in results if r["status"] == "error")

    catalog = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_datasets": len(results),
        "successful": ok_count,
        "failed": err_count,
        "datasets": results,
    }

    CATALOG_BASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_BASE_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest ECB SDMX structure definitions into catalog/ecb/structures/"
    )
    parser.add_argument(
        "--dataset",
        metavar="ID",
        help="Process a single dataset only (e.g. --dataset EXR)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=f"Re-fetch even if cached file is less than {CACHE_VALID_DAYS} days old",
    )
    args = parser.parse_args()

    datasets = [args.dataset.upper()] if args.dataset else ACTIVE_DATASETS
    total = len(datasets)

    print("=" * 60)
    print(f"ECB Structure Ingestion  —  {total} dataset(s)")
    print(f"Output: {STRUCTURES_DIR}")
    print("=" * 60)

    t_start = time.monotonic()
    results: list[dict[str, Any]] = []

    with httpx.Client() as client:
        for i, dataset_id in enumerate(datasets, start=1):
            result = process_dataset(client, dataset_id, i, total, force=args.force)
            results.append(result)
            if i < total:
                time.sleep(REQUEST_DELAY_S)

    save_catalog_base(results)

    elapsed = time.monotonic() - t_start
    ok_count = sum(1 for r in results if r["status"] in ("ok", "cached"))
    err_count = sum(1 for r in results if r["status"] == "error")

    print("=" * 60)
    print(f"Done in {elapsed:.1f}s  |  OK: {ok_count}  |  Errors: {err_count}")
    print(f"Structures : {STRUCTURES_DIR}")
    print(f"Catalog    : {CATALOG_BASE_PATH}")
    print("=" * 60)

    if err_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
