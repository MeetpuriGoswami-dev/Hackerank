from decimal import Decimal
from typing import List

from buy_or_wait.money import format_money_for_plan, format_money_general
from buy_or_wait.models import CandidatePlan, Profile, Request, SimulationResult, SpendingChange
from buy_or_wait.finance.lifecycle import ResolvedCashEvent


class ExplanationGenerator:

    def generate_explanation(
        self,
        request: Request,
        profile: Profile,
        plan: CandidatePlan,
        sim_result: SimulationResult,
        base_events: List[ResolvedCashEvent],
    ) -> str:
        curr = profile.home_currency
        min_bal = format_money_general(profile.minimum_balance_to_keep)
        min_proj = format_money_general(sim_result.minimum_balance)
        req_amt = format_money_general(request.requested_amount)

        # Build spending change clause if any
        change_clauses = []
        for chg in plan.changes:
            # find event description
            desc = "recurring expense"
            for evt in base_events:
                if (evt.source_event_ids and chg.event_id in evt.source_event_ids) or evt.event_id == chg.event_id:
                    desc = evt.description
                    break
            
            # Clean description text
            desc = desc.replace("[Projected] ", "").strip()
            if chg.action == "stop":
                change_clauses.append(f"Stop the {desc.lower()}")
            elif chg.action == "reduce_to" and chg.new_amount is not None:
                new_amt_str = format_money_general(chg.new_amount)
                change_clauses.append(f"Reduce the {desc.lower()} to {curr} {new_amt_str}")

        change_prefix = ""
        if change_clauses:
            change_prefix = ", ".join(change_clauses) + ", then "

        # Method specific explanations
        if plan.method == "not_recommended":
            deadline_str = request.desired_completion_date.strftime("%d %B %Y").lstrip("0")
            return (
                f"Do not make this payment by {deadline_str}. "
                f"None of the available options keeps the {curr} {min_bal} minimum protected."
            )

        elif plan.method == "full_payment":
            if plan.payments and plan.payments[0].payment_date == request.request_date:
                if change_prefix:
                    return (
                        f"{change_prefix.capitalize()}pay {curr} {req_amt} today. "
                        f"This leaves at least {curr} {min_proj} available."
                    )
                else:
                    return (
                        f"Pay {curr} {req_amt} today. "
                        f"This leaves at least {curr} {min_bal} available over the next 90 days."
                    )

        elif plan.method == "partial_payment":
            if len(plan.payments) == 2:
                p1_amt = format_money_general(plan.payments[0].amount)
                p2_amt = format_money_general(plan.payments[1].amount)
                p2_date_str = plan.payments[1].payment_date.strftime("%d %B %Y").lstrip("0")
                return (
                    f"Pay {curr} {p1_amt} today and the remaining {curr} {p2_amt} on {p2_date_str}. "
                    f"This completes the full request and keeps the {curr} {min_bal} minimum protected."
                )

        elif plan.method == "installments":
            n_pmts = len(plan.payments)
            inst_amt = format_money_for_plan(plan.payments[0].amount) if plan.payments else req_amt
            first_date_str = plan.payments[0].payment_date.strftime("%d %B %Y").lstrip("0") if plan.payments else ""
            return (
                f"Use {n_pmts} installments of {curr} {inst_amt}, starting {first_date_str}. "
                f"This leaves at least {curr} {min_proj} available."
            )

        elif plan.method == "wait":
            wait_date = plan.payments[0].payment_date.strftime("%d %B %Y").lstrip("0") if plan.payments else ""
            return (
                f"Pay {curr} {req_amt} in full on {wait_date}. "
                f"Paying earlier would take the balance below the {curr} {min_bal} minimum."
            )

        return f"Pay {curr} {req_amt} as recommended."
