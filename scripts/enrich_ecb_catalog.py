#!/usr/bin/env python3
"""Enrich ECB dataset catalog with semantic metadata using Claude.

Reads SDMX structure files from catalog/ecb/structures/, calls the Claude API
to generate human-readable descriptions, concept keywords, and example use cases,
then saves the enriched metadata for use by the MCP natural language routing.

Output:
    catalog/ecb/enriched/{ID}.json      — per-dataset enriched metadata
    catalog/ecb/catalog_enriched.json   — consolidated runtime catalog

Usage:
    uv run python scripts/enrich_ecb_catalog.py
    uv run python scripts/enrich_ecb_catalog.py --dataset MNA ICP EXR GFS BLS
    uv run python scripts/enrich_ecb_catalog.py --force
"""

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import httpx

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
STRUCTURES_DIR = REPO_ROOT / "catalog" / "ecb" / "structures"
ENRICHED_DIR = REPO_ROOT / "catalog" / "ecb" / "enriched"
CATALOG_ENRICHED_PATH = REPO_ROOT / "catalog" / "ecb" / "catalog_enriched.json"

# ─── Model config ─────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1000
TEMPERATURE = 0

# ─── Rate limiting & retries ──────────────────────────────────────────────────
REQUEST_DELAY_S = 1.0
MAX_RETRIES = 3

# ─── Pricing (Sonnet 4, per token) ────────────────────────────────────────────
INPUT_COST_PER_TOKEN = 0.000003   # $3 / 1M tokens
OUTPUT_COST_PER_TOKEN = 0.000015  # $15 / 1M tokens

# ─── ECB API ──────────────────────────────────────────────────────────────────
ECB_BASE = "https://data-api.ecb.europa.eu/service"
SDMX_NS = {
    "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}


# ─── Dataflow name lookup ─────────────────────────────────────────────────────

def fetch_dataflow_names() -> dict[str, str]:
    """Fetch all ECB dataflow names in a single request.

    Returns dict mapping dataset_id → human-readable name.
    """
    url = f"{ECB_BASE}/dataflow/ECB"
    headers = {"Accept": "application/vnd.sdmx.structure+xml;version=2.1"}
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        names = {}
        for df in root.findall(".//str:Dataflow", SDMX_NS):
            df_id = df.get("id", "")
            name_elem = df.find("com:Name", SDMX_NS)
            name = name_elem.text if name_elem is not None and name_elem.text else df_id
            if df_id:
                names[df_id] = name
        return names
    except Exception as exc:
        print(f"Warning: could not fetch dataflow names ({exc}). Using dataset IDs as names.")
        return {}


# ─── Prompt building ──────────────────────────────────────────────────────────

def build_dimensions_summary(dimensions: list[dict]) -> str:
    """Build a readable dimensions string for the enrichment prompt.

    Appends example codes for small codelists (≤20 values) to give Claude
    enough context to generate accurate concepts.
    """
    parts = []
    for dim in dimensions:
        codes = dim.get("codes", {})
        if codes and len(codes) <= 20:
            examples = ", ".join(
                f"{k}={v}" for k, v in list(codes.items())[:10]
            )
            parts.append(f"{dim['id']} ({dim['name']}): {examples}")
        else:
            parts.append(f"{dim['id']} ({dim['name']})")
    return "; ".join(parts)


ENRICHMENT_PROMPT = """\
You are an expert economist specialising in European statistics and central bank data. \
Analyse this ECB dataset and generate semantic metadata to enable natural language discovery.

Dataset:
* ID: {id}
* Name: {name}
* Technical description: {description}
* Dimensions: {dimensions_summary}
* Number of series: {n_series}

Respond ONLY with valid JSON (no markdown, no backticks, no explanation) containing exactly these fields:
{{
  "description_short": "1-2 sentences in plain English for an economist. No statistical jargon. Focus on what questions this data answers.",
  "concepts": ["12-20 keywords an analyst would use to search for this data. Mix of specific terms, acronyms, and plain language variants."],
  "use_cases": ["4-6 concrete questions in English that this dataset can answer. Write them as a user would ask them."],
  "primary_frequency": "Most common frequency in this dataset: A, Q, M, D, or MIXED",
  "geographic_coverage": "One of: euro_area_only, euro_area_and_countries, eu_wide, global"
}}

Rules for concepts:
* Always include both the acronym and the full form when one exists (GDP and gross domestic product, HICP and harmonised index of consumer prices)
* Think about how a junior analyst would ask a senior colleague for this data in a chat message
* Include domain-specific terms that appear in the dimensions or description
* Do not include the dataset name, ID, or the word ECB as concepts\
"""


def build_prompt(
    dataset_id: str,
    name: str,
    dimensions_summary: str,
    n_series: int,
) -> str:
    description = name if name != dataset_id else f"ECB dataset with dimensions: {dimensions_summary}"
    return ENRICHMENT_PROMPT.format(
        id=dataset_id,
        name=name,
        description=description,
        dimensions_summary=dimensions_summary,
        n_series=n_series,
    )


# ─── Claude call with retry ───────────────────────────────────────────────────

def call_claude_with_retry(
    client: anthropic.Anthropic,
    prompt: str,
) -> tuple[dict[str, Any], int, int]:
    """Call Claude and parse the JSON response, retrying on parse failure.

    On each retry the parse error is appended to the conversation so Claude
    can self-correct.

    Returns:
        (parsed_dict, input_tokens, output_tokens)

    Raises:
        ValueError if all MAX_RETRIES attempts fail.
    """
    messages: list[dict] = [{"role": "user", "content": prompt}]
    last_error = ""
    total_input = 0
    total_output = 0

    for attempt in range(MAX_RETRIES):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            messages=messages,
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        text = next((b.text for b in response.content if b.type == "text"), "")

        # Strip accidental markdown fencing
        cleaned = text.strip()
        if cleaned.startswith("```"):
            inner = cleaned.split("```", 2)
            cleaned = inner[2] if len(inner) > 2 else inner[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            result = json.loads(cleaned)
            return result, total_input, total_output
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES - 1:
                messages.append({"role": "assistant", "content": text})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your response was not valid JSON. Parse error: {last_error}\n\n"
                        "Please respond again with ONLY valid JSON, no markdown, no backticks."
                    ),
                })
                time.sleep(REQUEST_DELAY_S)

    raise ValueError(f"Invalid JSON after {MAX_RETRIES} attempts. Last error: {last_error}")


