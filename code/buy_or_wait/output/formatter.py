from decimal import Decimal
from typing import List, Optional

from buy_or_wait.money import format_money_for_plan, format_money_general
from buy_or_wait.models import CandidatePlan, DecisionResult, Request


class OutputFormatter:

    def format_decision(
        self,
        request: Request,
        amount_safe_to_pay: Decimal,
        affordability_status: str,
        winning_plan: CandidatePlan,
        earliest_date_for_full_payment: Optional[object],
        explanation: str,
    ) -> DecisionResult:
        req_id = request.request_id

        # Format amount_safe_to_pay
        amt_safe_str = format_money_general(amount_safe_to_pay)

        # Format payment_plan
        if winning_plan.method == "not_recommended" or not winning_plan.payments:
            plan_str = "none"
        else:
            parts = []
            for pmt in winning_plan.payments:
                date_str = pmt.payment_date.strftime("%Y-%m-%d")
                amt_str = format_money_for_plan(pmt.amount)
                parts.append(f"{date_str}:{amt_str}")
            plan_str = "|".join(parts)

        # Format earliest_date_for_full_payment
        if affordability_status == "affordable_now":
            earliest_str = request.request_date.strftime("%Y-%m-%d")
        elif earliest_date_for_full_payment:
            earliest_str = earliest_date_for_full_payment.strftime("%Y-%m-%d")
        else:
            earliest_str = ""

        # Format spending_changes_needed
        if winning_plan.changes:
            chg_parts = [chg.to_string() for chg in winning_plan.changes]
            changes_str = "|".join(chg_parts)
        else:
            changes_str = "none"

        return DecisionResult(
            request_id=req_id,
            amount_safe_to_pay=amount_safe_to_pay,
            affordability_status=affordability_status,
            recommended_payment_method=winning_plan.method,
            payment_plan=plan_str,
            earliest_date_for_full_payment=earliest_str,
            spending_changes_needed=changes_str,
            decision_explanation=explanation,
        )
