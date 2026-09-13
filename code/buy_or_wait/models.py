from datetime import date
from decimal import Decimal
from typing import List, Optional, Set
from pydantic import BaseModel, ConfigDict


class Request(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    request_id: str
    user_id: str
    request_date: date
    request_type: str
    requested_amount: Decimal
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str


class Profile(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    user_id: str
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    financial_priorities: List[str]
    protected_categories: Set[str]
    reducible_categories: Set[str]
    stoppable_categories: Set[str]
    payment_methods_user_will_consider: Set[str]
    max_installment_months: Optional[int] = None


class FinancialEvent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str  # "credit" or "debit"
    amount: Optional[Decimal] = None
    currency: str
    event_date: date
    settlement_date: date
    status: str
    linked_event_id: Optional[str] = None
    flexibility: Optional[str] = None
    minimum_allowed_amount: Optional[Decimal] = None


class PaymentOption(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    payment_option_id: str
    request_id: str
    payment_method: str
    payment_amount: Decimal
    number_of_payments: int
    first_payment_date: date
    payment_frequency_days: int
    financing_fee: Decimal
    total_payable_amount: Decimal


class ExchangeRate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    rate_date: date
    from_currency: str
    to_currency: str
    rate: Decimal


class Message(BaseModel):
    message_id: str
    user_id: str
    request_id: Optional[str] = None
    related_event_id: Optional[str] = None
    sent_at: str
    source_type: str
    message_text: str


class ImageRecord(BaseModel):
    image_id: str
    user_id: str
    request_id: Optional[str] = None
    related_event_id: Optional[str] = None


class Payment(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    payment_date: date
    amount: Decimal


class SpendingChange(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    action: str  # "stop" or "reduce_to"
    event_id: str
    new_amount: Optional[Decimal] = None

    def to_string(self) -> str:
        if self.action == "stop":
            return f"stop:{self.event_id}"
        elif self.action == "reduce_to":
            # format amount
            if self.new_amount is not None:
                if self.new_amount == self.new_amount.quantize(Decimal("1")):
                    amt_str = str(int(self.new_amount))
                else:
                    amt_str = f"{self.new_amount:.2f}".rstrip("0").rstrip(".")
            else:
                amt_str = "0"
            return f"reduce_to:{self.event_id}:{amt_str}"
        return ""


class CandidatePlan(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    method: str  # full_payment, partial_payment, installments, wait, not_recommended
    payments: List[Payment]
    changes: List[SpendingChange]
    payment_option_id: Optional[str] = None
    total_payable: Decimal
    earliest_date_for_full_payment: Optional[date] = None


class SimulationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    safe: bool
    minimum_balance: Decimal
    minimum_balance_date: date
    ending_balance: Decimal
    first_breach_date: Optional[date] = None
    completion_date: Optional[date] = None
    rejection_reasons: List[str]


class DecisionResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    request_id: str
    amount_safe_to_pay: Decimal
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: str  # "YYYY-MM-DD" or ""
    spending_changes_needed: str
    decision_explanation: str
