"""M2 Stage 1 — 事实模型、概念、单位、上下文测试。"""


import pandas as pd
import pytest

from ashare_research.exceptions import UnitConversionError
from ashare_research.facts.concepts import ConceptRegistry
from ashare_research.facts.contexts import (
    build_context_id,
    compute_period_dates,
    create_context,
    is_instant,
    parse_period_label,
)
from ashare_research.facts.mappings import ConceptMapping
from ashare_research.facts.models import (
    ConsolidationScope,
    Fact,
    FactContext,
    PeriodType,
    VerificationStatus,
)
from ashare_research.facts.units import UnitRegistry


class TestConceptRegistry:
    def test_get_known_concept(self):
        c = ConceptRegistry.get("revenue")
        assert c is not None
        assert c.display_name_zh == "营业收入"

    def test_get_unknown_concept(self):
        assert ConceptRegistry.get("nonexistent") is None

    def test_is_registered(self):
        assert ConceptRegistry.is_registered("net_profit")
        assert not ConceptRegistry.is_registered("fake_concept")

    def test_get_by_category(self):
        income = ConceptRegistry.get_by_category(
            __import__(
                "ashare_research.facts.models", fromlist=["ConceptCategory"]
            ).ConceptCategory.income_statement,
        )
        concept_ids = [c.concept_id for c in income]
        assert "revenue" in concept_ids
        assert "net_profit" in concept_ids

    def test_at_least_40_concepts(self):
        all_c = ConceptRegistry.list_all()
        assert len(all_c) >= 40

    def test_canonical_unit(self):
        assert ConceptRegistry.get_canonical_unit("revenue") == "CNY"
        assert ConceptRegistry.get_canonical_unit("basic_eps") == "CNY_PER_SHARE"

    def test_is_instant(self):
        assert ConceptRegistry.is_instant("total_assets")
        assert not ConceptRegistry.is_instant("revenue")


class TestUnitRegistry:
    def test_parse_unit(self):
        assert UnitRegistry.parse_unit("元") is not None
        assert UnitRegistry.parse_unit("亿元") is not None

    def test_validate_unit(self):
        assert UnitRegistry.validate_unit("CNY")
        assert not UnitRegistry.validate_unit("unknown_unit_xyz")

    def test_normalize_100m_to_cny(self):
        val, unit, rule = UnitRegistry.normalize_amount(12.5, "亿元")
        assert val == 1_250_000_000.0
        assert unit == "CNY"

    def test_normalize_percent_to_decimal(self):
        val, unit, rule = UnitRegistry.normalize_amount(12.5, "%")
        assert val == 0.125
        assert unit == "DECIMAL"

    def test_normalize_identity(self):
        val, unit, rule = UnitRegistry.normalize_amount(100.0, "元")
        assert val == 100.0
        assert unit == "CNY"

    def test_unknown_unit_raises(self):
        with pytest.raises(UnitConversionError):
            UnitRegistry.normalize_amount(100.0, "unknown")


class TestContexts:
    def test_build_context_id(self):
        ctx = build_context_id("601857.SH", 2025, "annual")
        assert ctx == "601857.SH|2025|annual|consolidated|original"

    def test_parse_period_label_annual(self):
        result = parse_period_label("2021FY")
        assert result["fiscal_year"] == 2021
        assert result["period_type"] == "annual"

    def test_parse_period_label_quarter(self):
        result = parse_period_label("2024Q2")
        assert result["fiscal_year"] == 2024
        assert result["quarter"] == 2

    def test_compute_period_dates_annual(self):
        start, end = compute_period_dates(2025, PeriodType.annual)
        assert start == "2025-01-01"
        assert end == "2025-12-31"

    def test_is_instant(self):
        assert is_instant(PeriodType.instant)
        assert not is_instant(PeriodType.annual)

    def test_create_context(self):
        ctx = create_context("601857.SH", 2025, "annual",
                             filing_date="2026-03-28")
        assert ctx.symbol == "601857.SH"
        assert ctx.fiscal_year == 2025
        assert ctx.consolidation_scope == ConsolidationScope.consolidated


