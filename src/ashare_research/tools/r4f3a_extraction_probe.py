"""R4F.3A extraction — pull the 5 target cells from the official PDFs.

Anchors (confirmed by probe):
- 2017 AR  p122  consolidated balance sheet: 归属于母公司股东权益合计  1,193,810 (2017-12-31)
- 2018 AR  p113  consolidated balance sheet: 归属于母公司股东权益合计  1,214,570 (2018-12-31)
- 2018 AR  p115  consolidated income statement: 归属于母公司股东的净利润  52,585 (2018)
- 2019 AR  p114  consolidated balance sheet: 归属于母公司股东权益合计  1,230,428 (2019-12-31)
- 2019 AR  p115  consolidated income statement: 归属于母公司股东的净利润  45,677 (2019)

Unit: CNY_million -> CNY (x 1,000,000).  Consolidation scope: consolidated,
attributable to parent shareholders.
"""

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from ashare_research.pit_valuation.pe_historical_annual_backfill import (  # noqa: E402
    CONCEPT_EQUITY,
    CONCEPT_NET_PROFIT,
)

CACHE = ROOT / "tmp" / "r4f3a_official_cache" / "objects"

# (label, pdf_sha, fiscal_year, page_index, row_pattern, concept,
#  expected_value_million, evidence_id)
TARGETS = [
    (
        "A_equity_2017",
        "c1a6fbffcc210020e672410400646e0c9fe2097f5de43047a24b950ae7930cea",
        2017,
        121,
        r"归属于母公司股东权益\s*合计\s+([0-9,]+)",
        CONCEPT_EQUITY,
        "1193810",
        "R4F3A-SSE-2017-AR",
    ),
    (
        "B_equity_2018",
        "5c205cc110a1650c7463530a05aac544737b78a317891ffc8f93ea5e35f6bf92",
        2018,
        112,
        r"归属于母公司股东权益\s*合计\s+([0-9,]+)",
        CONCEPT_EQUITY,
        "1214570",
        "R4F3A-SSE-2018-AR",
    ),
    (
        "C_np_2018",
        "5c205cc110a1650c7463530a05aac544737b78a317891ffc8f93ea5e35f6bf92",
        2018,
        113,
        r"归属于母公司股东的净利润\s+([0-9,]+)",
        CONCEPT_NET_PROFIT,
        "52585",
        "R4F3A-SSE-2018-AR",
    ),
    (
        "D_equity_2019",
        "d5fc46581ffc4617ee267682079c245f8d9e1c0eacdd8451c5d62151d6090778",
        2019,
        113,
        r"归属于母公司股东权益\s*合计\s+([0-9,]+)",
        CONCEPT_EQUITY,
        "1230428",
        "R4F3A-SSE-2019-AR",
    ),
    (
        "E_np_2019",
        "d5fc46581ffc4617ee267682079c245f8d9e1c0eacdd8451c5d62151d6090778",
        2019,
        114,
        r"归属于母公司股东的净利润\s+([0-9,]+)",
        CONCEPT_NET_PROFIT,
        "45677",
        "R4F3A-SSE-2019-AR",
    ),
]

# Restatement comparatives (2019 AR restates 2018 per Dalian Xitai SCA,
#   note 6(2); values read from the 2019 AR consolidated balance sheet /
#   income statement comparative columns):
#   2018-12-31 equity: 1,214,067 (restated_1); 2018 NP: 53,030 (restated_1)
#   2017-12-31 equity: 1,192,862 (restated_1, 2019 AR opening balance)
RESTATEMENTS = {
    (CONCEPT_EQUITY, "2018-12-31"): ("1214067", "R4F3A-SSE-2019-AR", "restated_1"),
    (CONCEPT_NET_PROFIT, "2018-12-31"): ("53030", "R4F3A-SSE-2019-AR", "restated_1"),
    (CONCEPT_EQUITY, "2017-12-31"): ("1192862", "R4F3A-SSE-2019-AR", "restated_1"),
}


def extract_value(page_text: str, pattern: str) -> Decimal | None:
    m = re.search(pattern, page_text)
    if not m:
        return None
    return Decimal(m.group(1).replace(",", ""))


def main() -> int:
    results = []
    ok = True
    for label, sha, fy, page_idx, pat, concept, expected, eid in TARGETS:
        pdf = CACHE / f"{sha}.pdf"
        if not pdf.is_file():
            print(f"FAIL {label}: PDF missing {pdf}")
            ok = False
            continue
        text = (PdfReader(str(pdf)).pages[page_idx].extract_text() or "").replace(
            "\n", " "
        )
        val = extract_value(text, pat)
        match = val is not None and str(val) == expected
        if not match:
            ok = False
        results.append(
            {
                "target_cell": label,
                "concept": concept,
                "period_end": f"{fy}-12-31",
                "source_document": f"objects/{sha}.pdf",
                "source_page": page_idx + 1,
                "raw_value_million": str(val) if val is not None else None,
                "expected_million": expected,
                "match": match,
                "evidence_id": eid,
            }
        )
        print(f"{'OK ' if match else 'FAIL'} {label}: {val} (expected {expected})")
    # restatement comparatives
    for (concept, pe), (val, src, ver) in RESTATEMENTS.items():
        results.append(
            {
                "target_cell": "RESTATED",
                "concept": concept,
                "period_end": pe,
                "raw_value_million": val,
                "restatement_version": ver,
                "source_evidence": src,
            }
        )
    out = ROOT / "reports" / "petrochina_pe_3y_historical_backfill_extraction_v1.json"
    out.write_text(
        json.dumps(
            {"schema": "pe_3y_historical_backfill_extraction_v1", "cells": results},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
