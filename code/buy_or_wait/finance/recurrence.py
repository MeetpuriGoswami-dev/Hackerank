from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set

from .lifecycle import ResolvedCashEvent

RECURRING_EVENT_TYPES = {"subscription", "income", "debt payment", "rent", "salary"}
RECURRING_CATEGORIES = {
    "rent",
    "utilities",
    "education",
    "housing",
    "insurance",
    "subscription",
    "debt_repayment",
    "salary",
    "income",
    "membership",
}

NON_RECURRING_KEYWORDS = {
    "prorated",
    "one-time",
    "one time",
    "one off",
    "one-off",
    "bonus",
    "arrears",
    "sign-on",
    "adjustment",
    "deposit",
    "initial",
    "first salary",
    "gift",
    "refund",
}


def add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    max_days = [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    day = min(d.day, max_days)
    return date(year, month, day)


class RecurrenceEngine:

    def infer_and_project_recurrences(
        self,
        historical_events: List[ResolvedCashEvent],
        request_date: date,
        horizon_end_date: date,
        terminated_categories: Set[str],
        user_salary_amendments: Optional[Dict[str, Dict]] = None,
    ) -> List[ResolvedCashEvent]:
        """Infers recurring patterns from historical events and projects future occurrences
        up to horizon_end_date.
        """
        groups: Dict[tuple, List[ResolvedCashEvent]] = {}
        for evt in historical_events:
            cat = evt.category.lower()
            if cat in terminated_categories:
                continue

            desc_norm = evt.description.strip().lower()

            # Ignore one-time / non-recurring keywords
            if any(kw in desc_norm for kw in NON_RECURRING_KEYWORDS):
                continue

            key = (cat, evt.direction.lower(), desc_norm)
            if key not in groups:
                groups[key] = []
            groups[key].append(evt)

        projected: List[ResolvedCashEvent] = []

        for key, evts in groups.items():
            cat, direction, desc = key

            sorted_evts = sorted(evts, key=lambda x: x.effective_date)
            last_evt = sorted_evts[-1]

            is_income = direction == "credit" and (cat in ("salary", "income") or "salary" in desc)

            # Require at least 2 events for non-income recurring candidates
            if not is_income and len(evts) < 2:
                continue

            is_monthly = False
            cadence_days = 30

            if len(evts) >= 2:
                intervals = []
                for i in range(1, len(sorted_evts)):
                    diff = (sorted_evts[i].effective_date - sorted_evts[i - 1].effective_date).days
                    if diff > 0:
                        intervals.append(diff)
                avg_interval = sum(intervals) / len(intervals) if intervals else 30
                if 5 <= avg_interval <= 9:
                    cadence_days = 7
                elif 12 <= avg_interval <= 16:
                    cadence_days = 14
                elif 27 <= avg_interval <= 33:
                    is_monthly = True
                    cadence_days = 30
                else:
                    cadence_days = int(round(avg_interval))
            else:
                is_monthly = True
                cadence_days = 30

            if cadence_days <= 0 or cadence_days > 45:
                continue

            base_proj_amount = last_evt.amount_home
            proj_min_amount = last_evt.minimum_allowed_amount
            flexibility = last_evt.flexibility
            protected = last_evt.protected
            src_ids = tuple(e.event_id for e in sorted_evts)

            # Apply user-level salary amendments if applicable
            salary_amend = None
            if is_income and user_salary_amendments and last_evt.user_id in user_salary_amendments:
                salary_amend = user_salary_amendments[last_evt.user_id]

            proj_count = 1
            month_offset = 1
            day_offset = cadence_days

            while True:
                if is_monthly:
                    next_date = add_months(last_evt.effective_date, month_offset)
                    month_offset += 1
                else:
                    next_date = last_evt.effective_date + timedelta(days=day_offset)
                    day_offset += cadence_days

                if next_date > horizon_end_date:
                    break

                if next_date >= request_date:
                    curr_amt = base_proj_amount
                    if salary_amend and "amount" in salary_amend:
                        eff_date = salary_amend.get("effective_date")
                        if eff_date is None or next_date >= eff_date:
                            curr_amt = salary_amend["amount"]

                    proj_id = f"proj_{last_evt.event_id}_{proj_count}"
                    proj_evt = ResolvedCashEvent(
                        event_id=proj_id,
                        user_id=last_evt.user_id,
                        effective_date=next_date,
                        direction=direction,
                        amount_home=curr_amt,
                        category=last_evt.category,
                        description=f"[Projected] {last_evt.description}",
                        status="scheduled",
                        protected=protected,
                        flexibility=flexibility,
                        minimum_allowed_amount=proj_min_amount,
                        source_event_ids=src_ids,
                        is_recurring=True,
                    )
                    projected.append(proj_evt)
                    proj_count += 1

        return projected
