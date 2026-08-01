"""Canonical dividend event identity and chain validation."""

from __future__ import annotations

import hashlib
from typing import Any

DIVIDEND_EVENT_CONTRACT = "dividend_event_record_v1"
EVENT_STAGES = (
    "proposal",
    "shareholder_approved",
    "implementation_announced",
    "paid/implemented",
)


def build_dividend_event_id(
    symbol: str, source_fiscal_year: int, event_type: str, version: str = "1"
) -> str:
    """Return a stable event id independent of announcement URL bytes."""
    key = f"{DIVIDEND_EVENT_CONTRACT}|{symbol}|{source_fiscal_year}|{event_type}|{version}"
    return "dividend_event_" + hashlib.sha256(key.encode()).hexdigest()


def validate_dividend_event(record: dict[str, Any]) -> None:
    """Validate the non-schema parts of a committed dividend event record."""
    if record.get("contract") != DIVIDEND_EVENT_CONTRACT:
        raise ValueError("dividend event contract differs")
    if record.get("event_id") != build_dividend_event_id(
        str(record["symbol"]), int(record["source_fiscal_year"]), str(record["event_type"])
    ):
        raise ValueError("dividend event_id is not canonical")
    if record.get("event_stage") != "paid/implemented":
        raise ValueError("only paid/implemented events can be canonicalized")
    if record.get("market_scope") != "A_H_ordinary_combined":
        raise ValueError("dividend market scope must be the explicit A/H combined scope")
    if record.get("currency") != "CNY":
        raise ValueError("dividend currency must be CNY")
    chain = record.get("event_chain")
    if not isinstance(chain, list) or [item.get("stage") for item in chain] != list(EVENT_STAGES):
        raise ValueError("dividend proposal/approval/implementation/payment chain is incomplete")
    if not record.get("source_documents") or len(record["source_documents"]) != 2:
        raise ValueError("dividend event requires company and exchange official documents")
    if {item.get("source_tier") for item in record["source_documents"]} != {
        "company_official",
        "exchange_official",
    }:
        raise ValueError("dividend event requires one company and one exchange official document")
    for document in record["source_documents"]:
        if document.get("source_tier") not in {"company_official", "exchange_official"}:
            raise ValueError("dividend event source tier is not official")
    if not record.get("available_at"):
        raise ValueError("dividend event available_at is required")
