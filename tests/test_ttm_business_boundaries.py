"""Independent arithmetic and visibility invariants for the shared PE/PS TTM engine."""

from copy import deepcopy
from itertools import permutations

import pytest

from ashare_research.pit_valuation.financial_state import build_pe_states, build_ps_states


@pytest.fixture(params=[("net_profit_attributable_to_parent", build_pe_states),
                        ("revenue", build_ps_states)])
def engine(request):
    concept, build = request.param

    def run(facts):
        return build([{**fact, "concept_id": concept} for fact in facts])

    return run


def fact(fid, period, effective, value, supersedes=""):
    return dict(fact_id=fid, period_end=period, effective_from=effective,
                available_at=effective, value=str(value), supersedes_fact_id=supersedes)


def inputs():
    return [fact("prior", "2024-03-31", "2024-04-30", 10),
            fact("z-old", "2024-12-31", "2025-04-01", 100),
            fact("a-new", "2024-12-31", "2025-04-01", 200, "z-old"),
            fact("current", "2025-03-31", "2025-04-30", 40)]


def q1(states):
    return [s for s in states if s["period_end"] == "2025-03-31"]


def test_supersession_controls_annual_and_interim_values_in_any_order(engine):
    expected = None
    for ordered in permutations(inputs()):
        states = engine(ordered)
        annual = [s for s in states if s["period_end"] == "2024-12-31"]
        assert len(annual) == 1
        assert annual[0]["value_decimal"] == "200"
        current = q1(states)[0]
        assert current["value_decimal"] == "230"
        assert current["input_fact_ids"] == ["a-new", "current", "prior"]
        assert current["available_at_max"] == "2025-04-30"
        if expected is None:
            expected = states
        assert states == expected


@pytest.mark.parametrize("slot, new_value, expected", [(0, 20, "120"), (3, 60, "150")])
def test_current_and_prior_cumulative_use_same_day_successor(engine, slot, new_value, expected):
    rows = inputs()
    rows.pop(2)
    original = rows[0 if slot == 0 else 2]
    rows.append({**original, "fact_id": "0-successor", "value": str(new_value),
                 "supersedes_fact_id": original["fact_id"]})
    assert q1(engine(rows))[0]["value_decimal"] == expected


def test_three_versions_and_renamed_ids_preserve_economic_result(engine):
    rows = inputs()
    rows.append(fact("0-final", "2024-12-31", "2025-04-01", 300, "a-new"))
    first = q1(engine(rows))[0]
    assert first["value_decimal"] == "330"
    renamed = {row["fact_id"]: f"renamed-{i}" for i, row in enumerate(reversed(rows))}
    for row in rows:
        row["fact_id"] = renamed[row["fact_id"]]
        row["supersedes_fact_id"] = renamed.get(row["supersedes_fact_id"], "")
    second = q1(engine(rows))[0]
    assert second["value_decimal"] == first["value_decimal"]
    assert second["effective_from"] == first["effective_from"]
    assert second["input_fact_ids"] == sorted(renamed[f] for f in first["input_fact_ids"])


@pytest.mark.parametrize("problem", ["unrelated", "fork", "cycle", "self", "duplicate_id"])
def test_ambiguous_or_conflicting_versions_fail_closed(engine, problem):
    rows = inputs()
    if problem == "unrelated":
        rows[2]["supersedes_fact_id"] = ""
    elif problem == "fork":
        rows.append(fact("other", "2024-12-31", "2025-04-01", 300, "z-old"))
    elif problem == "cycle":
        rows[1]["supersedes_fact_id"] = "a-new"
    elif problem == "self":
        rows[2]["supersedes_fact_id"] = "a-new"
    else:
        rows.append({**rows[2], "value": "999"})
    with pytest.raises(ValueError, match="a-new"):
        engine(rows)


def test_later_restatement_changes_only_later_states(engine):
    rows = inputs()
    rows[2]["effective_from"] = rows[2]["available_at"] = "2025-05-15"
    baseline = q1(engine([r for r in rows if r["fact_id"] != "a-new"]))[0]
    states = q1(engine(list(reversed(rows))))
    assert states[0] == baseline
    assert [s["value_decimal"] for s in states] == ["130", "230"]
    assert states[1]["effective_from"] == "2025-05-15"


@pytest.mark.parametrize("missing_slot", [0, 1])
def test_late_dependency_transitions_without_future_lineage(engine, missing_slot):
    rows = inputs()
    rows.pop(2)
    delayed = rows[missing_slot]
    delayed["available_at"] = delayed["effective_from"] = "2025-05-15"
    before_rows = [r for r in rows if r is not delayed]
    before = q1(engine(before_rows))[0]
    states = q1(engine(rows))
    assert states[0] == before
    assert states[0]["status"] == "missing_ttm_input"
    assert states[0]["value_decimal"] is None
    assert delayed["fact_id"] not in states[0]["input_fact_ids"]
    assert states[0]["available_at_max"] == "2025-04-30"
    assert states[1]["value_decimal"] == "130"
    assert states[1]["status"] == "computed"
    assert states[1]["effective_from"] == "2025-05-15"
    assert states[1]["available_at_max"] == "2025-05-15"


def test_permanent_missing_input_keeps_visible_lineage_and_updates(engine):
    rows = inputs()[1:]
    rows.append(fact("current-v2", "2025-03-31", "2025-05-15", 45, "current"))
    states = q1(engine(rows))
    assert len(states) == 2
    assert all(s["status"] == "missing_ttm_input" for s in states)
    assert all(s["value_decimal"] is None for s in states)
    assert states[0]["input_fact_ids"] == ["a-new", "current"]
    assert states[1]["input_fact_ids"] == ["a-new", "current-v2"]


def test_transition_at_next_period_start_does_not_extend_old_window(engine):
    rows = inputs()
    rows[0]["effective_from"] = rows[0]["available_at"] = "2025-08-01"
    rows.extend([fact("prior-h1", "2024-06-30", "2024-08-01", 25),
                 fact("current-h1", "2025-06-30", "2025-08-01", 70)])
    original = deepcopy(rows)
    states = engine(rows)
    assert rows == original
    assert len(q1(states)) == 1
    assert q1(states)[0]["status"] == "missing_ttm_input"
    h1 = [s for s in states if s["period_end"] == "2025-06-30"]
    assert h1[0]["value_decimal"] == "245"
