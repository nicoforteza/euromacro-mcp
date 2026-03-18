"""Natural language interaction tests for EuroData MCP.

These tests simulate how an AI agent or end user interacts with the MCP
via natural language queries — from vague questions to precise requests.
Each test follows the realistic multi-step flow:
  1. search_series / explore_datasets  → discover what exists
  2. explore_dimensions                → understand dataset structure
  3. explore_codes                     → find valid values
  4. build_series                      → assemble the series key
  5. describe_series / get_series      → retrieve metadata or data

No network calls are made — all assertions are against the shipped catalog.
"""
from __future__ import annotations

import pytest

from eurodata_mcp.tools.series import search_series
from eurodata_mcp.tools.explore import (
    build_series,
    explore_codes,
    explore_datasets,
    explore_dimensions,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _ids(results: list[dict]) -> list[str]:
    """Extract dataset or series IDs from a result list."""
    return [r.get("id", "") for r in results]


# =============================================================================
# SCENARIO 1 — "What is the EUR/USD exchange rate?"
# =============================================================================

class TestExchangeRateFlow:
    """User asks for euro/dollar exchange rate data."""

    @pytest.mark.asyncio
    async def test_search_finds_exchange_rate_dataset(self):
        # explore_datasets is the right tool when looking for a dataset by topic
        result = await explore_datasets("ecb", query="exchange rate")
        ids = _ids(result["datasets"])
        assert "EXR" in ids, f"EXR missing from: {ids}"

    @pytest.mark.asyncio
    async def test_explore_datasets_exchange(self):
        result = await explore_datasets("ecb", query="exchange rate")
        ids = _ids(result["datasets"])
        assert "EXR" in ids

    @pytest.mark.asyncio
    async def test_exr_dimensions_match_expected_format(self):
        result = await explore_dimensions("ecb", "EXR")
        assert result["series_key_format"] == "<FREQ>.<CURRENCY>.<CURRENCY_DENOM>.<EXR_TYPE>.<EXR_SUFFIX>"

    @pytest.mark.asyncio
    async def test_exr_currency_codes_include_usd_gbp_jpy(self):
        # 369 currencies — need limit > 50 to cover U/G/J range alphabetically
        result = await explore_codes("ecb", "EXR", "CURRENCY", limit=400)
        codes = {c["code"] for c in result["codes"]}
        assert "USD" in codes
        assert "GBP" in codes
        assert "JPY" in codes

    @pytest.mark.asyncio
    async def test_build_eurusd_monthly_series_key(self):
        result = await build_series(
            "ecb", "EXR",
            {"FREQ": "M", "CURRENCY": "USD", "CURRENCY_DENOM": "EUR",
             "EXR_TYPE": "SP00", "EXR_SUFFIX": "A"},
        )
        assert result["series_key"] == "M.USD.EUR.SP00.A"
        assert "EXR/M.USD.EUR.SP00.A" in result["data_url"]

    @pytest.mark.asyncio
    async def test_build_eurgbp_daily_series_key(self):
        result = await build_series(
            "ecb", "EXR",
            {"FREQ": "D", "CURRENCY": "GBP", "CURRENCY_DENOM": "EUR",
             "EXR_TYPE": "SP00", "EXR_SUFFIX": "A"},
        )
        assert result["series_key"] == "D.GBP.EUR.SP00.A"


# =============================================================================
# SCENARIO 2 — "Show me euro area inflation"
# =============================================================================

class TestInflationFlow:
    """User asks for HICP inflation data."""

    @pytest.mark.asyncio
    async def test_search_inflation_returns_curated_series(self):
        results = await search_series("euro area inflation")
        ids = _ids(results)
        assert any("hicp" in i.lower() for i in ids), f"No HICP in {ids}"

    @pytest.mark.asyncio
    async def test_search_core_inflation(self):
        results = await search_series("core inflation excluding energy food")
        ids = _ids(results)
        assert any("core" in i.lower() or "hicp" in i.lower() for i in ids)

    @pytest.mark.asyncio
    async def test_explore_datasets_inflation(self):
        result = await explore_datasets("ecb", query="inflation")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["HICP", "ICP"])

    @pytest.mark.asyncio
    async def test_hicp_dimensions_include_ref_area(self):
        result = await explore_dimensions("ecb", "HICP")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "REF_AREA" in dim_ids
        assert "FREQ" in dim_ids

    @pytest.mark.asyncio
    async def test_hicp_ref_area_includes_euro_area(self):
        result = await explore_codes("ecb", "HICP", "REF_AREA", query="euro")
        # Should find at least one euro area code
        assert len(result["codes"]) > 0

    @pytest.mark.asyncio
    async def test_build_hicp_headline_euro_area(self):
        # First, get dimension order
        dims = await explore_dimensions("ecb", "HICP")
        dim_ids = [d["id"] for d in dims["dimensions"]]
        assert "FREQ" in dim_ids
        assert "REF_AREA" in dim_ids

        result = await build_series(
            "ecb", "HICP",
            {"FREQ": "M", "REF_AREA": "U2"},
        )
        assert "HICP" in result["data_url"]
        assert result["series_key"].startswith("M.")