# ─── Per-dataset processing ───────────────────────────────────────────────────

def process_dataset(
    client: anthropic.Anthropic,
    dataset_id: str,
    dataflow_names: dict[str, str],
    index: int,
    total: int,
    force: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Enrich a single dataset and persist the result.

    Returns a summary dict for the run report.
    """
    structure_path = STRUCTURES_DIR / f"{dataset_id}.json"
    out_path = ENRICHED_DIR / f"{dataset_id}.json"
    prefix = f"[{index:>{len(str(total))}}/{total}] {dataset_id:<8}"

    # Missing structure file → can't enrich
    if not structure_path.exists():
        print(f"{prefix} → SKIP (no structure file — dataset may not exist in ECB API)")
        return {"dataset_id": dataset_id, "status": "skipped_no_structure", "input_tokens": 0, "output_tokens": 0}

    # Already enriched and cache is valid
    if not force and out_path.exists():
        print(f"{prefix} → SKIPPED (already enriched)")
        return {"dataset_id": dataset_id, "status": "skipped", "input_tokens": 0, "output_tokens": 0}

    # Load structure
    with open(structure_path, encoding="utf-8") as f:
        structure = json.load(f)

    dimensions = structure.get("dimensions", [])
    stats = structure.get("_stats", {})
    n_series = stats.get("total_codes", 0)
    name = dataflow_names.get(dataset_id, dataset_id)
    dimensions_summary = build_dimensions_summary(dimensions)

    prompt = build_prompt(dataset_id, name, dimensions_summary, n_series)

    try:
        enriched, input_tokens, output_tokens = call_claude_with_retry(client, prompt)

        result = {
            "id": dataset_id,
            "name": name,
            "status": "active",
            "n_series": n_series,
            "description_original": name,
            "description_short": enriched.get("description_short", ""),
            "concepts": enriched.get("concepts", []),
            "use_cases": enriched.get("use_cases", []),
            "primary_frequency": enriched.get("primary_frequency", "MIXED"),
            "geographic_coverage": enriched.get("geographic_coverage", "euro_area_and_countries"),
            "key_dimensions": [d["id"] for d in dimensions],
            "enriched_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        total_tokens = input_tokens + output_tokens
        print(f"{prefix} → OK ({total_tokens} tokens)")

        if verbose:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print()

        return {
            "dataset_id": dataset_id,
            "status": "ok",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    except Exception as exc:
        print(f"{prefix} → ERROR ({exc})")
        return {
            "dataset_id": dataset_id,
            "status": "error",
            "error": str(exc),
            "input_tokens": 0,
            "output_tokens": 0,
        }


# ─── Catalog consolidation ────────────────────────────────────────────────────

def consolidate_catalog() -> int:
    """Read all enriched files and write catalog_enriched.json.

    Returns the number of datasets included.
    """
    datasets = []
    for path in sorted(ENRICHED_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            datasets.append(json.load(f))

    catalog = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ecb_api_base": "https://data-api.ecb.europa.eu/service",
        "total_datasets": len(datasets),
        "datasets": datasets,
    }

    with open(CATALOG_ENRICHED_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    size_kb = CATALOG_ENRICHED_PATH.stat().st_size / 1024
    print(f"catalog_enriched.json → {len(datasets)} datasets, {size_kb:.1f} KB")
    return len(datasets)


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich ECB dataset catalog with semantic metadata via Claude API"
    )
    parser.add_argument(
        "--dataset",
        nargs="+",
        metavar="ID",
        help="Enrich specific datasets only (space-separated, e.g. --dataset MNA ICP EXR)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-enrich even if enriched file already exists",
    )
    args = parser.parse_args()

    # Determine target datasets
    if args.dataset:
        target_ids = [d.upper() for d in args.dataset]
        verbose = True  # Print full JSON when running a targeted subset
    else:
        target_ids = sorted(p.stem for p in STRUCTURES_DIR.glob("*.json"))
        verbose = False

    total = len(target_ids)

    print("=" * 60)
    print(f"ECB Catalog Enrichment  —  {total} dataset(s)  —  {MODEL}")
    print("=" * 60)

    print("Fetching dataflow names from ECB API...")
    dataflow_names = fetch_dataflow_names()
    print(f"  {len(dataflow_names)} names loaded")
    print()

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    t_start = time.monotonic()
    results: list[dict[str, Any]] = []

    for i, dataset_id in enumerate(target_ids, start=1):
        result = process_dataset(
            client, dataset_id, dataflow_names, i, total,
            force=args.force, verbose=verbose,
        )
        results.append(result)
        # Rate limit between API calls (skip after last)
        if i < total and result["status"] not in ("skipped", "skipped_no_structure"):
            time.sleep(REQUEST_DELAY_S)

    # Consolidate catalog
    print()
    consolidate_catalog()

    # Summary
    elapsed = time.monotonic() - t_start
    ok = [r for r in results if r["status"] == "ok"]
    skipped = [r for r in results if r["status"].startswith("skipped")]
    errors = [r for r in results if r["status"] == "error"]

    total_input = sum(r.get("input_tokens", 0) for r in results)
    total_output = sum(r.get("output_tokens", 0) for r in results)
    cost = total_input * INPUT_COST_PER_TOKEN + total_output * OUTPUT_COST_PER_TOKEN

    print("=" * 60)
    print(f"Done in {elapsed:.1f}s")
    print(f"  Processed : {len(ok)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Errors    : {len(errors)}")
    print(f"  Tokens    : {total_input:,} in / {total_output:,} out")
    print(f"  Est. cost : ${cost:.4f}")
    print(f"  Output    : {ENRICHED_DIR}")
    print("=" * 60)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
