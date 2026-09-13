import itertools
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from buy_or_wait.models import CandidatePlan, Profile, SpendingChange
from buy_or_wait.finance.lifecycle import ResolvedCashEvent
from buy_or_wait.finance.simulator import FinanceSimulator


class SpendingOptimizer:

    def __init__(self, simulator: FinanceSimulator):
        self.simulator = simulator

    def find_minimal_spending_changes(
        self,
        request_date: date,
        requested_amount: Decimal,
        desired_completion_date: date,
        profile: Profile,
        base_events: List[ResolvedCashEvent],
        candidate_plan: CandidatePlan,
    ) -> Optional[List[SpendingChange]]:
        """Finds minimal spending changes (up to 3) that make candidate_plan safe."""
        # 1. First check if candidate_plan is already safe without changes
        sim_no_change = self.simulator.simulate_90_days(
            request_date=request_date,
            requested_amount=requested_amount,
            desired_completion_date=desired_completion_date,
            profile=profile,
            base_events=base_events,
            plan=candidate_plan,
        )
        if sim_no_change.safe:
            return []

        # 2. Collect eligible candidate actions from recurring debit events
        eligible_actions: List[SpendingChange] = []

        # Deduplicate target events by event_id or source_event_ids
        seen_targets = set()
        for evt in base_events:
            if evt.direction != "debit":
                continue
            if evt.category in profile.protected_categories:
                continue

            flex = (evt.flexibility or "").lower()
            if flex == "fixed":
                continue

            target_id = evt.source_event_ids[0] if evt.source_event_ids else evt.event_id
            if target_id in seen_targets:
                continue
            seen_targets.add(target_id)

            can_reduce = (
                "reducible" in flex
                and evt.category in profile.reducible_categories
            )
            can_stop = (
                "stoppable" in flex
                and evt.category in profile.stoppable_categories
            )

            if can_stop:
                eligible_actions.append(
                    SpendingChange(action="stop", event_id=target_id)
                )

            if can_reduce:
                # Minimum allowed amount
                min_amt = evt.minimum_allowed_amount or Decimal("0")
                if evt.amount_home > min_amt:
                    eligible_actions.append(
                        SpendingChange(
                            action="reduce_to",
                            event_id=target_id,
                            new_amount=min_amt,
                        )
                    )

        if not eligible_actions:
            return None

        # 3. Test combinations of size 1, 2, 3
        for k in range(1, min(4, len(eligible_actions) + 1)):
            for comb in itertools.combinations(eligible_actions, k):
                # Ensure no duplicate event_ids in combination
                event_ids = [chg.event_id for chg in comb]
                if len(set(event_ids)) < len(event_ids):
                    continue

                test_plan = CandidatePlan(
                    method=candidate_plan.method,
                    payments=candidate_plan.payments,
                    changes=list(comb),
                    payment_option_id=candidate_plan.payment_option_id,
                    total_payable=candidate_plan.total_payable,
                    earliest_date_for_full_payment=candidate_plan.earliest_date_for_full_payment,
                )

                sim_res = self.simulator.simulate_90_days(
                    request_date=request_date,
                    requested_amount=requested_amount,
                    desired_completion_date=desired_completion_date,
                    profile=profile,
                    base_events=base_events,
                    plan=test_plan,
                )
                if sim_res.safe:
                    return list(comb)

        return None
