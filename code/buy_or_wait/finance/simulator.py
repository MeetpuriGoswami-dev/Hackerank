from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from buy_or_wait.models import CandidatePlan, Payment, Profile, SimulationResult, SpendingChange
from buy_or_wait.finance.lifecycle import ResolvedCashEvent


class FinanceSimulator:

    def simulate_90_days(
        self,
        request_date: date,
        requested_amount: Decimal,
        desired_completion_date: date,
        profile: Profile,
        base_events: List[ResolvedCashEvent],
        plan: CandidatePlan,
    ) -> SimulationResult:
        """Simulates 90-day daily balance from request_date to request_date + 89 days.

        Enforces minimum_balance_to_keep and desired_completion_date.
        """
        horizon_start = request_date
        horizon_end = request_date + timedelta(days=89)

        # 1. Map spending changes by target event_id or source_event_ids
        stop_events: Set[str] = set()
        reduce_events: Dict[str, Decimal] = {}

        for chg in plan.changes:
            if chg.action == "stop":
                stop_events.add(chg.event_id)
            elif chg.action == "reduce_to" and chg.new_amount is not None:
                reduce_events[chg.event_id] = chg.new_amount

        # 2. Build daily cash flows for the 90 days
        daily_debits: Dict[date, Decimal] = {
            horizon_start + timedelta(days=i): Decimal("0") for i in range(90)
        }
        daily_credits: Dict[date, Decimal] = {
            horizon_start + timedelta(days=i): Decimal("0") for i in range(90)
        }

        # Apply base events
        for evt in base_events:
            d = evt.effective_date
            if d < horizon_start or d > horizon_end:
                continue

            # Historical settled events (effective_date <= request_date) are already reflected in opening balance!
            if evt.status == "settled" and d <= request_date and not evt.is_recurring:
                continue

            # Check if this event or any of its source_event_ids is modified by spending changes
            is_stopped = False
            for src_id in evt.source_event_ids:
                if src_id in stop_events:
                    is_stopped = True
                    break

            if is_stopped:
                continue

            amt = evt.amount_home
            for src_id in evt.source_event_ids:
                if src_id in reduce_events:
                    amt = min(amt, reduce_events[src_id])
                    break

            if evt.direction == "debit":
                daily_debits[d] += amt
            elif evt.direction == "credit":
                daily_credits[d] += amt

        # Apply plan payments
        for pmt in plan.payments:
            d = pmt.payment_date
            if d in daily_debits:
                daily_debits[d] += pmt.amount

        # 3. Simulate day-by-day balance
        current_balance = profile.current_available_balance
        min_balance = current_balance
        min_balance_date = horizon_start
        first_breach_date: Optional[date] = None
        rejection_reasons: List[str] = []

        for i in range(90):
            day = horizon_start + timedelta(days=i)

            # Apply day's debits and credits
            current_balance -= daily_debits[day]
            current_balance += daily_credits[day]

            if current_balance < min_balance:
                min_balance = current_balance
                min_balance_date = day

            if current_balance < profile.minimum_balance_to_keep:
                if first_breach_date is None:
                    first_breach_date = day
                    rejection_reasons.append(
                        f"Balance breached minimum reserve of {profile.minimum_balance_to_keep} on {day} (balance: {current_balance})"
                    )

        # 4. Check completion date & plan total
        plan_total = sum(p.amount for p in plan.payments)
        completion_date = (
            max(p.payment_date for p in plan.payments) if plan.payments else None
        )

        if plan.method != "not_recommended":
            if plan_total < requested_amount:
                rejection_reasons.append(
                    f"Plan total {plan_total} is less than requested amount {requested_amount}"
                )

            if completion_date and completion_date > desired_completion_date:
                rejection_reasons.append(
                    f"Plan completion date {completion_date} is after desired completion date {desired_completion_date}"
                )

        is_safe = (
            first_breach_date is None
            and len(rejection_reasons) == 0
            and plan.method != "not_recommended"
        )

        return SimulationResult(
            safe=is_safe,
            minimum_balance=min_balance,
            minimum_balance_date=min_balance_date,
            ending_balance=current_balance,
            first_breach_date=first_breach_date,
            completion_date=completion_date,
            rejection_reasons=rejection_reasons,
        )
