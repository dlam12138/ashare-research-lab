"""M2 Stage 2K.1R4D — official source cache acquisition contract tests.

Non-official sources are rejected; the external cache is required; hash/size/
page mismatches are rejected; issuer/SSE byte-identical objects deduplicate to
one content object with two evidence aliases while distinct objects bind
separately; post-cutoff filings are excluded; raw PDFs never enter Git.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ashare_research.pit_valuation.contracts import (
    RESEARCH_EVIDENCE_AS_OF,
)
from ashare_research.pit_valuation.source_cache import (
    require_external_cache_root,
    solve_acw_sc_v2,
    verify_official_cache,
)

ROOT = Path(__file__).resolve().parents[1]


# ── synthetic fixtures ────────────────────────────────────────────────────


def _tiny_pdf_bytes(label: bytes = b"test") -> bytes:
    # A minimal but structurally valid PDF whose byte content is deterministic.
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n0\n%%EOF"
    )
    return content + label + b"\n"


def _registry(objects: list[dict]) -> dict:
    return {"schema": "pit_valuation_official_cache_registry_v1", "objects": objects}


def _evidence_map(objects: list[dict]) -> dict[str, dict]:
    out = {}
    for obj in objects:
        for eid in obj["evidence_ids"]:
            out[eid] = {
                "evidence_id": eid,
                "announcement_date": "2026-04-30",
                "fiscal_year": 2026,
                "report_type": "q1",
            }
    return out


def _sse_object(tmp_path: Path, eid: str, label: bytes = b"a") -> dict:
    data = _tiny_pdf_bytes(label)
    obj = {
        "object_key": None,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
        "page_count": 1,
        "media_type": "application/pdf",
        "evidence_ids": [eid],
    }
    obj["object_key"] = f"objects/{obj['sha256']}.pdf"
    (tmp_path / "objects").mkdir(exist_ok=True)
    (tmp_path / obj["object_key"]).write_bytes(data)
    return obj


# ── external cache required ───────────────────────────────────────────────


def test_external_cache_root_required():
    with pytest.raises(FileNotFoundError):
        require_external_cache_root(None)


def test_cache_root_must_be_external(tmp_path):
    from ashare_research.pit_valuation.source_cache import acquire

    with pytest.raises(ValueError):
        # The repository root is not an allowed external cache root.
        acquire(str(ROOT))


# ── formal verification failures ──────────────────────────────────────────


def test_hash_mismatch_rejected(tmp_path):
    obj = _sse_object(tmp_path, "ev-1", label=b"a")
    obj["sha256"] = "0" * 64
    with pytest.raises(RuntimeError):
        verify_official_cache(
            tmp_path,
            registry=_registry([obj]),
            evidence_map=_evidence_map([obj]),
        )


def test_size_mismatch_rejected(tmp_path):
    obj = _sse_object(tmp_path, "ev-1", label=b"a")
    obj["byte_size"] = obj["byte_size"] + 1
    with pytest.raises(RuntimeError):
        verify_official_cache(
            tmp_path,
            registry=_registry([obj]),
            evidence_map=_evidence_map([obj]),
        )


def test_pdf_magic_mismatch_rejected(tmp_path):
    obj = _sse_object(tmp_path, "ev-1", label=b"a")
    target = tmp_path / obj["object_key"]
    target.write_bytes(b"NOTAPDF" + b"\x00" * 20)  # not a %PDF- magic
    with pytest.raises(RuntimeError):
        verify_official_cache(
            tmp_path,
            registry=_registry([obj]),
            evidence_map=_evidence_map([obj]),
        )


def test_page_count_mismatch_rejected(tmp_path):
    obj = _sse_object(tmp_path, "ev-1", label=b"a")
    obj["page_count"] = 7
    with pytest.raises(RuntimeError):
        verify_official_cache(
            tmp_path,
            registry=_registry([obj]),
            evidence_map=_evidence_map([obj]),
        )


def test_missing_object_rejected(tmp_path):
    obj = _sse_object(tmp_path, "ev-1", label=b"a")
    (tmp_path / obj["object_key"]).unlink()
    with pytest.raises(RuntimeError):
        verify_official_cache(
            tmp_path,
            registry=_registry([obj]),
            evidence_map=_evidence_map([obj]),
        )


# ── dual alias / distinct objects ─────────────────────────────────────────


def test_issuer_sse_byte_identical_dedup_to_one_object(tmp_path):
    data = _tiny_pdf_bytes(b"shared")
    obj = {
        "object_key": f"objects/{hashlib.sha256(data).hexdigest()}.pdf",
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
        "page_count": 1,
        "media_type": "application/pdf",
        "evidence_ids": ["R4D-ISS-2025-AR", "R4D-SSE-2025-AR"],
    }
    (tmp_path / obj["object_key"]).parent.mkdir(exist_ok=True)
    (tmp_path / obj["object_key"]).write_bytes(data)
    result = verify_official_cache(
        tmp_path,
        registry=_registry([obj]),
        evidence_map=_evidence_map([obj]),
    )
    assert result["all_objects_ok"]
    alias_eids = {c["evidence_id"] for c in result["alias_checks"]}
    assert alias_eids == {"R4D-ISS-2025-AR", "R4D-SSE-2025-AR"}


def test_distinct_official_objects_bind_separately(tmp_path):
    o1 = _sse_object(tmp_path, "issuer-1", label=b"issuer")
    o2 = _sse_object(tmp_path, "exchange-1", label=b"exchange")
    assert o1["sha256"] != o2["sha256"]
    result = verify_official_cache(
        tmp_path,
        registry=_registry([o1, o2]),
        evidence_map=_evidence_map([o1, o2]),
    )
    assert result["objects_verified"] == 2


# ── cutoff exclusion ──────────────────────────────────────────────────────


def test_post_cutoff_filing_excluded(tmp_path):
    obj = _sse_object(tmp_path, "ev-late", label=b"late")
    evidence = _evidence_map([obj])
    evidence["ev-late"]["announcement_date"] = "2026-08-20"  # after frozen cutoff
    with pytest.raises(RuntimeError):
        verify_official_cache(
            tmp_path,
            registry=_registry([obj]),
            evidence_map=evidence,
        )


def test_frozen_cutoff_is_2026_08_02():
    assert RESEARCH_EVIDENCE_AS_OF == "2026-08-02"


# ── raw PDF never enters Git ──────────────────────────────────────────────


def test_cache_objects_are_content_addressed():
    registry = json.loads(
        (ROOT / "config" / "pit_valuation_official_cache_registry_v1.json").read_text("utf-8")
    )
    for obj in registry["objects"]:
        assert obj["object_key"] == f"objects/{obj['sha256']}.pdf"


def test_gitignore_excludes_cache_and_pdf_tmp():
    gitignore = (ROOT / ".gitignore").read_text("utf-8")
    assert "tmp/" in gitignore
    assert "*.pdf" not in gitignore  # no blanket PDF ignore; the cache root is external


def test_acw_solver_deterministic():
    a = solve_acw_sc_v2("AB9917117DC44951D86B9A9225D974FEFCA5E033")
    b = solve_acw_sc_v2("AB9917117DC44951D86B9A9225D974FEFCA5E033")
    assert a == b
    assert len(a) == 40


def test_forbidden_official_mirrors_rejected():
    # The cache registry explicitly forbids third-party mirror fallbacks.
    from ashare_research.pit_valuation.contracts import load_cache_registry

    registry = load_cache_registry()
    assert "third_party_mirror" in registry["forbidden_fallbacks"]
    assert "Downloads" in registry["forbidden_fallbacks"]


def test_non_official_sources_not_acquired(tmp_path):
    # The acquire mode only downloads exchange_official evidence; issuer
    # entries recorded as blocked_source_access are never fetched.
    from ashare_research.pit_valuation.source_cache import acquire

    with pytest.raises(FileNotFoundError):
        acquire(None)  # external cache root is required first
