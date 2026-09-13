import re
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from buy_or_wait.models import CandidatePlan


class PlanRanker:

    def extract_option_num(self, opt_id: Optional[str]) -> int:
        if not opt_id:
            return 999999
        nums = re.findall(r"\d+", opt_id)
        if nums:
            return int(nums[0])
        return 999999

    def get_rank_key(
        self, plan: CandidatePlan, desired_completion_date: date
    ) -> Tuple[int, int, Decimal, int, date, int]:
        completion_date = (
            max(p.payment_date for p in plan.payments) if plan.payments else date(9999, 12, 31)
        )
        first_date = (
            min(p.payment_date for p in plan.payments) if plan.payments else date(9999, 12, 31)
        )

        completes_by_deadline = 0 if completion_date <= desired_completion_date else 1
        no_changes = 0 if len(plan.changes) == 0 else 1
        total_paid = plan.total_payable
        num_payments = len(plan.payments)
        opt_num = self.extract_option_num(plan.payment_option_id)

        return (
            completes_by_deadline,
            no_changes,
            total_paid,
            first_date,
            num_payments,
            opt_num,
        )

    def select_best_plan(
        self, safe_plans: List[CandidatePlan], desired_completion_date: date
    ) -> CandidatePlan:
        if not safe_plans:
            return CandidatePlan(
                method="not_recommended",
                payments=[],
                changes=[],
                total_payable=Decimal("0"),
                earliest_date_for_full_payment=None,
            )

        # Sort lexicographically by rank key
        sorted_plans = sorted(
            safe_plans, key=lambda p: self.get_rank_key(p, desired_completion_date)
        )
        return sorted_plans[0]

    def determine_affordability_status(
        self, winning_plan: CandidatePlan, request_date: date
    ) -> str:
        method = winning_plan.method
        if method == "not_recommended":
            return "not_affordable"
        elif method == "wait":
            return "affordable_later"
        elif method == "full_payment":
            if (
                winning_plan.payments
                and winning_plan.payments[0].payment_date == request_date
                and len(winning_plan.changes) == 0
            ):
                return "affordable_now"
            else:
                return "affordable_with_plan"
        elif method in ("partial_payment", "installments"):
            return "affordable_with_plan"
        return "affordable_with_plan"
