from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from .lifecycle import ResolvedCashEvent

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
    "gym",
    "music_subscription",
    "delivery_membership",
    "streaming",
    "cloud_storage",
    "groceries",
    "transport",
    "dining",
    "entertainment",
    "shopping",
}

# Categories where we project a SINGLE fixed-amount stream (not variable)
FIXED_AMOUNT_CATEGORIES = {
    "rent", "salary", "income", "insurance", "subscription",
    "debt_repayment", "gym", "music_subscription", "delivery_membership",
    "streaming", "cloud_storage",
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
    "reimburse",
}


def add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    max_days = [
        31,
        29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    ][month - 1]
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
        """Infers recurring patterns from historical events and projects future occurrences.

        Groups events by (category, direction) to avoid double-counting multiple
        sub-streams within the same category. Projects ONE consolidated monthly
        stream per (category, direction) pair.
        """

        # Step 1: Build per-category groups using ONLY settled historical events.
        # Use (category, direction) as the primary key.
        # For fine-grained categories (rent, salary, gym, etc.) we preserve
        # per-description granularity because each description represents a
        # distinct, independent commitment (e.g. different credit cards).
        # For variable categories (groceries, transport, dining) we consolidate.

        # Check if user has a final payroll event marking employment end
        user_terminated_cats = set(terminated_categories)
        for evt in historical_events:
            desc_l = evt.description.lower()
            if any(kw in desc_l for kw in ("final employer payroll", "final payroll", "final salary", "final settlement", "final pay")):
                user_terminated_cats.add("salary")
                user_terminated_cats.add("income")

        # First pass: group by (category, direction, description)
        desc_groups: Dict[tuple, List[ResolvedCashEvent]] = {}
        for evt in historical_events:
            cat = evt.category.lower()
            direction = evt.direction.lower()
            is_income = direction == "credit" and (cat in ("salary", "income") or "salary" in evt.description.lower())

            # Only use settled events (or scheduled events for salary/income) to infer patterns
            if is_income:
                if evt.status not in ("settled", "scheduled"):
                    continue
            else:
                if evt.status not in ("settled",):
                    continue

            if cat in user_terminated_cats:
                continue

            desc_norm = evt.description.strip().lower()

            # Skip non-recurring by keyword
            if is_income:
                income_non_recurring = {
                    "bonus", "gift", "refund", "reimburse", "one-time", "one time", "one off", "one-off",
                    "lottery", "arrears", "promotion", "back-pay", "backpay", "sign-on", "severance", "commission",
                    "final employer payroll", "final payroll", "final salary", "final settlement", "final pay"
                }
                if any(kw in desc_norm for kw in income_non_recurring):
                    continue
            else:
                if any(kw in desc_norm for kw in NON_RECURRING_KEYWORDS):
                    continue

            key = (cat, direction, desc_norm)
            if key not in desc_groups:
                desc_groups[key] = []
            desc_groups[key].append(evt)

        # Step 2: Decide which desc-level groups are genuinely recurring
        # (require >= 2 occurrences, cadence <= 45 days, except salary/income)
        valid_desc_groups: Dict[tuple, List[ResolvedCashEvent]] = {}
        for key, evts in desc_groups.items():
            cat, direction, desc = key
            is_income = direction == "credit" and (cat in ("salary", "income") or "salary" in desc)

            if not is_income and len(evts) < 2:
                continue

            sorted_evts = sorted(evts, key=lambda x: x.effective_date)
            cadence, _ = self._estimate_cadence_full(sorted_evts, is_income)
            if cadence is None:
                continue

            valid_desc_groups[key] = sorted_evts

        # Step 3: For variable categories, consolidate all desc-streams into one
        # monthly aggregate per (category, direction).
        VARIABLE_CATEGORIES = {
            "groceries", "transport", "dining", "entertainment", "shopping",
        }

        # We'll collect projected events into a list
        projected: List[ResolvedCashEvent] = []

        # Track what (category, direction) pairs have been handled to avoid
        # duplication between desc-level and aggregated paths.
        handled_cat_dirs: Set[Tuple[str, str]] = set()

        # Process variable categories first (aggregate)
        cat_dir_groups: Dict[Tuple[str, str], Dict[str, List[ResolvedCashEvent]]] = {}
        for key, evts in valid_desc_groups.items():
            cat, direction, desc = key
            if cat not in VARIABLE_CATEGORIES:
                continue
            cd_key = (cat, direction)
            if cd_key not in cat_dir_groups:
                cat_dir_groups[cd_key] = {}
            cat_dir_groups[cd_key][desc] = evts

        for (cat, direction), desc_map in cat_dir_groups.items():
            handled_cat_dirs.add((cat, direction))

            # Gather all settled events in historical_events for this (cat, direction)
            all_cat_evts = [
                e for e in historical_events
                if e.status == "settled" and e.category.lower() == cat and e.direction.lower() == direction
            ]
            if not all_cat_evts:
                continue

            all_cat_evts.sort(key=lambda x: x.effective_date)
            min_date = all_cat_evts[0].effective_date
            max_date = request_date
            days_span = max(30, (max_date - min_date).days)

            total_spent = sum(e.amount_home for e in all_cat_evts)
            monthly_total = total_spent * Decimal("30") / Decimal(str(days_span))

            if monthly_total <= Decimal("0"):
                continue

            representative_evt = all_cat_evts[-1]
            all_source_ids = tuple(e.event_id for e in all_cat_evts)

            # Project daily payments (monthly_total / 30) starting from request_date + 1
            daily_amount = monthly_total / Decimal("30")
            proj_count = 1
            curr_proj_date = request_date + timedelta(days=1)

            while curr_proj_date <= horizon_end_date:
                proj_id = f"proj_{cat}_{direction}_{proj_count}"
                proj_evt = ResolvedCashEvent(
                    event_id=proj_id,
                    user_id=representative_evt.user_id,
                    effective_date=curr_proj_date,
                    direction=direction,
                    amount_home=daily_amount,
                    category=cat,
                    description=f"[Projected] {cat} daily",
                    status="scheduled",
                    protected=representative_evt.protected,
                    flexibility=representative_evt.flexibility,
                    minimum_allowed_amount=None,
                    source_event_ids=all_source_ids,
                    is_recurring=True,
                )
                projected.append(proj_evt)
                proj_count += 1
                curr_proj_date += timedelta(days=1)

        # Process fixed / distinct categories (one stream per description)
        for key, evts in valid_desc_groups.items():
            cat, direction, desc = key
            cd_key = (cat, direction)
            if cd_key in handled_cat_dirs:
                continue  # already aggregated

            sorted_evts = sorted(evts, key=lambda x: x.effective_date)
            last_evt = sorted_evts[-1]
            is_income = direction == "credit" and (cat in ("salary", "income") or "salary" in desc)
            cadence, is_monthly = self._estimate_cadence_full(sorted_evts, is_income)

            if cadence is None or cadence <= 0:
                continue

            base_proj_amount = last_evt.amount_home
            proj_min_amount = last_evt.minimum_allowed_amount
            flexibility = last_evt.flexibility
            protected = last_evt.protected
            src_ids = tuple(e.event_id for e in sorted_evts)

            salary_amend = None
            if is_income and user_salary_amendments and last_evt.user_id in user_salary_amendments:
                salary_amend = user_salary_amendments[last_evt.user_id]

            proj_count = 1
            month_offset = 1
            day_offset = cadence

            while True:
                if is_monthly:
                    next_date = add_months(last_evt.effective_date, month_offset)
                    month_offset += 1
                else:
                    next_date = last_evt.effective_date + timedelta(days=day_offset)
                    day_offset += cadence

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

    def _estimate_cadence(self, sorted_evts: List[ResolvedCashEvent]) -> Optional[int]:
        """Returns cadence in days, or None if not recurring."""
        cadence, _ = self._estimate_cadence_full(sorted_evts, False)
        return cadence

    def _estimate_cadence_full(
        self,
        sorted_evts: List[ResolvedCashEvent],
        is_income: bool,
    ) -> Tuple[Optional[int], bool]:
        """Returns (cadence_days, is_monthly). Returns (None, False) if not valid."""
        if len(sorted_evts) < 2 and not is_income:
            return None, False

        is_monthly = False
        cadence_days = 30

        if len(sorted_evts) >= 2:
            intervals = []
            for i in range(1, len(sorted_evts)):
                diff = (sorted_evts[i].effective_date - sorted_evts[i - 1].effective_date).days
                if diff > 0:
                    intervals.append(diff)
            if not intervals:
                return None, False
            avg_interval = sum(intervals) / len(intervals)
            if 5 <= avg_interval <= 9:
                cadence_days = 7
            elif 12 <= avg_interval <= 16:
                cadence_days = 14
            elif 27 <= avg_interval <= 33:
                is_monthly = True
                cadence_days = 30
            elif avg_interval <= 45:
                cadence_days = int(round(avg_interval))
            else:
                # Interval too long to be reliably recurring
                return None, False
        else:
            # Single income event: assume monthly
            is_monthly = True
            cadence_days = 30

        return cadence_days, is_monthly
