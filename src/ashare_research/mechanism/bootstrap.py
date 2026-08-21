"""Non-circular overlapping moving-block bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ashare_research.mechanism.analysis_contracts import (
    BOOTSTRAP_REPLICATIONS,
    BOOTSTRAP_RNG,
    BOOTSTRAP_SEED,
)
from ashare_research.mechanism.regression import fit_primary_ols


def moving_block_length(n: int) -> int:
    if n < 1:
        raise ValueError("n must be positive")
    return max(1, min(20, int(np.floor(n ** (1 / 3) + 0.5))))


def moving_block_sample(frame: pd.DataFrame, starts: np.ndarray, block_length: int) -> pd.DataFrame:
    n = len(frame)
    if block_length > n:
        raise ValueError("block_length cannot exceed n")
    if np.any(starts < 0) or np.any(starts > n - block_length):
        raise ValueError("moving block start is outside non-circular range")
    indices = np.concatenate(
        [np.arange(start, start + block_length, dtype=int) for start in starts]
    )[:n]
    return frame.iloc[indices].reset_index(drop=True)


@dataclass(frozen=True)
class BootstrapResult:
    gamma_samples: np.ndarray
    block_length: int
    replications: int
    seed: int
    rng: str
    gamma_ci_lower: float
    gamma_ci_upper: float


def moving_block_bootstrap(
    frame: pd.DataFrame,
    *,
    replications: int = BOOTSTRAP_REPLICATIONS,
    seed: int = BOOTSTRAP_SEED,
    rng_algorithm: str = BOOTSTRAP_RNG,
) -> BootstrapResult:
    """Resample complete rows and refit the locked OLS for every replicate."""

    if replications < 1:
        raise ValueError("replications must be positive")
    if rng_algorithm != "PCG64":
        raise ValueError("only PCG64 is frozen")
    length = moving_block_length(len(frame))
    rng = np.random.Generator(np.random.PCG64(seed))
    block_count = int(np.ceil(len(frame) / length))
    samples = np.empty(replications, dtype=float)
    for index in range(replications):
        starts = rng.integers(0, len(frame) - length + 1, size=block_count)
        sample = moving_block_sample(frame, starts, length)
        samples[index] = fit_primary_ols(sample).gamma
    interval = np.percentile(samples, [2.5, 97.5])
    return BootstrapResult(
        gamma_samples=samples,
        block_length=length,
        replications=replications,
        seed=seed,
        rng=rng_algorithm,
        gamma_ci_lower=float(interval[0]),
        gamma_ci_upper=float(interval[1]),
    )
