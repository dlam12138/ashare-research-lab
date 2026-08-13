"""Path-independent market snapshot registry and resolver.

Registry records identify content.  A caller supplies the location in which
that content is allowed to exist.  The resolver never downloads, guesses a
fallback, or exposes the resolved private path in a run manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class MissingExternalResearchInput(FileNotFoundError):  # noqa: N818
    """Raised when explicitly configured real research input is unavailable."""


class MarketSnapshotResolver:
    """Resolve a v2 registry against an explicit real or test root."""

    def __init__(
        self,
        registry_path: Path | str,
        *,
        mode: str,
        cache_root: Path | str | None = None,
        fixture_root: Path | str | None = None,
    ) -> None:
        self.registry_path = Path(registry_path)
        self.mode = mode
        self.cache_root = Path(cache_root) if cache_root is not None else None
        self.fixture_root = Path(fixture_root) if fixture_root is not None else None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _is_absolute_text(value: str) -> bool:
        text = str(value)
        return (
            Path(text).is_absolute()
            or text.startswith(("~", "/"))
            or (len(text) >= 2 and text[1] == ":")
            or "\\" in text and ("\\" in text[:3] or text.startswith("\\"))
        )

    @classmethod
    def validate_registry_contract(cls, registry: dict[str, Any]) -> None:
        if registry.get("contract") != "market_data_snapshot_registry_v2":
            raise ValueError("market registry must use market_data_snapshot_registry_v2")
        providers = registry.get("providers")
        if not isinstance(providers, list) or not providers:
            raise ValueError("market registry has no providers")
        for key in ("normalized_cache_path", "raw_response_path"):
            if key in json.dumps(registry, ensure_ascii=False):
                raise ValueError(f"market registry contains removed path field: {key}")
        for record in providers:
            if record.get("retrieval_status") not in {"verified_external", "synthetic_test_only"}:
                raise ValueError(
                    f"unsupported market retrieval status: {record.get('retrieval_status')}"
                )
            object_key = str(record.get("object_key", ""))
            if not object_key or cls._is_absolute_text(object_key):
                raise ValueError("market registry object_key must be relative")
            if ".." in Path(object_key).parts:
                raise ValueError("market registry object_key may not escape its root")
            if len(str(record.get("sha256", ""))) != 64:
                raise ValueError("market registry snapshot SHA-256 is required")
        serialized = json.dumps(registry, ensure_ascii=False, sort_keys=True)
        if "D:\\" in serialized or "D:/" in serialized:
            raise ValueError("market registry contains a machine-specific path")

    def _root_for_mode(self, registry: dict[str, Any]) -> Path:
        if self.mode == "test_capsule":
            if self.cache_root is not None:
                raise ValueError("test_capsule mode cannot use an external market cache")
            if self.fixture_root is None:
                raise FileNotFoundError(
                    "missing_input: test_capsule requires --market-fixture-root"
                )
            if registry.get("data_class") != "synthetic_test_only":
                raise ValueError("test_capsule mode requires a synthetic_test_only registry")
            return self.fixture_root
        if self.mode == "real_research":
            if self.cache_root is None:
                raise MissingExternalResearchInput(
                    "missing_external_research_input: --market-cache-root is required"
                )
            if registry.get("data_class") == "synthetic_test_only":
                raise ValueError("real_research mode cannot consume test market fixtures")
            return self.cache_root
        raise ValueError(f"unknown market resolver mode: {self.mode}")

    def resolve(self) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any]]:
        if not self.registry_path.is_file():
            raise MissingExternalResearchInput(
                f"missing_external_research_input: registry not found: {self.registry_path.name}"
            )
        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.validate_registry_contract(registry)
        root = self._root_for_mode(registry).resolve()
        resolved: list[tuple[Path, dict[str, Any]]] = []
        for record in registry["providers"]:
            candidate = (root / str(record["object_key"])).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError("resolved market snapshot escaped its configured root") from exc
            if not candidate.is_file():
                message = (
                    "missing_external_research_input"
                    if self.mode == "real_research"
                    else "missing_input"
                )
                raise FileNotFoundError(f"{message}: market snapshot {record['object_key']}")
            actual = self._sha256(candidate)
            if actual != record["sha256"]:
                raise ValueError(
                    f"market snapshot hash mismatch for {record['logical_name']}: "
                    f"expected {record['sha256']}, got {actual}"
                )
            if (
                self.mode == "test_capsule"
                and record.get("retrieval_status") != "synthetic_test_only"
            ):
                raise ValueError("test_capsule market records must be synthetic_test_only")
            if (
                self.mode == "real_research"
                and record.get("retrieval_status") != "verified_external"
            ):
                raise ValueError("real_research market records must be verified_external")
            resolved.append((candidate, record))
        return resolved, registry


def read_market_frame(path: Path):
    """Read a registry-resolved CSV or Parquet snapshot without network access."""

    import pandas as pd

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"unsupported market snapshot format: {path.suffix}")
