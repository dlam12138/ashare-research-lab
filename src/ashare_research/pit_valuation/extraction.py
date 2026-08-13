"""M2 Stage 2K.1R4D — named-capture extraction of quarterly denominator cells.

Extraction is anchored to the CAS main-accounting-data section of each official
filing.  Values come exclusively from named capture groups; there are no
numeric constants in extraction.  A value must be independently recomputable
from its capture group.  This module never creates a Fact ID and never opens a
database.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)

# A number token: digits with optional thousand separators, optional decimals,
# optional surrounding parentheses (negative), optional leading minus and an
# optional trailing percentage sign (kept as part of the token so that a
# percentage column does not truncate the capture group).
_NUMBER_TOKEN = r"\(?-?[0-9][0-9,]*(?:\.[0-9]+)?\)?%?"

# Row pattern: label (non-greedy, no digits) followed by one or more numbers.
ROW_PATTERN = re.compile(
    rf"(?P<label>[一-鿿A-Za-z／/（）()%\s]+?)"
    rf"(?P<numbers>{_NUMBER_TOKEN}(?:\s+{_NUMBER_TOKEN})*)"
)


@dataclass
class ExtractedCell:
    """A single extracted numeric cell with full provenance."""

    cells: str = ""  # repeated field marker (schema compatibility)
    extraction_spec_id: str = ""
    role_id: str = ""
    evidence_id: str = ""
    report_type: str = ""
    fiscal_year: int = 0
    page_index: int = 0
    raw_token: str = ""
    tokens: list[str] = field(default_factory=list)
    has_restatement_comparatives: bool = False
    raw_value: Decimal | None = None
    normalized_value: Decimal | None = None
    unit: str = ""
    excerpt: str = ""
    excerpt_hash: str = ""
    span_start: int = 0
    span_end: int = 0
    sign_rule: str = ""
    conversion_multiplier: str = "1"
    status: str = "acquired"
    notes: str = ""


def sha256_span(excerpt: str) -> str:
    return hashlib.sha256(excerpt.encode("utf-8")).hexdigest()


def parse_decimal_token(token: str) -> Decimal | None:
    """Parse a number token into a Decimal.

    Parentheses denote a negative value (``(16,234)`` -> -16234).  A trailing
    percentage sign is dropped (``23.0%`` -> 23.0).  Thousand separators are
    removed.  Returns None on unparseable input.
    """
    t = token.strip()
    if not t:
        return None
    negative = t.startswith("(") and t.endswith(")")
    cleaned = t.strip("()")
    cleaned = cleaned.replace(",", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value if negative else value


def normalize_value(raw: Decimal, multiplier: str, unit: str) -> Decimal:
    """Deterministic unit conversion (raw unit -> canonical unit)."""
    factor = Decimal(multiplier)
    if unit == "CNY":
        return (raw * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return raw * factor


def _page_texts(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


_CAS_ANCHOR = re.compile(r"按中国企业会计准则编制的主要(?:会计|财务)数据")
# Next-section headers that terminate the CAS main-accounting-data section.
# Note: "非经常性损益项目" (not the bare "非经常性损益") so that the row
# label "扣除非经常性损益的净利润" does not truncate the section.
_SECTION_BOUNDARIES = (
    "非经常性损益项目和金额",
    "非经常性损益项目",
    "国内外会计准则差异",
    "境内外财务报表差异",
    "2.1.3",
    "2.2 非经常",
    "2.3",
    "三、重要事项",
    "四、",
    "管理层讨论与分析",
    "经营情况讨论与分析",
)


def _cas_section_bounds(pages: list[str]) -> tuple[int, str] | None:
    """Locate the CAS main-accounting-data section.

    The section can span several pages (e.g. the 2020-2022 Q3 filings print
    the balance-sheet items on one page and the income table on the next).
    Text is collected from the anchor page onwards until a next-section
    boundary marker appears.  Returns (page_index, section_text) or None.
    """
    for i, text in enumerate(pages):
        m = _CAS_ANCHOR.search(text)
        if not m:
            continue
        collected = [text[m.start() :]]
        for j in range(i + 1, min(i + 5, len(pages))):
            nxt = pages[j]
            stops = [nxt.find(b) for b in _SECTION_BOUNDARIES if nxt.find(b) >= 0]
            if stops:
                collected.append(nxt[: min(stops)])
                break
            collected.append(nxt)
        return i, "".join(collected)
    return None


def _numbers_from_match(match: re.Match[str]) -> list[str]:
    return match.group("numbers").split()


def extract_cell(
    spec: dict[str, Any],
    pdf_path: Path,
    *,
    evidence: dict[str, Any],
    page_texts: list[str] | None = None,
) -> ExtractedCell:
    """Extract one cell for one filing following one extraction spec.

    Extraction order: PDF -> page text -> CAS section -> named capture ->
    raw Decimal -> deterministic unit transform -> ExtractedCell.  Any failure
    yields a status-carrying cell (gap), never a fabricated value.
    ``page_texts`` may be injected for offline tests; otherwise the PDF is
    read with pypdf embedded-text extraction.
    """
    cell = ExtractedCell(
        extraction_spec_id=spec["extraction_spec_id"],
        role_id=spec["role_id"],
        evidence_id=evidence["evidence_id"],
        report_type=evidence["report_type"],
        fiscal_year=evidence["fiscal_year"],
        unit=spec["raw_unit"],
        sign_rule=spec["sign_rule"],
        conversion_multiplier=str(spec["conversion_multiplier"]),
    )

    pages = list(page_texts) if page_texts is not None else _page_texts(pdf_path)
    section = None
    if spec.get("section_constraint") == "cas_table":
        section = _cas_section_bounds(pages)
        if section is None:
            cell.status = "extraction_marker_missing"
            cell.notes = "CAS section anchor not found"
            return cell
        page_index, section_text = section
    else:
        page_index, section_text = 0, "\n".join(pages)

    pattern = re.compile(spec["named_capture_pattern"])
    # Normalise line breaks inside the section text: table labels sometimes
    # wrap across lines (e.g. ``归属于母公司股东\n的净利润``).  Numbers stay
    # whitespace-separated, so the row structure is preserved.
    section_text = section_text.replace("\n", " ")
    cell.has_restatement_comparatives = "追溯后" in section_text
    matches = list(pattern.finditer(section_text))
    if not matches:
        cell.status = "extraction_marker_missing"
        cell.notes = "row label not found in CAS section"
        return cell

    target_index = int(spec.get("target_token_index", 0))
    # The first match in the CAS section (or in the filing text for the annual
    # report) is the main-accounting-data row.  The current-period value is the
    # token at the documented index — never a scan for a repeated number.
    row = matches[0]
    numbers = _numbers_from_match(row)
    # When the spec pins the exact column layout, a row with a different token
    # count fails closed: the layout may have changed between filings and the
    # documented token index would silently select the wrong column.
    expected_count = spec.get("expected_token_count")
    if expected_count is not None and len(numbers) != int(expected_count):
        cell.status = "ambiguous_table_scope"
        cell.notes = (
            f"row token count {len(numbers)} != expected {expected_count}; "
            "column layout mismatch"
        )
        return cell
    if target_index >= len(numbers):
        cell.status = "ambiguous_table_scope"
        cell.notes = f"target token index {target_index} out of range ({len(numbers)} tokens)"
        return cell

    token = numbers[target_index]
    raw = parse_decimal_token(token)
    if raw is None:
        cell.status = "extraction_marker_missing"
        cell.notes = f"token {token!r} is not a parseable number"
        return cell

    cell.page_index = page_index
    cell.raw_token = token
    cell.tokens = numbers
    cell.raw_value = raw
    cell.excerpt = section_text[
        max(0, row.start() - 40) : row.end() + 40
    ]
    cell.excerpt_hash = sha256_span(cell.excerpt)
    cell.span_start = row.start()
    cell.span_end = row.end()
    cell.normalized_value = normalize_value(
        raw, spec["conversion_multiplier"], spec["raw_unit"]
    )
    cell.status = "acquired_reported_verified"
    return cell


def extract_filing(
    pdf_path: Path,
    evidence: dict[str, Any],
    specs: list[dict[str, Any]],
    *,
    page_texts: list[str] | None = None,
) -> list[ExtractedCell]:
    """Run every applicable spec against one filing."""
    cells: list[ExtractedCell] = []
    for spec in specs:
        if spec.get("evidence_ref") and spec["evidence_ref"] != evidence["evidence_id"]:
            continue
        if spec.get("report_type") != evidence["report_type"]:
            continue
        if (
            spec.get("fiscal_year") is not None
            and int(spec["fiscal_year"]) != evidence["fiscal_year"]
        ):
            continue
        if spec.get("role_id") in ("total_ordinary_shares_at_period_end",):
            # share-count cells are extracted through the share-capital spec
            continue
        cells.append(extract_cell(spec, pdf_path, evidence=evidence, page_texts=page_texts))
    return cells


def extract_share_capital(
    pdf_path: Path,
    evidence: dict[str, Any],
    spec: dict[str, Any],
    *,
    page_texts: list[str] | None = None,
) -> ExtractedCell:
    """Extract the precise period-end share count from the dividend statement.

    Anchor: ``<total> 股为基数`` inside the dividend base statement.  The
    precise count is only disclosed in the annual and half-year reports.
    ``page_texts`` may be injected for offline tests.
    """
    cell = ExtractedCell(
        extraction_spec_id=spec["extraction_spec_id"],
        role_id=spec["role_id"],
        evidence_id=evidence["evidence_id"],
        report_type=evidence["report_type"],
        fiscal_year=evidence["fiscal_year"],
        unit=spec["raw_unit"],
        sign_rule=spec["sign_rule"],
        conversion_multiplier=str(spec["conversion_multiplier"]),
    )
    pages = list(page_texts) if page_texts is not None else _page_texts(pdf_path)
    pattern = re.compile(spec["named_capture_pattern"])
    for page_index, text in enumerate(pages):
        m = pattern.search(text)
        if not m:
            continue
        token = m.group("target").strip().replace(",", "")
        try:
            raw = DECIMAL_CONTEXT.create_decimal(token)
        except InvalidOperation:
            continue
        cell.page_index = page_index
        cell.raw_token = m.group("target")
        cell.raw_value = raw
        cell.normalized_value = raw
        cell.excerpt = text[max(0, m.start() - 60) : m.end() + 60]
        cell.excerpt_hash = sha256_span(cell.excerpt)
        cell.span_start = m.start()
        cell.span_end = m.end()
        cell.status = "acquired_reported_verified"
        return cell
    cell.status = "not_separately_disclosed"
    cell.notes = "precise period-end share count not disclosed in this filing"
    return cell
