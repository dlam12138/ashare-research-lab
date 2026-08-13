"""Portable test-session guards for legacy baseline-only runners.

The historical acceptance runners retain a no-mutation check for the ignored
``data/research.duckdb`` path. Clean clones intentionally do not contain that
file, so the session replaces only those hash probes with an absent-path
baseline guard. Any present file and every other hash operation still use the
original implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any

from ashare_research.storage.default_db_guard import hash_optional_default_db

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "research.duckdb"
DEFAULT_DB_SHA256 = "4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6"
BASELINE_MODULES = (
    "ashare_research.tools.official_dividend_realization_vertical_slice",
    "ashare_research.tools.official_earnings_quality_2025_acceptance",
    "ashare_research.tools.official_earnings_quality_fact_foundation",
    "ashare_research.tools.official_earnings_quality_metric_extension",
    "ashare_research.tools.official_financial_safety_vertical_slice",
    "ashare_research.tools.official_net_profit_fact_foundation",
    "ashare_research.tools.official_roa_metric_extension",
    "ashare_research.tools.official_roe_metric_extension",
    "ashare_research.tools.official_roe_roa_denominator_2025_acceptance",
    "ashare_research.tools.official_roe_roa_denominator_foundation",
)


def _guarded_hash(original: Callable[[Path], str]) -> Callable[[Path], str]:
    def guarded(path: Path) -> str:
        if Path(path).resolve() == DEFAULT_DB.resolve() and not DEFAULT_DB.exists():
            return hash_optional_default_db(DEFAULT_DB, DEFAULT_DB_SHA256)
        return original(path)

    return guarded


def pytest_configure(config: Any) -> None:
    del config
    if DEFAULT_DB.exists():
        return
    for module_name in BASELINE_MODULES:
        module = import_module(module_name)
        for function_name in ("_sha", "_sha256"):
            original = getattr(module, function_name, None)
            if original is not None:
                setattr(module, function_name, _guarded_hash(original))