# =============================================================================
# SCENARIO 3 — "Interest rates in the euro area"
# =============================================================================

class TestInterestRatesFlow:
    """User asks about ECB policy rates and money market rates."""

    @pytest.mark.asyncio
    async def test_search_interest_rates(self):
        results = await search_series("ECB interest rate")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_euribor(self):
        results = await search_series("euribor 3 month")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_explore_datasets_interest_rates(self):
        result = await explore_datasets("ecb", query="interest rate")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["IRS", "MIR", "FM", "EST"])

    @pytest.mark.asyncio
    async def test_irs_dataset_exists_and_has_dimensions(self):
        result = await explore_dimensions("ecb", "IRS")
        assert "dimensions" in result
        assert len(result["dimensions"]) > 0
        assert "series_key_format" in result

    @pytest.mark.asyncio
    async def test_fm_financial_markets_dimensions(self):
        result = await explore_dimensions("ecb", "FM")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "FREQ" in dim_ids

    @pytest.mark.asyncio
    async def test_build_estr_daily_series(self):
        """€STR overnight rate — daily, reference area U2."""
        result = await build_series(
            "ecb", "EST",
            {"FREQ": "D"},
        )
        assert result["series_key"].startswith("D")
        assert "EST" in result["data_url"]


# =============================================================================
# SCENARIO 4 — "Bank lending to businesses in Spain"
# =============================================================================

class TestBankLendingFlow:
    """User asks about credit and lending conditions."""

    @pytest.mark.asyncio
    async def test_search_bank_lending(self):
        results = await search_series("bank lending corporations credit")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_loans_non_financial_corporations(self):
        results = await search_series("loans non-financial corporations euro area")
        ids = _ids(results)
        assert any("loan" in i.lower() or "nfc" in i.lower() for i in ids)

    @pytest.mark.asyncio
    async def test_explore_bls_dataset(self):
        """Bank Lending Survey — qualitative credit conditions."""
        result = await explore_dimensions("ecb", "BLS")
        assert "dimensions" in result
        assert len(result["dimensions"]) > 0

    @pytest.mark.asyncio
    async def test_bls_codes_for_a_dimension(self):
        dims = await explore_dimensions("ecb", "BLS")
        first_dim = dims["dimensions"][0]["id"]
        result = await explore_codes("ecb", "BLS", first_dim)
        assert "codes" in result
        assert len(result["codes"]) > 0

    @pytest.mark.asyncio
    async def test_mir_interest_rates_on_loans(self):
        """MIR: MFI interest rates on new business loans."""
        result = await explore_dimensions("ecb", "MIR")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "FREQ" in dim_ids
        assert "REF_AREA" in dim_ids

    @pytest.mark.asyncio
    async def test_build_mir_loans_series(self):
        result = await build_series(
            "ecb", "MIR",
            {"FREQ": "M", "REF_AREA": "ES"},  # Spain
        )
        assert "MIR" in result["data_url"]
        assert "ES" in result["series_key"]


# =============================================================================
# SCENARIO 5 — "Real estate prices in Germany"
# =============================================================================

class TestRealEstateFlow:
    """User asks about residential property prices."""

    @pytest.mark.asyncio
    async def test_search_property_prices(self):
        # explore_datasets is the right entry point for dataset discovery by topic
        result = await explore_datasets("ecb", query="residential")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["RPP", "RPV", "RDE", "RDF"])

    @pytest.mark.asyncio
    async def test_explore_datasets_real_estate(self):
        result = await explore_datasets("ecb", query="residential property")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["RPP", "RPV", "RDE", "RDF"])

    @pytest.mark.asyncio
    async def test_rpp_dimensions(self):
        result = await explore_dimensions("ecb", "RPP")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "FREQ" in dim_ids
        assert "REF_AREA" in dim_ids

    @pytest.mark.asyncio
    async def test_build_german_property_prices(self):
        result = await build_series(
            "ecb", "RPP",
            {"FREQ": "Q", "REF_AREA": "DE"},  # Germany, quarterly
        )
        assert "RPP" in result["data_url"]
        assert "DE" in result["series_key"]


# =============================================================================
# SCENARIO 6 — "Balance of payments / current account"
# =============================================================================