class TestConceptMapping:
    def setup_method(self):
        self.mapping = ConceptMapping()

    def test_map_revenue(self):
        cid, factor = self.mapping.map_field("营业收入")
        assert cid == "revenue"
        assert factor == 1.0

    def test_map_unknown(self):
        cid, factor = self.mapping.map_field("不存在的字段")
        assert cid is None

    def test_reverse_map(self):
        reverse = self.mapping.get_reverse_map()
        assert "revenue" in reverse
        assert "营业收入" in reverse["revenue"]


class TestFactModel:
    def test_fact_defaults(self):
        f = Fact(symbol="601857.SH", concept_id="revenue")
        assert f.verification_status == VerificationStatus.unverified
        assert not f.is_derived
        assert not f.eligible_for_metrics

    def test_context_defaults(self):
        ctx = FactContext(
            context_id="test",
            symbol="601857.SH",
            fiscal_year=2025,
            period_type=PeriodType.annual,
        )
        assert ctx.consolidation_scope == ConsolidationScope.consolidated


class TestDerivationEngine:
    def test_single_quarter_q1(self):
        from ashare_research.derivations.engine import DerivationEngine

        df = pd.DataFrame([
            {"concept_id": "revenue", "symbol": "601857.SH",
             "fiscal_year": 2025, "report_type": "Q1", "value": 100.0,
             "fact_id": "f1", "unit": "CNY", "period_end": "2025-03-31",
             "source_provider": "test", "filing_date": "2025-04-28",
             "announcement_date": "2025-04-28",
             "available_at": "2025-04-28"},
        ])
        derived = DerivationEngine.derive_single_quarter(df, "revenue")
        assert len(derived) == 1
        assert derived[0]["value"] == 100.0

    def test_single_quarter_q2(self):
        from ashare_research.derivations.engine import DerivationEngine

        df = pd.DataFrame([
            {"concept_id": "revenue", "symbol": "601857.SH",
             "fiscal_year": 2025, "report_type": "Q1", "value": 300.0,
             "fact_id": "f1", "unit": "CNY", "period_end": "2025-03-31",
             "source_provider": "test", "filing_date": "2025-04-28",
             "announcement_date": "2025-04-28",
             "available_at": "2025-04-28"},
            {"concept_id": "revenue", "symbol": "601857.SH",
             "fiscal_year": 2025, "report_type": "H1", "value": 700.0,
             "fact_id": "f2", "unit": "CNY", "period_end": "2025-06-30",
             "source_provider": "test", "filing_date": "2025-08-28",
             "announcement_date": "2025-08-28",
             "available_at": "2025-08-28"},
        ])
        derived = DerivationEngine.derive_single_quarter(df, "revenue")
        # Q1 = 300, Q2 = 700-300 = 400
        values = {d["report_type"]: d["value"] for d in derived}
        assert values.get("single_q1") == 300
        assert values.get("single_q2") == 400

    def test_single_quarter_q3(self):
        from ashare_research.derivations.engine import DerivationEngine

        df = pd.DataFrame([
            {"concept_id": "net_profit", "symbol": "601857.SH",
             "fiscal_year": 2025, "report_type": "Q1", "value": 100.0,
             "fact_id": "f1", "unit": "CNY", "period_end": "2025-03-31",
             "source_provider": "test", "filing_date": "2025-04-28",
             "announcement_date": "2025-04-28",
             "available_at": "2025-04-28"},
            {"concept_id": "net_profit", "symbol": "601857.SH",
             "fiscal_year": 2025, "report_type": "H1", "value": 250.0,
             "fact_id": "f2", "unit": "CNY", "period_end": "2025-06-30",
             "source_provider": "test", "filing_date": "2025-08-28",
             "announcement_date": "2025-08-28",
             "available_at": "2025-08-28"},
            {"concept_id": "net_profit", "symbol": "601857.SH",
             "fiscal_year": 2025, "report_type": "Q3", "value": 400.0,
             "fact_id": "f3", "unit": "CNY", "period_end": "2025-09-30",
             "source_provider": "test", "filing_date": "2025-10-28",
             "announcement_date": "2025-10-28",
             "available_at": "2025-10-28"},
        ])
        derived = DerivationEngine.derive_single_quarter(df, "net_profit")
        values = {d["report_type"]: d["value"] for d in derived}
        assert values["single_q1"] == 100
        assert values["single_q2"] == 150
        assert values["single_q3"] == 150


