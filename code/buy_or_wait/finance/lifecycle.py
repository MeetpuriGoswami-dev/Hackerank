from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from buy_or_wait.models import FinancialEvent, Profile
from buy_or_wait.finance.currency import CurrencyConverter


class ResolvedCashEvent:

    def __init__(
        self,
        event_id: str,
        user_id: str,
        effective_date: date,
        direction: str,  # "credit" or "debit"
        amount_home: Decimal,
        category: str,
        description: str,
        status: str,
        protected: bool,
        flexibility: Optional[str] = None,
        minimum_allowed_amount: Optional[Decimal] = None,
        source_event_ids: Optional[Tuple[str, ...]] = None,
        is_recurring: bool = False,
    ):
        self.event_id = event_id
        self.user_id = user_id
        self.effective_date = effective_date
        self.direction = direction
        self.amount_home = amount_home
        self.category = category
        self.description = description
        self.status = status
        self.protected = protected
        self.flexibility = flexibility
        self.minimum_allowed_amount = minimum_allowed_amount
        self.source_event_ids = source_event_ids or (event_id,)
        self.is_recurring = is_recurring


class EventLifecycleResolver:

    def __init__(self, currency_converter: CurrencyConverter):
        self.converter = currency_converter

    def resolve_events_for_user(
        self,
        user_id: str,
        events: List[FinancialEvent],
        profile: Profile,
        image_amounts: Dict[str, Decimal],
        message_amendments: Dict[str, Dict],
        request_date: Optional[date] = None,
    ) -> List[ResolvedCashEvent]:
        """Resolves raw financial events for a user into normalized home-currency cash events."""
        resolved: List[ResolvedCashEvent] = []

        events_by_id: Dict[str, FinancialEvent] = {}
        for evt in events:
            if evt.user_id != user_id:
                continue

            amount = evt.amount
            if amount is None or amount == Decimal("0"):
                if evt.event_id in image_amounts:
                    amount = image_amounts[evt.event_id]

            settlement_date = evt.settlement_date
            status = evt.status

            if evt.event_id in message_amendments:
                amend = message_amendments[evt.event_id]
                if "amount" in amend and amend["amount"] is not None:
                    amount = amend["amount"]
                if "settlement_date" in amend and amend["settlement_date"]:
                    settlement_date = amend["settlement_date"]
                if "status" in amend and amend["status"]:
                    status = amend["status"]

            updated_evt = FinancialEvent(
                event_id=evt.event_id,
                user_id=evt.user_id,
                event_type=evt.event_type,
                description=evt.description,
                category=evt.category,
                direction=evt.direction,
                amount=amount,
                currency=evt.currency,
                event_date=evt.event_date,
                settlement_date=settlement_date,
                status=status,
                linked_event_id=evt.linked_event_id,
                flexibility=evt.flexibility,
                minimum_allowed_amount=evt.minimum_allowed_amount,
            )
            events_by_id[evt.event_id] = updated_evt

        for evt_id, evt in events_by_id.items():
            st = evt.status.lower()
            if st in ("failed", "cancelled", "unrealized"):
                continue

            # Pending credits must be ignored!
            if evt.direction.lower() == "credit" and st == "pending":
                continue

            # If amount is still None, skip
            if evt.amount is None:
                continue

            # Determine effective date for forecast
            effective_date = evt.settlement_date

            if request_date is not None:
                # Historical settled events (settlement_date <= request_date) are already reflected
                # in current_available_balance! Do NOT re-apply in 90-day forecast.
                if st == "settled" and effective_date <= request_date:
                    # Still keep resolved record for recurrence inference, but mark or filter
                    pass
                elif st == "pending" and evt.direction.lower() == "debit":
                    # Reserve pending debits on max(request_date, settlement_date)
                    effective_date = max(request_date, effective_date)

            try:
                amt_home = self.converter.convert(
                    evt.amount, evt.currency, profile.home_currency, evt.settlement_date
                )
            except Exception:
                amt_home = evt.amount

            min_amt_home = None
            if evt.minimum_allowed_amount is not None:
                try:
                    min_amt_home = self.converter.convert(
                        evt.minimum_allowed_amount,
                        evt.currency,
                        profile.home_currency,
                        evt.settlement_date,
                    )
                except Exception:
                    min_amt_home = evt.minimum_allowed_amount

            is_protected = evt.category in profile.protected_categories

            res_evt = ResolvedCashEvent(
                event_id=evt.event_id,
                user_id=evt.user_id,
                effective_date=effective_date,
                direction=evt.direction.lower(),
                amount_home=amt_home,
                category=evt.category,
                description=evt.description,
                status=st,
                protected=is_protected,
                flexibility=evt.flexibility,
                minimum_allowed_amount=min_amt_home,
                source_event_ids=(evt.event_id,),
            )
            resolved.append(res_evt)

        return resolved
