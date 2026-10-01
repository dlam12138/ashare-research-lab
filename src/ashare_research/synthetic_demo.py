"""Offline synthetic demonstration entry for the frozen five-stage M4 pipeline.

``python -m ashare_research.synthetic_demo`` builds one fixed, clearly invented
24-row daily synthetic example with the public stage APIs, runs the existing
frozen ``run_synthetic_pipeline`` composed entry, validates the returned
envelope and prints a readable summary.  ``--json`` writes the existing
canonical serialized result bytes verbatim instead (exactly one final newline,
unchanged).

The demonstration is deliberately bounded and non-parametric: the command
exposes only ``--json`` and help, so there is no input, config, seed, provider,
database, output-path, environment or registry-state argument to choose.  The
fixed configuration disables bootstrap and keeps an empty robustness registry,
and no M4-B registry record is bound.  The module performs no filesystem,
network, database or environment access of its own.

Boundary: a successful run is a software demonstration on invented synthetic
values.  It is not a research finding, not evidence of estimability,
significance, economic validity or tradability, not an A-share mechanism result
and not an authorization to execute on real or holdout data.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import fields
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from ashare_research.mechanism.contract_compiler import compile_hypothesis_config
from ashare_research.mechanism.datasets import (
    BoundDatasetInputsV1,
    ExpectedDomainV1,
    ObservationV1,
    RoleBindingV1,
)
from ashare_research.mechanism.datasets.synthetic import SCHEMA as BOUND_DATASET_SCHEMA
from ashare_research.mechanism.hypothesis_config import (
    CONFIG_SCHEMA_VERSION,
    canonical_decimal,
    parse_hypothesis_config,
)
from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.pipeline import (
    ORCHESTRATOR_VERSION,
    PIPELINE_SCHEMA_VERSION,
    SYNTHETIC_PIPELINE_MODE,
    SyntheticPipelineRequestV1,
    SyntheticPipelineResultV1,
    bound_inputs_identity_payload,
    run_synthetic_pipeline,
    serialize_pipeline_result,
    validate_pipeline_result,
)
from ashare_research.mechanism.planning import build_analysis_plan

# --- Fixed, invented demonstration identity -----------------------------------------------------

DEMO_HYPOTHESIS_ID = "DEMO_INVENTED_DAILY_001"
DEMO_ROW_COUNT = 24
DEMO_DEVELOPMENT_START = "2030-01-01"
DEMO_DEVELOPMENT_END = "2030-12-31"
DEMO_FIRST_TRADE_DATE = "2030-02-01"
DEMO_TARGET_SERIES_ID = "DEMO_TARGET_INVENTED_A"
DEMO_FACTOR_SERIES_ID = "DEMO_FACTOR_INVENTED_A"
DEMO_CONTROL_SERIES_IDS = ("DEMO_CONTROL_INVENTED_1", "DEMO_CONTROL_INVENTED_2")
DEMO_DOMAIN_ID = "DEMO_DOMAIN_INVENTED_A"
DEMO_UNIVERSE_ID = "DEMO_UNIVERSE_INVENTED_A"
DEMO_OUTCOME_ID = "DEMO_INVENTED_DAILY_RETURN"
DEMO_CONDITION_OPERATOR = "LTE"
DEMO_CONDITION_THRESHOLD = "-0.0050"
DEMO_EVIDENCE_RULE_ID = "DEMO_INVENTED_EVIDENCE_RULE_1"
DEMO_DECIMAL_PRECISION = 28

# --- Command surface ----------------------------------------------------------------------------

FAILURE_PREFIX = "SYNTHETIC_DEMO_FAILURE"
FALLBACK_FAILURE_CODE = "DEMO_VALIDATION_FAILED"
EXIT_SUCCESS = 0
EXIT_VALIDATION_FAILURE = 1
EXIT_USAGE_ERROR = 2

_SAFE_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


def demo_dates() -> tuple[str, ...]:
    """Return the fixed, invented 24 trading dates of the demonstration window."""

    year_month = DEMO_FIRST_TRADE_DATE[:8]
    return tuple(f"{year_month}{day:02d}" for day in range(1, DEMO_ROW_COUNT + 1))


def _demo_config_document() -> dict:
    """Return a fresh document for the fixed, invented synthetic configuration."""

    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "hypothesis_id": DEMO_HYPOTHESIS_ID,
        "target": {
            "series_id": DEMO_TARGET_SERIES_ID,
            "identity_policy": "SYNTHETIC_FIXED_IDENTITY",
        },
        "universe": {
            "universe_id": DEMO_UNIVERSE_ID,
            "membership_policy": "SYNTHETIC_FIXED_UNIVERSE",
            "pit_policy": "EXPLICIT_PIT",
        },
        "factor": {
            "factor_id": DEMO_FACTOR_SERIES_ID,
            "factor_kind": "SYNTHETIC_REGISTERED",
            "direction": "POSITIVE",
            "transform_semantics": "RETURN",
        },
        "condition": {"operator": DEMO_CONDITION_OPERATOR, "threshold": DEMO_CONDITION_THRESHOLD},
        "outcome": {
            "outcome_id": DEMO_OUTCOME_ID,
            "horizon": "1D",
            "observation_timing": "CLOSE_TO_CLOSE",
        },
        "controls": list(DEMO_CONTROL_SERIES_IDS),
        "development": {"start": DEMO_DEVELOPMENT_START, "end": DEMO_DEVELOPMENT_END},
        "data_quality_gates": {
            "coverage_gate": "0.9900",
            "pit_required": True,
            "identity_required": True,
            "missingness_policy": "FAIL_CLOSED",
            "duplicate_policy": "FAIL_CLOSED",
        },
        "analysis_method": {"method_id": "DAILY_CONDITIONAL_CONTROLLED_OLS_V1"},
        # Fixed no-bootstrap policy: bootstrap is explicitly disabled, and the remaining policy
        # fields stay valid so the frozen parser accepts one complete declaration.
        "bootstrap_policy": {
            "enabled": False,
            "method_id": "DISABLED",
            "replications": 1000,
            "seed": 7,
            "rng": "PCG64",
            "confidence_level": 0.95,
        },
        # The demonstration registers no robustness entry; the registry is empty, not absent.
        "robustness_registry": [],
        "evidence_rule": {
            "rule_id": DEMO_EVIDENCE_RULE_ID,
            "expected_direction": "POSITIVE",
            "confidence_requirement": "0.95",
            "data_quality_failure_disposition": "INCONCLUSIVE",
        },
    }


def _row_values() -> dict[str, tuple[str, ...]]:
    """Invent the fixed per-role values of the 24-row example.

    Every value is a canonical decimal string built inside one fixed local decimal
    context, so ambient precision or rounding cannot change the demonstration bytes.
    The factor alternates below and above the frozen condition threshold; the two
    controls use different invented deterministic patterns, so the design keeps full
    rank without copying any existing fixture values.
    """

    with localcontext() as context:
        context.prec = DEMO_DECIMAL_PRECISION
        context.rounding = ROUND_HALF_EVEN
        outcome: list[str] = []
        factor: list[str] = []
        first_control: list[str] = []
        second_control: list[str] = []
        for index in range(DEMO_ROW_COUNT):
            conditioned = index % 2 == 0
            factor_value = (
                Decimal("-0.02") - Decimal("0.0005") * index
                if conditioned
                else Decimal("0.015") + Decimal("0.0005") * index
            )
            control_one = Decimal("0.003") * (index + 1)
            control_two = Decimal("0.002") * ((2 * index) % 5)
            response = (
                Decimal("0.004") * (1 if conditioned else 0)
                + Decimal("0.002") * control_one
                + Decimal("0.001") * control_two
                + Decimal("0.0003") * ((index * index) % 7)
            )
            factor.append(canonical_decimal(factor_value))
            first_control.append(canonical_decimal(control_one))
            second_control.append(canonical_decimal(control_two))
            outcome.append(canonical_decimal(response))
    return {
        "TARGET_OUTCOME": tuple(outcome),
        "FACTOR": tuple(factor),
        "CONTROL_0001": tuple(first_control),
        "CONTROL_0002": tuple(second_control),
    }


def _demo_domain(dates: tuple[str, ...]) -> ExpectedDomainV1:
    """Build the invented synthetic domain with recomputed evidence digests."""

    calendar = {
        "evidence_kind": "SYNTHETIC_CALENDAR_V1",
        "domain_id": DEMO_DOMAIN_ID,
        "development_start": DEMO_DEVELOPMENT_START,
        "development_end": DEMO_DEVELOPMENT_END,
        "expected_dates": list(dates),
    }
    membership = {
        "evidence_kind": "SYNTHETIC_FIXED_MEMBERSHIP_V1",
        "universe_id": DEMO_UNIVERSE_ID,
        "target_series_id": DEMO_TARGET_SERIES_ID,
        "expected_dates": list(dates),
    }
    return ExpectedDomainV1.from_dict(
        {
            "domain_id": DEMO_DOMAIN_ID,
            "universe_id": DEMO_UNIVERSE_ID,
            "membership_policy": "SYNTHETIC_FIXED_UNIVERSE",
            "pit_policy": "EXPLICIT_PIT",
            "target_series_id": DEMO_TARGET_SERIES_ID,
            "identity_policy": "SYNTHETIC_FIXED_IDENTITY",
            "development_start": DEMO_DEVELOPMENT_START,
            "development_end": DEMO_DEVELOPMENT_END,
            "expected_dates": list(dates),
            "calendar_evidence": {**calendar, "evidence_digest": canonical_digest(calendar)},
            "membership_evidence": {**membership, "evidence_digest": canonical_digest(membership)},
        }
    )


def _demo_bindings() -> tuple[RoleBindingV1, ...]:
    """Declare the four invented synthetic role bindings in frozen plan order."""

    roles = ("TARGET_OUTCOME", "FACTOR", "CONTROL_0001", "CONTROL_0002")
    series = (
        DEMO_TARGET_SERIES_ID,
        DEMO_FACTOR_SERIES_ID,
        *DEMO_CONTROL_SERIES_IDS,
    )
    return tuple(
        RoleBindingV1(
            role,
            series_id,
            "DAILY_RETURN",
            "DECIMAL_RETURN",
            "SYNTHETIC_DECLARED_RETURN",
            DEMO_OUTCOME_ID if role == "TARGET_OUTCOME" else None,
            "1D",
            "CLOSE_TO_CLOSE",
        )
        for role, series_id in zip(roles, series, strict=True)
    )


def _demo_observations(
    dates: tuple[str, ...],
    values: dict[str, tuple[str, ...]],
    bindings: tuple[RoleBindingV1, ...],
) -> tuple[ObservationV1, ...]:
    """Build one PIT-available observation per role and date with public digests."""

    observations: list[ObservationV1] = []
    for binding in bindings:
        binding_payload = {field.name: getattr(binding, field.name) for field in fields(binding)}
        for trade_date, value in zip(dates, values[binding.role], strict=True):
            source_record_id = f"DEMO_SOURCE_{binding.role}_{trade_date}"
            payload = {
                "role": binding.role,
                "trade_date": trade_date,
                "value": value,
                "available_on": trade_date,
                "source_record_id": source_record_id,
                "binding": binding_payload,
            }
            observations.append(
                ObservationV1(
                    binding.role,
                    trade_date,
                    value,
                    trade_date,
                    source_record_id,
                    canonical_digest(payload),
                )
            )
    return tuple(observations)


def build_demo_request() -> SyntheticPipelineRequestV1:
    """Build the fixed synthetic request with public stage and digest APIs only.

    Two passes exactly as documented for the composed entry: the contract and plan are
    compiled first, then the public ``bound_inputs_identity_payload`` plus the public
    ``canonical_digest`` produce ``input_digest``.  No registry record is bound, so the
    envelope reports the explicit ``REGISTRY_BINDING_ABSENT`` form.
    """

    config = parse_hypothesis_config(_demo_config_document())
    contract = compile_hypothesis_config(config)
    plan = build_analysis_plan(contract)
    dates = demo_dates()
    bindings = _demo_bindings()
    observations = _demo_observations(dates, _row_values(), bindings)
    domain = _demo_domain(dates)
    input_digest = canonical_digest(
        bound_inputs_identity_payload(contract, plan, domain, bindings, observations)
    )
    bound_inputs = BoundDatasetInputsV1(
        schema_version=BOUND_DATASET_SCHEMA,
        mode=SYNTHETIC_PIPELINE_MODE,
        source_contract_digest=contract.contract_digest,
        plan_digest=plan.plan_digest,
        domain=domain,
        bindings=bindings,
        observations=observations,
        input_digest=input_digest,
    )
    return SyntheticPipelineRequestV1(
        schema_version=PIPELINE_SCHEMA_VERSION,
        orchestrator_version=ORCHESTRATOR_VERSION,
        config=config,
        bound_inputs=bound_inputs,
        registry_record=None,
    )


def run_demo() -> SyntheticPipelineResultV1:
    """Run the fixed synthetic chain and return the validated immutable envelope."""

    request = build_demo_request()
    result = run_synthetic_pipeline(request=request)
    validate_pipeline_result(result, request)
    return result


def _summary_lines(result: SyntheticPipelineResultV1) -> tuple[str, ...]:
    """Render the readable summary, including the verbatim interpretation boundary."""

    metadata = result.metadata
    observations = len(result.preparation.audit_rows) * len(result.preparation.role_order)
    return (
        f"M4 synthetic demonstration: invented {DEMO_ROW_COUNT}-row daily example, "
        "synthetic-only, no real data",
        f"hypothesis_id={DEMO_HYPOTHESIS_ID}",
        f"mode={SYNTHETIC_PIPELINE_MODE} rows={result.execution.sample.row_count} "
        f"observations={observations}",
        f"pipeline_state={metadata.pipeline_state}",
        f"stages_completed={','.join(metadata.stages_completed)}",
        f"pipeline_digest={metadata.pipeline_digest}",
        "interpretation_boundary:",
        metadata.interpretation_boundary,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ashare_research.synthetic_demo",
        description=(
            "Run the frozen five-stage M4 synthetic mechanism pipeline on one fixed, invented "
            "24-row daily example and print the canonical result. No input, config, seed, "
            "provider, database or output-path argument exists."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "write the existing canonical serialized result bytes verbatim "
            "instead of the readable summary"
        ),
    )
    return parser


def _failure_code(error: BaseException) -> str:
    """Return a sanitized failure code: no message text, paths, values or traceback."""

    code = getattr(error, "code", None)
    if type(code) is str and _SAFE_CODE_RE.fullmatch(code) is not None:
        return code
    return FALLBACK_FAILURE_CODE


def _emit(stream, encoded: bytes) -> None:
    """Write exact bytes to a stream, bypassing platform newline translation."""

    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(encoded.decode("utf-8"))
    else:
        buffer.write(encoded)
    stream.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: 0 on success, 1 on a known validation failure, 2 on a usage error.

    Every frozen stage layer signals a validation failure with a ``ValueError``
    subclass, so those are reported as one sanitized code on stderr and no result is
    printed.  Programming errors (``TypeError`` and anything outside that contract) are
    not swallowed, so a defect cannot masquerade as a clean validation failure.
    """

    arguments = _build_parser().parse_args(argv)
    try:
        result = run_demo()
        encoded = (
            serialize_pipeline_result(result)
            if arguments.json
            else ("\n".join(_summary_lines(result)) + "\n").encode("utf-8")
        )
    except ValueError as error:
        _emit(sys.stderr, f"{FAILURE_PREFIX} code={_failure_code(error)}\n".encode())
        return EXIT_VALIDATION_FAILURE
    _emit(sys.stdout, encoded)
    return EXIT_SUCCESS


__all__ = [
    "DEMO_HYPOTHESIS_ID",
    "DEMO_ROW_COUNT",
    "EXIT_SUCCESS",
    "EXIT_USAGE_ERROR",
    "EXIT_VALIDATION_FAILURE",
    "FAILURE_PREFIX",
    "build_demo_request",
    "demo_dates",
    "main",
    "run_demo",
]


if __name__ == "__main__":
    raise SystemExit(main())