class TestBalanceOfPaymentsFlow:
    """User asks about current account and balance of payments."""

    @pytest.mark.asyncio
    async def test_search_balance_of_payments(self):
        results = await search_series("balance of payments current account")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_explore_bop_dataset(self):
        result = await explore_datasets("ecb", query="balance of payments")
        ids = _ids(result["datasets"])
        assert "BOP" in ids

    @pytest.mark.asyncio
    async def test_bop_dimensions_available(self):
        result = await explore_dimensions("ecb", "BOP")
        assert len(result["dimensions"]) > 0
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_bop_freq_codes(self):
        result = await explore_codes("ecb", "BOP", "FREQ")
        codes = {c["code"] for c in result["codes"]}
        assert "Q" in codes or "M" in codes


# =============================================================================
# SCENARIO 7 — "Money supply M3"
# =============================================================================

class TestMoneySupplyFlow:
    """User asks about monetary aggregates."""

    @pytest.mark.asyncio
    async def test_search_m3_money_supply(self):
        results = await search_series("M3 money supply")
        ids = _ids(results)
        assert any("m3" in i.lower() for i in ids)

    @pytest.mark.asyncio
    async def test_search_broad_money(self):
        results = await search_series("broad money monetary aggregate euro area")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_explore_datasets_bsi_money(self):
        # "balance sheet" is in BSI/BSP name; query must be a substring of name/id/concepts
        result = await explore_datasets("ecb", query="balance sheet")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["BSI", "BSP", "ILM"])

    @pytest.mark.asyncio
    async def test_bsi_dimensions(self):
        result = await explore_dimensions("ecb", "BSI")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "FREQ" in dim_ids

    @pytest.mark.asyncio
    async def test_build_m3_series(self):
        result = await build_series(
            "ecb", "BSI",
            {"FREQ": "M", "REF_AREA": "U2"},
        )
        assert "BSI" in result["data_url"]


# =============================================================================
# SCENARIO 8 — "Yield curve for euro area government bonds"
# =============================================================================

class TestYieldCurveFlow:
    """User asks about sovereign bond yields and term structure."""

    @pytest.mark.asyncio
    async def test_search_yield_curve(self):
        results = await search_series("yield curve government bonds")
        ids = _ids(results)
        assert any(x in ids for x in ["YC", "IRS", "FM"])

    @pytest.mark.asyncio
    async def test_explore_yc_dataset(self):
        result = await explore_datasets("ecb", query="yield curve")
        ids = _ids(result["datasets"])
        assert "YC" in ids

    @pytest.mark.asyncio
    async def test_yc_dimensions(self):
        result = await explore_dimensions("ecb", "YC")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "FREQ" in dim_ids

    @pytest.mark.asyncio
    async def test_yc_has_maturity_dimension(self):
        result = await explore_dimensions("ecb", "YC")
        dim_ids = [d["id"] for d in result["dimensions"]]
        # Yield curve must have a maturity or data type dimension
        assert any("MATURITY" in d or "DATA_TYPE" in d or "TENOR" in d
                   for d in dim_ids), f"No maturity-like dim in {dim_ids}"

    @pytest.mark.asyncio
    async def test_build_yc_daily_series(self):
        result = await build_series(
            "ecb", "YC",
            {"FREQ": "D"},
        )
        assert "YC" in result["data_url"]


# =============================================================================
# SCENARIO 9 — "Systemic stress / financial stability indicators"
# =============================================================================

class TestFinancialStressFlow:
    """User asks about financial stress and systemic risk indicators."""

    @pytest.mark.asyncio
    async def test_search_systemic_stress(self):
        results = await search_series("systemic stress financial stability")
        ids = _ids(results)
        assert any(x in ids for x in ["CISS", "CLIFS", "FM"])

    @pytest.mark.asyncio
    async def test_explore_ciss_dataset(self):
        result = await explore_datasets("ecb", query="systemic stress")
        ids = _ids(result["datasets"])
        assert "CISS" in ids

    @pytest.mark.asyncio
    async def test_ciss_dimensions(self):
        result = await explore_dimensions("ecb", "CISS")
        assert len(result["dimensions"]) > 0
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_clifs_country_level_stress(self):
        """CLIFS: Country-Level Index of Financial Stress."""
        result = await explore_dimensions("ecb", "CLIFS")
        assert len(result["dimensions"]) > 0

    @pytest.mark.asyncio
    async def test_build_ciss_weekly_series(self):
        result = await build_series("ecb", "CISS", {"FREQ": "W"})
        assert "CISS" in result["data_url"]


# =============================================================================
# SCENARIO 10 — "Survey data: professional forecasters, consumer expectations"
# =============================================================================

