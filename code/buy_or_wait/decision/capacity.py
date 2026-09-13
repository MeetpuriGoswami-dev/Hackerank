from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from buy_or_wait.money import quantize_money, to_decimal
from buy_or_wait.models import CandidatePlan, Payment, Profile, SimulationResult
from buy_or_wait.finance.lifecycle import ResolvedCashEvent
from buy_or_wait.finance.simulator import FinanceSimulator


class CapacityCalculator:

    def __init__(self, simulator: FinanceSimulator):
        self.simulator = simulator

    def calculate_amount_safe_to_pay(
        self,
        request_date: date,
        requested_amount: Decimal,
        desired_completion_date: date,
        profile: Profile,
        base_events: List[ResolvedCashEvent],
    ) -> Decimal:
        """Calculates largest amount safe to pay today before optional spending changes."""
        if requested_amount <= Decimal("0"):
            return Decimal("0")

        # Probe helper
        def is_safe_for_amount(amt: Decimal) -> bool:
            if amt <= Decimal("0"):
                return True
            probe_plan = CandidatePlan(
                method="full_payment",
                payments=[Payment(payment_date=request_date, amount=amt)],
                changes=[],
                total_payable=amt,
            )
            sim_res = self.simulator.simulate_90_days(
                request_date=request_date,
                requested_amount=amt,
                desired_completion_date=desired_completion_date,
                profile=profile,
                base_events=base_events,
                plan=probe_plan,
            )
            return sim_res.first_breach_date is None

        # Check full requested amount first
        if is_safe_for_amount(requested_amount):
            return requested_amount

        # Binary search for maximum safe amount
        low = Decimal("0")
        high = requested_amount
        step = Decimal("0.01")
        if profile.home_currency in ("IDR", "INR", "ZAR"):
            step = Decimal("1")  # Integer steps for integer currencies

        best_safe = Decimal("0")

        # Binary search
        iters = 0
        while high - low >= step and iters < 30:
            iters += 1
            mid = quantize_money((low + high) / Decimal("2"), 2)
            if is_safe_for_amount(mid):
                best_safe = mid
                low = mid + step
            else:
                high = mid - step

        return best_safe

    def calculate_earliest_date_for_full_payment(
        self,
        request_date: date,
        requested_amount: Decimal,
        desired_completion_date: date,
        profile: Profile,
        base_events: List[ResolvedCashEvent],
    ) -> Optional[date]:
        """Calculates earliest date within 90-day forecast for one safe full payment (without spending changes)."""
        horizon_end = request_date + timedelta(days=89)
        curr_date = request_date

        while curr_date <= horizon_end:
            probe_plan = CandidatePlan(
                method="full_payment",
                payments=[Payment(payment_date=curr_date, amount=requested_amount)],
                changes=[],
                total_payable=requested_amount,
            )
            sim_res = self.simulator.simulate_90_days(
                request_date=request_date,
                requested_amount=requested_amount,
                desired_completion_date=desired_completion_date,
                profile=profile,
                base_events=base_events,
                plan=probe_plan,
            )
            if sim_res.first_breach_date is None:
                return curr_date

            curr_date += timedelta(days=1)

        return None
