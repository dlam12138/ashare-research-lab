"""配置加载模块。

从 YAML 配置文件加载数据源、存储和质量检查参数。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# 默认值
DEFAULT_CONFIG: dict[str, Any] = {
    "storage": {
        "duckdb_path": "data/research.duckdb",
        "raw_dir": "data/raw",
        "staging_dir": "data/staging",
        "quarantine_dir": "data/quarantine",
        "parquet_dir": "data/parquet",
    },
    "providers": {
        "stock_daily_primary": "baostock",
        "stock_daily_fallback": "akshare",
        "index_daily_primary": "akshare",
        "stock_basic_primary": "baostock",
        "trade_calendar_primary": "baostock",
    },
    "quality": {
        "reject_duplicate_keys": True,
        "reject_negative_prices": True,
        "reject_negative_volume": True,
        "warn_large_price_jump": True,
        "warn_missing_dates": True,
    },
}


def _find_project_root() -> Path:
    """查找项目根目录（包含 pyproject.toml 或 CLAUDE.md）。"""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists() or (parent / "CLAUDE.md").exists():
            return parent
    return current


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """加载配置，支持本地覆盖。

    优先级：local.yaml > example.yaml > 默认值

    Args:
        config_path: 显式配置文件路径，为 None 时自动搜索

    Returns:
        dict: 合并后的配置
    """
    root = _find_project_root()
    from copy import deepcopy
    config = deepcopy(DEFAULT_CONFIG)

    # 尝试加载 example 和 local 配置
    config_dir = root / "config"

    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    else:
        example = config_dir / "data_sources.example.yaml"
        local = config_dir / "data_sources.local.yaml"
        if local.exists():
            candidates.append(local)
        elif example.exists():
            candidates.append(example)

    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
                _deep_merge(config, file_config)

    # 将所有存储路径转为绝对路径（相对于项目根目录）
    for key in ("raw_dir", "staging_dir", "quarantine_dir", "parquet_dir"):
        val = config.get("storage", {}).get(key, "")
        if val and not os.path.isabs(val):
            config["storage"][key] = str(root / val)

    duckdb_path = config.get("storage", {}).get("duckdb_path", "")
    if duckdb_path and not os.path.isabs(duckdb_path):
        config["storage"]["duckdb_path"] = str(root / duckdb_path)

    return config


def _deep_merge(base: dict, override: dict) -> None:
    """递归合并 override 到 base（原地修改）。"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
