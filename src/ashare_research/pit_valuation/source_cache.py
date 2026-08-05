"""M2 Stage 2K.1R4D — official source cache acquisition and formal verification.

Acquire mode downloads official report PDFs from the official exchange endpoint
into an explicit external, content-addressed cache (``objects/<sha256>.pdf``)
with at most three attempts per URL.  Formal mode is fully offline: it verifies
every cached object against the frozen registry (SHA-256, byte size, ``%PDF-``
magic, page count, evidence aliases, filing period) and enforces the evidence
cutoff.  No third-party mirror is ever used.

The SSE static host answers with an ``acw_sc__v2`` JavaScript challenge.  The
solver below reproduces the deobfuscated permutation/XOR algorithm so that the
official filing bytes can be retrieved from the official source directly.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ashare_research.pit_valuation.contracts import (
    evidence_by_id,
    load_cache_registry,
)

# ── acw_sc__v2 challenge solver (official SSE static host) ────────────────

# Permutation positions observed in the official challenge script.  For each
# output position j, arg2[j] = arg1[pos_list[j] - 1].
_POS_LIST = [
    0xF, 0x23, 0x1D, 0x18, 0x21, 0x10, 0x1, 0x26, 0xA, 0x9,
    0x13, 0x1F, 0x28, 0x1B, 0x16, 0x17, 0x19, 0xD, 0x6, 0xB,
    0x27, 0x12, 0x14, 0x8, 0xE, 0x15, 0x20, 0x1A, 0x2, 0x1E,
    0x7, 0x4, 0x11, 0x5, 0x3, 0x1C, 0x22, 0x25, 0xC, 0x24,
]
_MASK = "3000176000856006061501533003690027800375"

_ACW_ARG1_RE = re.compile(r"var arg1='([0-9A-F]+)'")


def solve_acw_sc_v2(arg1: str) -> str:
    """Compute the ``acw_sc__v2`` cookie for a challenge ``arg1``.

    Reproduces the deobfuscated official algorithm: permute ``arg1`` by
    ``pos_list``, then XOR each hex pair with the fixed mask.
    """
    if len(arg1) != len(_POS_LIST):
        raise ValueError("unexpected acw arg1 length")
    out = [""] * len(_POS_LIST)
    for i, ch in enumerate(arg1):
        for j, pos in enumerate(_POS_LIST):
            if pos == i + 1:
                out[j] = ch
    arg2 = "".join(out)
    result = []
    for k in range(0, min(len(arg2), len(_MASK)), 2):
        xor_char = format(int(arg2[k : k + 2], 16) ^ int(_MASK[k : k + 2], 16), "x")
        result.append(("0" + xor_char) if len(xor_char) == 1 else xor_char)
    return "".join(result)


def _http_get(url: str, cookies: dict[str, str] | None = None) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (official endpoint)
        data = resp.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def fetch_official_pdf(url: str, *, retries: int = 3) -> bytes:
    """Fetch an official PDF, solving the acw challenge if present.

    Up to ``retries`` attempts; each challenge round-trip is one attempt.
    """
    cookies: dict[str, str] = {}
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            data = _http_get(url, cookies)
            if data[:5] == b"%PDF-":
                return data
            text = data.decode("utf-8", errors="replace")
            match = _ACW_ARG1_RE.search(text)
            if not match:
                raise RuntimeError("official endpoint returned a non-PDF response")
            cookies["acw_sc__v2"] = solve_acw_sc_v2(match.group(1))
            time.sleep(1.0 + attempt * 0.5)
        except Exception as exc:  # bounded acquisition log
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"official acquisition failed after {retries} attempts: {last_error}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── external cache root ───────────────────────────────────────────────────


def require_external_cache_root(cache_root: Path | str | None) -> Path:
    """Fail unless an explicit external cache root is supplied."""
    if cache_root is None:
        raise FileNotFoundError("formal/acquire mode requires --official-cache-root")
    root = Path(cache_root).resolve()
    return root


def _outside_repository(root: Path) -> bool:
    repo = Path(__file__).resolve().parents[3]
    return root != repo and repo not in root.parents


# ── acquire mode ──────────────────────────────────────────────────────────


def acquire(cache_root: Path | str | None, *, clock: Any | None = None) -> dict[str, Any]:
    """Download every missing official filing into the external cache.

    Content-addressed object keys.  At most three attempts per URL.  Never
    falls back to a third-party mirror.  Returns the formal verification
    result plus per-object acquisition outcomes.
    """
    root = require_external_cache_root(cache_root)
    if not _outside_repository(root):
        raise ValueError("official cache must be external to the repository")
    root.mkdir(parents=True, exist_ok=True)
    objects_dir = root / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    evidence = evidence_by_id()
    outcomes: list[dict[str, Any]] = []
    acquired: list[dict[str, Any]] = []

    # Only exchange_official SSE entries are downloadable this run; issuer
    # entries are recorded as blocked_source_access (see source evidence).
    for eid, entry in sorted(evidence.items()):
        if entry.get("source_role") != "exchange_official":
            outcomes.append(
                {
                    "evidence_id": eid,
                    "source_role": entry.get("source_role"),
                    "status": "blocked_source_access",
                    "note": entry.get("notes", "issuer endpoint not reachable"),
                }
            )
            continue
        url = entry.get("proof_url")
        if not url:
            outcomes.append({"evidence_id": eid, "status": "missing_url"})
            continue
        last_error = ""
        success = False
        for attempt in range(1, 4):
            try:
                data = fetch_official_pdf(url, retries=3)
                digest = sha256_bytes(data)
                target = objects_dir / f"{digest}.pdf"
                if not target.is_file():
                    target.write_bytes(data)
                acquired.append(
                    {
                        "evidence_id": eid,
                        "object_key": f"objects/{digest}.pdf",
                        "sha256": digest,
                        "byte_size": len(data),
                        "status": "downloaded_verified",
                        "attempt": attempt,
                    }
                )
                success = True
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < 3:
                    time.sleep(1.5 * attempt)
        if not success:
            outcomes.append(
                {"evidence_id": eid, "status": "acquisition_failed", "error": last_error[:200]}
            )
        else:
            outcomes.append(acquired[-1])

    result = verify_official_cache(root, acquired=acquired, clock=clock)
    result["acquisition_outcomes"] = outcomes
    return result


# ── formal verification ───────────────────────────────────────────────────


def _page_count(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


def verify_official_cache(
    cache_root: Path | str | None,
    *,
    acquired: list[dict[str, Any]] | None = None,
    clock: Any | None = None,
    registry: dict[str, Any] | None = None,
    evidence_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fully offline formal verification of the external official cache.

    Checks, per expected object: SHA-256, byte size, ``%PDF-`` magic, page
    count, evidence alias membership, and filing-period eligibility before the
    frozen evidence cutoff.  Raises on any mismatch (fail-closed).
    ``registry`` / ``evidence_map`` may be injected for offline tests.
    """
    root = require_external_cache_root(cache_root)
    registry = registry if registry is not None else load_cache_registry()
    evidence = evidence_map if evidence_map is not None else evidence_by_id()
    checks: list[dict[str, Any]] = []
    for obj in registry.get("objects", []):
        okey = obj["object_key"]
        path = root / okey
        expected_sha = obj["sha256"]
        row: dict[str, Any] = {
            "object_key": okey,
            "expected_sha256": expected_sha,
            "expected_byte_size": obj["byte_size"],
            "expected_page_count": obj["page_count"],
        }
        if not path.is_file():
            row.update({"status": "missing_object", "ok": False})
            checks.append(row)
            raise RuntimeError(f"official cache object missing: {okey}")
        actual_sha = sha256_bytes(path.read_bytes())
        actual_size = path.stat().st_size
        head = path.read_bytes()[:5]
        try:
            actual_pages = _page_count(path)
        except Exception:  # not a readable PDF -> fail closed
            actual_pages = -1
        row.update(
            {
                "actual_sha256": actual_sha,
                "actual_byte_size": actual_size,
                "actual_page_count": actual_pages,
                "pdf_magic": head.decode("latin-1", errors="replace") == "%PDF-",
            }
        )
        ok = (
            actual_sha == expected_sha
            and actual_size == obj["byte_size"]
            and actual_pages == obj["page_count"]
            and head == b"%PDF-"
        )
        row["ok"] = ok
        if not ok:
            row["status"] = "mismatch"
        else:
            row["status"] = "verified"
        checks.append(row)
        if not ok:
            raise RuntimeError(f"official cache object mismatch: {okey}")

    # Evidence alias membership + cutoff eligibility.
    alias_checks: list[dict[str, Any]] = []
    for obj in registry.get("objects", []):
        for eid in obj.get("evidence_ids", []):
            entry = evidence.get(eid)
            if entry is None:
                alias_checks.append(
                    {"evidence_id": eid, "status": "unknown_evidence", "ok": False}
                )
                raise RuntimeError(f"cache object references unknown evidence {eid}")
            cutoff_ok = entry.get("announcement_date", "9999-99-99") <= "2026-08-02"
            alias_checks.append(
                {
                    "object_key": obj["object_key"],
                    "evidence_id": eid,
                    "reporting_period": f"{entry['fiscal_year']}-{entry['report_type']}",
                    "cutoff_eligible": cutoff_ok,
                    "ok": cutoff_ok,
                }
            )
            if not cutoff_ok:
                raise RuntimeError(f"evidence {eid} is after the frozen evidence cutoff")

    return {
        "schema": "pit_valuation_official_cache_verification_v1",
        "cache_root_policy": "explicit_external_only",
        "default_db_touched": False,
        "objects_verified": len(checks),
        "all_objects_ok": all(c["ok"] for c in checks),
        "alias_checks": alias_checks,
        "checks": checks,
        "acquired": acquired or [],
    }


def write_cache_registry(registry_path: Path, objects: list[dict[str, Any]]) -> None:
    """Write the cache registry atomically (replaces the committed registry)."""
    registry = {
        "schema": "pit_valuation_official_cache_registry_v1",
        "data_class": "official_document",
        "symbol": "601857.SH",
        "cache_root_policy": "explicit_external_only",
        "objects": objects,
        "forbidden_fallbacks": [
            "Downloads",
            "browser_cache",
            "repository_tmp",
            "test_capsule",
            "third_party_mirror",
        ],
        "formal_network_access": False,
    }
    tmp = registry_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    tmp.replace(registry_path)
