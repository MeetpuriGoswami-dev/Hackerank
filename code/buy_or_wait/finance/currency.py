from datetime import date
from decimal import Decimal
from typing import Dict, Tuple

from buy_or_wait.money import to_decimal, quantize_money


class CurrencyConverter:

    def __init__(self, rates: Dict[Tuple[date, str, str], Decimal]):
        self.rates = rates

    def convert(
        self, amount: Decimal, from_curr: str, to_curr: str, settlement_date: date
    ) -> Decimal:
        if amount is None or amount == Decimal("0"):
            return Decimal("0")
        if from_curr == to_curr:
            return amount

        key = (settlement_date, from_curr, to_curr)
        if key in self.rates:
            return amount * self.rates[key]

        inv_key = (settlement_date, to_curr, from_curr)
        if inv_key in self.rates and self.rates[inv_key] != Decimal("0"):
            return amount / self.rates[inv_key]

        raise ValueError(
            f"Missing exchange rate for {from_curr} -> {to_curr} on {settlement_date}"
        )
