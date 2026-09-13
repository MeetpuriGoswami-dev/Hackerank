import csv
from pathlib import Path
from typing import List

from buy_or_wait.money import format_money_general
from buy_or_wait.models import DecisionResult

HEADER = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]


class OutputWriter:

    def write_output_csv(
        self, decisions: List[DecisionResult], output_filepath: Path
    ):
        output_filepath = Path(output_filepath)
        temp_filepath = output_filepath.with_suffix(".tmp")

        with open(temp_filepath, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            for d in decisions:
                amt_safe_str = format_money_general(d.amount_safe_to_pay)
                writer.writerow(
                    [
                        d.request_id,
                        amt_safe_str,
                        d.affordability_status,
                        d.recommended_payment_method,
                        d.payment_plan,
                        d.earliest_date_for_full_payment,
                        d.spending_changes_needed,
                        d.decision_explanation,
                    ]
                )

        # Replace target file atomically
        temp_filepath.replace(output_filepath)
