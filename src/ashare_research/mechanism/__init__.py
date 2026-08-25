"""M3 data-preparation layers plus locked Stage 3C-A synthetic primitives.

Stage 3B contracts, normalization, lineage, acquisition, and market-proxy
construction remain the canonical data layer. Stage 3C-A modules are imported
directly and remain synthetic-only; no real mechanism result is exposed here.
"""

from ashare_research.mechanism.contracts import Stage3BContractError

__all__ = ["Stage3BContractError"]
