from decimal import Decimal
from typing import Dict, List

from buy_or_wait.models import DecisionResult, Request

ALLOWED_AFFORDABILITY_STATUS = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

ALLOWED_PAYMENT_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}


class OutputValidator:

    def validate_decisions(
        self, decisions: List[DecisionResult], requests: List[Request]
    ) -> List[str]:
        errors = []
        req_map = {r.request_id: r for r in requests}

        if len(decisions) != len(requests):
            errors.append(
                f"Expected {len(requests)} decisions, got {len(decisions)}"
            )

        seen_ids = set()

        for d in decisions:
            if d.request_id in seen_ids:
                errors.append(f"Duplicate request_id in output: {d.request_id}")
            seen_ids.add(d.request_id)

            if d.request_id not in req_map:
                errors.append(f"Unknown request_id in output: {d.request_id}")
                continue

            req = req_map[d.request_id]

            # 1. Check amount_safe_to_pay bounds
            if not (Decimal("0") <= d.amount_safe_to_pay <= req.requested_amount):
                errors.append(
                    f"Request {d.request_id}: amount_safe_to_pay {d.amount_safe_to_pay} out of bounds [0, {req.requested_amount}]"
                )

            # 2. Check enums
            if d.affordability_status not in ALLOWED_AFFORDABILITY_STATUS:
                errors.append(
                    f"Request {d.request_id}: invalid affordability_status {d.affordability_status}"
                )

            if d.recommended_payment_method not in ALLOWED_PAYMENT_METHODS:
                errors.append(
                    f"Request {d.request_id}: invalid recommended_payment_method {d.recommended_payment_method}"
                )

            # 3. Check partial_payment 2-payment rule
            if d.recommended_payment_method == "partial_payment":
                if d.affordability_status != "affordable_with_plan":
                    errors.append(
                        f"Request {d.request_id}: partial_payment must have affordability_status affordable_with_plan"
                    )
                parts = d.payment_plan.split("|")
                if len(parts) != 2:
                    errors.append(
                        f"Request {d.request_id}: partial_payment must have exactly 2 payments in plan, got {len(parts)}"
                    )

            # 4. Check not_recommended payment plan
            if d.recommended_payment_method == "not_recommended":
                if d.payment_plan != "none":
                    errors.append(
                        f"Request {d.request_id}: not_recommended must have payment_plan=none"
                    )

            # 5. Check spending changes limit
            if d.spending_changes_needed != "none":
                chgs = d.spending_changes_needed.split("|")
                if len(chgs) > 3:
                    errors.append(
                        f"Request {d.request_id}: spending_changes_needed exceeds max 3 changes"
                    )

        return errors