class TestFactValidator:
    def test_valid_fact_passes(self):
        from ashare_research.validation.validator import FactValidator

        validator = FactValidator()
        fact = {
            "fact_id": "test_fact_1",
            "concept_id": "revenue",
            "symbol": "601857.SH",
            "value": 100.0,
            "unit": "CNY",
            "context_id": "ctx1",
            "filing_date": "2025-04-28",
            "period_end": "2025-03-31",
            "source_provider": "test",
            "source_tier": "company_official",
            "source_id": "official_report_2025_page_42",
            "verification_status": "verified",
            "announcement_date": "2025-04-28",
            "available_at": "2025-04-28",
            "eligible_for_metrics": False,
            "is_derived": False,
            "created_at": "2025-01-01",
        }
        results = validator.validate_single_fact(fact)
        failed = [r for r in results if not r.passed and r.severity == "error"]
        assert len(failed) == 0, f"Unexpected failures: {failed}"

    def test_nan_value_fails(self):
        from ashare_research.validation.validator import FactValidator

        validator = FactValidator()
        fact = {
            "fact_id": "test_nan", "concept_id": "revenue",
            "symbol": "601857.SH", "value": float("nan"),
            "unit": "CNY", "context_id": "ctx1",
            "filing_date": "2025-04-28", "period_end": "2025-03-31",
            "source_provider": "test",
            "verification_status": "unverified",
            "created_at": "2025-01-01",
        }
        results = validator.validate_single_fact(fact)
        failed = [r for r in results if not r.passed and r.severity == "error"]
        assert len(failed) >= 1
        assert any(r.rule_id == "FACT_VALUE_001" for r in failed)

    def test_unknown_unit_warns(self):
        from ashare_research.validation.validator import FactValidator

        validator = FactValidator()
        fact = {
            "fact_id": "test_unit", "concept_id": "revenue",
            "symbol": "601857.SH", "value": 100.0,
            "unit": "unknown_unit",
            "context_id": "ctx1",
            "filing_date": "2025-04-28", "period_end": "2025-03-31",
            "source_provider": "test",
            "verification_status": "unverified",
            "created_at": "2025-01-01",
        }
        results = validator.validate_single_fact(fact)
        failed = [r for r in results if not r.passed and r.severity == "error"]
        assert any(r.rule_id == "FACT_UNIT_001" for r in failed)

    def test_unregistered_concept_fails(self):
        from ashare_research.validation.validator import FactValidator

        validator = FactValidator()
        fact = {
            "fact_id": "test_unknown_concept",
            "concept_id": "nonexistent_concept_xyz",
            "symbol": "601857.SH", "value": 100.0,
            "unit": "CNY", "context_id": "ctx1",
            "filing_date": "2025-04-28", "period_end": "2025-03-31",
            "source_provider": "test",
            "verification_status": "unverified",
            "created_at": "2025-01-01",
        }
        results = validator.validate_single_fact(fact)
        failed = [r for r in results if not r.passed and r.severity == "error"]
        assert any(r.rule_id == "FACT_CONCEPT_001" for r in failed)

    def test_duplicate_fact_detected(self):
        from ashare_research.validation.validator import FactValidator

        validator = FactValidator()
        base = {
            "concept_id": "revenue", "symbol": "601857.SH",
            "value": 100.0, "unit": "CNY",
            "context_id": "dup_ctx",
            "filing_date": "2025-04-28", "period_end": "2025-03-31",
            "source_provider": "test",
            "verification_status": "unverified",
            "is_derived": False, "created_at": "2025-01-01",
        }
        facts = [
            {**base, "fact_id": "f1"},
            {**base, "fact_id": "f2"},
        ]
        results = validator.validate_batch(facts)
        failed = [r for r in results if not r.passed and r.severity == "error"]
        assert any(r.rule_id == "FACT_DUP_001" for r in failed)
