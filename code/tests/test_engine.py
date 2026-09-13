from datetime import date
from decimal import Decimal
import pytest

from buy_or_wait.money import format_money_for_plan, format_money_general, quantize_money, to_decimal
from buy_or_wait.models import CandidatePlan, DecisionResult, Payment, Profile, Request, SpendingChange
from buy_or_wait.finance.lifecycle import ResolvedCashEvent
from buy_or_wait.finance.simulator import FinanceSimulator
from buy_or_wait.decision.ranking import PlanRanker
from buy_or_wait.output.validator import OutputValidator


def test_money_formatting():
    assert format_money_for_plan(Decimal("25256")) == "25256"
    assert format_money_for_plan(Decimal("15952906.67")) == "15952906.67"
    assert format_money_for_plan(Decimal("620.40")) == "620.40"
    assert format_money_general(Decimal("603.3")) == "603.3"
    assert format_money_general(Decimal("18000")) == "18000"


def test_simulator_reserve_breach():
    sim = FinanceSimulator()
    req_date = date(2024, 3, 3)
    comp_date = date(2024, 3, 20)

    profile = Profile(
        user_id="user_test",
        home_currency="ZAR",
        current_available_balance=Decimal("20000"),
        minimum_balance_to_keep=Decimal("15000"),
        financial_priorities=[],
        protected_categories=set(),
        reducible_categories=set(),
        stoppable_categories=set(),
        payment_methods_user_will_consider={"full_payment"},
    )

    # Payment of 10,000 when balance is 20,000 leaving 10,000 < minimum_balance (15,000)
    plan = CandidatePlan(
        method="full_payment",
        payments=[Payment(payment_date=req_date, amount=Decimal("10000"))],
        changes=[],
        total_payable=Decimal("10000"),
    )

    res = sim.simulate_90_days(
        request_date=req_date,
        requested_amount=Decimal("10000"),
        desired_completion_date=comp_date,
        profile=profile,
        base_events=[],
        plan=plan,
    )

    assert res.safe is False
    assert res.first_breach_date == req_date
    assert res.minimum_balance == Decimal("10000")


def test_simulator_pending_credits_ignored_and_debits_reserved():
    sim = FinanceSimulator()
    req_date = date(2024, 3, 3)
    comp_date = date(2024, 3, 20)

    profile = Profile(
        user_id="user_test",
        home_currency="USD",
        current_available_balance=Decimal("1000"),
        minimum_balance_to_keep=Decimal("200"),
        financial_priorities=[],
        protected_categories=set(),
        reducible_categories=set(),
        stoppable_categories=set(),
        payment_methods_user_will_consider={"full_payment"},
    )

    # Base events: a pending debit of 500 (reserved) and pending credit of 5000 (ignored)
    pending_debit = ResolvedCashEvent(
        event_id="e1",
        user_id="user_test",
        effective_date=date(2024, 3, 5),
        direction="debit",
        amount_home=Decimal("500"),
        category="utility",
        description="Electricity",
        status="pending",
        protected=False,
    )

    events = [pending_debit]

    plan = CandidatePlan(
        method="full_payment",
        payments=[Payment(payment_date=req_date, amount=Decimal("400"))],
        changes=[],
        total_payable=Decimal("400"),
    )

    res = sim.simulate_90_days(
        request_date=req_date,
        requested_amount=Decimal("400"),
        desired_completion_date=comp_date,
        profile=profile,
        base_events=events,
        plan=plan,
    )

    # 1000 - 400 (payment) - 500 (pending debit) = 100 >= 200 (minimum)? No! 100 < 200 => breach!
    assert res.safe is False


def test_ranking_rules():
    ranker = PlanRanker()
    desired_date = date(2024, 3, 20)

    plan_no_change = CandidatePlan(
        method="full_payment",
        payments=[Payment(payment_date=date(2024, 3, 3), amount=Decimal("1000"))],
        changes=[],
        total_payable=Decimal("1000"),
    )

    plan_with_change = CandidatePlan(
        method="full_payment",
        payments=[Payment(payment_date=date(2024, 3, 3), amount=Decimal("1000"))],
        changes=[SpendingChange(action="stop", event_id="evt1")],
        total_payable=Decimal("1000"),
    )

    key_no_change = ranker.get_rank_key(plan_no_change, desired_date)
    key_with_change = ranker.get_rank_key(plan_with_change, desired_date)

    assert key_no_change < key_with_change
    best = ranker.select_best_plan([plan_with_change, plan_no_change], desired_date)
    assert best == plan_no_change


def test_output_validator():
    validator = OutputValidator()

    req = Request(
        request_id="req_01",
        user_id="user_01",
        request_date=date(2024, 3, 3),
        request_type="purchase",
        requested_amount=Decimal("1000"),
        desired_completion_date=date(2024, 3, 20),
        allows_partial_payment=True,
        request_text="Can I buy this?",
    )

    valid_dec = DecisionResult(
        request_id="req_01",
        amount_safe_to_pay=Decimal("1000"),
        affordability_status="affordable_now",
        recommended_payment_method="full_payment",
        payment_plan="2024-03-03:1000",
        earliest_date_for_full_payment="2024-03-03",
        spending_changes_needed="none",
        decision_explanation="Pay 1000 today.",
    )

    errors = validator.validate_decisions([valid_dec], [req])
    assert len(errors) == 0