class TestSurveyDataFlow:
    """User asks about survey-based expectations data."""

    @pytest.mark.asyncio
    async def test_search_professional_forecasters(self):
        results = await search_series("survey professional forecasters expectations")
        ids = _ids(results)
        assert any(x in ids for x in ["SPF", "CES", "ECS", "BLS", "SAFE"])

    @pytest.mark.asyncio
    async def test_explore_spf_dataset(self):
        result = await explore_datasets("ecb", query="professional forecasters")
        ids = _ids(result["datasets"])
        assert "SPF" in ids

    @pytest.mark.asyncio
    async def test_spf_dimensions(self):
        result = await explore_dimensions("ecb", "SPF")
        assert len(result["dimensions"]) >= 4
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_search_consumer_expectations(self):
        # Dataset discovery via explore_datasets, not curated series search
        result = await explore_datasets("ecb", query="consumer")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["CES", "ECS"])

    @pytest.mark.asyncio
    async def test_ces_consumer_expectations_dimensions(self):
        result = await explore_dimensions("ecb", "CES")
        assert len(result["dimensions"]) > 0

    @pytest.mark.asyncio
    async def test_safe_access_to_finance_enterprises(self):
        """SAFE: Survey on Access to Finance of Enterprises."""
        result = await explore_dimensions("ecb", "SAFE")
        assert "dimensions" in result
        assert len(result["dimensions"]) > 0


# =============================================================================
# SCENARIO 11 — "Government debt and fiscal data"
# =============================================================================

class TestFiscalDataFlow:
    """User asks about government debt, deficits and fiscal sustainability."""

    @pytest.mark.asyncio
    async def test_search_government_debt(self):
        results = await search_series("government debt deficit fiscal")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_explore_datasets_fiscal(self):
        result = await explore_datasets("ecb", query="government debt")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["PDD", "GST", "AME"])

    @pytest.mark.asyncio
    async def test_pdd_public_debt_dimensions(self):
        result = await explore_dimensions("ecb", "PDD")
        dim_ids = [d["id"] for d in result["dimensions"]]
        assert "FREQ" in dim_ids
        assert "REF_AREA" in dim_ids

    @pytest.mark.asyncio
    async def test_build_debt_series_italy(self):
        result = await build_series(
            "ecb", "PDD",
            {"FREQ": "Q", "REF_AREA": "IT"},  # Italy
        )
        assert "PDD" in result["data_url"]
        assert "IT" in result["series_key"]


# =============================================================================
# SCENARIO 12 — Provider and catalog discovery
# =============================================================================

class TestCatalogDiscoveryFlow:
    """User explores what data is available without knowing dataset names."""

    @pytest.mark.asyncio
    async def test_list_all_ecb_datasets(self):
        # Default limit=20; pass limit=200 to get the full catalog
        result = await explore_datasets("ecb", limit=200)
        assert result["count"] >= 90
        assert result.get("source") == "catalog"

    @pytest.mark.asyncio
    async def test_filter_by_payments(self):
        result = await explore_datasets("ecb", query="payment")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["PAY", "PCT", "PLB", "PSS"])

    @pytest.mark.asyncio
    async def test_filter_by_securities(self):
        result = await explore_datasets("ecb", query="securities")
        ids = _ids(result["datasets"])
        assert len(ids) > 0

    @pytest.mark.asyncio
    async def test_filter_by_supervisory(self):
        result = await explore_datasets("ecb", query="supervisory")
        ids = _ids(result["datasets"])
        assert any(x in ids for x in ["SUP", "CAR", "KRI"])

    @pytest.mark.asyncio
    async def test_invalid_provider_returns_error(self):
        result = await explore_datasets("imf")  # not yet implemented
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_vague_query_returns_dataset_hints(self):
        """Vague query should surface dataset-level suggestions."""
        results = await search_series("agricultural statistics europe")
        dataset_hits = [r for r in results if r.get("type") == "dataset"]
        assert len(dataset_hits) > 0
        ids = _ids(dataset_hits)
        assert "AGR" in ids

    @pytest.mark.asyncio
    async def test_codes_search_filter(self):
        """User searches for a specific currency within a codelist."""
        result = await explore_codes("ecb", "EXR", "CURRENCY", query="swiss")
        assert len(result["codes"]) > 0
        assert any("CHF" in c["code"] or "swiss" in c["description"].lower()
                   for c in result["codes"])

    @pytest.mark.asyncio
    async def test_build_series_url_is_valid_ecb_api_url(self):
        result = await build_series(
            "ecb", "HICP",
            {"FREQ": "M", "REF_AREA": "U2"},
        )
        url = result["data_url"]
        assert url.startswith("https://data-api.ecb.europa.eu/service/data/")
        assert "format=jsondata" in url
