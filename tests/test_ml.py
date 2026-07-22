"""Rung 2 risk model: deterministic, honestly measured, and exactly explained (docs/ml).

No database — the model is a pure function of the population, and these tests keep it that
way. They assert the three things a reviewer (or an auditor) needs to trust a score: it is
reproducible, its performance is measured not asserted, and its explanation has the Shapley
axioms rather than a plausible-looking bar chart.
"""

from decimal import Decimal

from taxos_core.ml import FEATURE_NAMES, RiskModel, score_population
from taxos_core.ml.explain import shapley_attributions
from taxos_core.ml.features import extract_features
from taxos_core.ml.synth import make_benchmark, precision_at_k
from taxos_core.risk.detectors import Transaction


def _txn(row_id, cp, net, vat):
    return Transaction(
        row_id=row_id,
        document_ref=row_id,
        counterparty=cp,
        net_amount=Decimal(net),
        vat_amount=Decimal(vat),
        vat_code="S20",
    )


# --- reproducibility ----------------------------------------------------------


def test_scores_are_reproducible_for_the_same_population():
    """A score a reviewer cannot reproduce is one they cannot defend. Same in, same out."""
    bench = make_benchmark()
    first = score_population(bench.transactions)
    second = score_population(bench.transactions)
    assert [r.score for r in first] == [r.score for r in second]
    assert [r.row_id for r in first] == [r.row_id for r in second]


def test_row_order_does_not_change_the_scores():
    """Re-fetching the population in a different order must not move a score."""
    bench = make_benchmark(n=120, n_anomalies=8)
    forward = {r.row_id: r.score for r in score_population(bench.transactions)}
    reversed_pop = list(reversed(bench.transactions))
    backward = {r.row_id: r.score for r in score_population(reversed_pop)}
    assert forward == backward


# --- honest performance -------------------------------------------------------


def test_model_recovers_planted_anomalies_far_above_chance():
    """Measured, not asserted: on a labelled synthetic population the model concentrates the
    planted anomalies in the top ranks. Chance precision@20 here is 20/400 = 5%."""
    bench = make_benchmark(n=400, n_anomalies=20)
    scored = score_population(bench.transactions)
    ranked_ids = [r.row_id for r in scored]  # already most-anomalous first

    p_at_20 = precision_at_k(ranked_ids, bench.planted, 20)
    assert p_at_20 >= 0.70, f"precision@20 was {p_at_20:.0%}, expected the model to beat chance"


def test_flagged_lines_are_the_high_scoring_ones():
    bench = make_benchmark(n=200, n_anomalies=12)
    scored = score_population(bench.transactions)
    flagged = [r for r in scored if r.flagged]
    unflagged = [r for r in scored if not r.flagged]
    assert flagged and unflagged
    assert min(r.score for r in flagged) >= max(r.score for r in unflagged)


# --- exact Shapley explanation ------------------------------------------------


def test_shapley_values_satisfy_the_efficiency_axiom():
    """The parts sum to the whole: attributions total the score gap from the baseline. This is
    what makes them Shapley values rather than a plausible-looking attribution."""
    bench = make_benchmark(n=150, n_anomalies=10)
    matrix, row_ids = extract_features(bench.transactions)
    model = RiskModel().fit(matrix)
    baseline = [sorted(col)[len(col) // 2] for col in zip(*matrix, strict=True)]

    for i in range(0, len(matrix), 15):  # sample across the population
        attributions = shapley_attributions(matrix[i], baseline, FEATURE_NAMES, model.score_batch)
        total = sum(a.contribution for a in attributions)
        gap = model.score_one(matrix[i]) - model.score_one(baseline)
        assert abs(total - gap) < 1e-9


def test_flagged_lines_carry_a_full_shapley_explanation():
    bench = make_benchmark(n=100, n_anomalies=6)
    scored = score_population(bench.transactions)
    for r in scored:
        assert r.reason  # every line says something, even "within the normal range"
        if r.flagged:
            # A flagged line a reviewer will open carries an attribution over every feature.
            assert {a.feature for a in r.attributions} == set(FEATURE_NAMES)


def test_mis_coded_vat_is_explained_by_the_vat_ratio_feature():
    """A planted mis-coded-VAT line should attribute chiefly to vat_ratio — the explanation
    points at the real reason, which is the whole purpose of storing one."""
    # A population where one Supplier-A line carries a wrong VAT ratio.
    population = [_txn(f"n{i}", "Supplier A", "10000.00", "2000.00") for i in range(20)]
    population.append(_txn("odd", "Supplier A", "10000.00", "500.00"))  # ratio 0.05, not 0.20
    scored = {r.row_id: r for r in score_population(population)}
    odd = scored["odd"]
    assert odd.flagged
    assert odd.attributions[0].feature == "vat_ratio"


# --- ML-1: advises, never decides ---------------------------------------------


def test_risk_score_has_no_decision_field():
    """The governance is structural: the score type cannot carry a disposition, so the model
    literally cannot record a decision. A human does that elsewhere."""
    from taxos_core.ml.scoring import RiskScore

    fields = set(RiskScore.__dataclass_fields__)
    for forbidden in ("disposition", "decision", "approved", "action", "resolved"):
        assert forbidden not in fields
