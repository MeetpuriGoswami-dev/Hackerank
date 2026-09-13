import csv
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

from buy_or_wait.money import to_decimal
from buy_or_wait.models import (
    FinancialEvent,
    ExchangeRate,
    ImageRecord,
    Message,
    PaymentOption,
    Profile,
    Request,
)


def parse_date(date_str: str) -> date:
    if not date_str:
        return date(1970, 1, 1)
    s = date_str.strip()
    # Handle YYYY-MM-DD format
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_pipe_set(val: str) -> set:
    if not val or val.strip() == "":
        return set()
    return {x.strip() for x in val.split("|") if x.strip()}


def parse_pipe_list(val: str) -> list:
    if not val or val.strip() == "":
        return []
    return [x.strip() for x in val.split("|") if x.strip()]


class DataLoader:

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = Path(dataset_dir)

    def load_requests(self, filename: str = "requests.csv") -> List[Request]:
        filepath = self.dataset_dir / filename
        requests = []
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                allows_partial = (
                    row.get("allows_partial_payment", "").strip().lower() == "true"
                )
                req = Request(
                    request_id=row["request_id"].strip(),
                    user_id=row["user_id"].strip(),
                    request_date=parse_date(row["request_date"]),
                    request_type=row["request_type"].strip(),
                    requested_amount=to_decimal(row["requested_amount"]),
                    desired_completion_date=parse_date(row["desired_completion_date"]),
                    allows_partial_payment=allows_partial,
                    request_text=row["request_text"].strip(),
                )
                requests.append(req)
        return requests

    def load_profiles(self) -> Dict[str, Profile]:
        filepath = self.dataset_dir / "financial_profiles.csv"
        profiles = {}
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"].strip()
                max_inst = row.get("max_installment_months", "").strip()
                max_inst_val = int(max_inst) if max_inst and max_inst.isdigit() else None

                prof = Profile(
                    user_id=uid,
                    home_currency=row["home_currency"].strip(),
                    current_available_balance=to_decimal(row["current_available_balance"]),
                    minimum_balance_to_keep=to_decimal(row["minimum_balance_to_keep"]),
                    financial_priorities=parse_pipe_list(row.get("financial_priorities", "")),
                    protected_categories=parse_pipe_set(row.get("expense_categories_to_protect", "")),
                    reducible_categories=parse_pipe_set(row.get("expense_categories_user_is_willing_to_reduce", "")),
                    stoppable_categories=parse_pipe_set(row.get("expense_categories_user_is_willing_to_stop", "")),
                    payment_methods_user_will_consider=parse_pipe_set(row.get("payment_methods_user_will_consider", "")),
                    max_installment_months=max_inst_val,
                )
                profiles[uid] = prof
        return profiles

    def load_financial_events(self) -> List[FinancialEvent]:
        filepath = self.dataset_dir / "financial_events.csv"
        events = []
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                amt_str = row.get("amount", "").strip()
                amt = to_decimal(amt_str) if amt_str != "" else None
                
                min_amt_str = row.get("minimum_allowed_amount", "").strip()
                min_amt = to_decimal(min_amt_str) if min_amt_str != "" else None

                evt = FinancialEvent(
                    event_id=row["event_id"].strip(),
                    user_id=row["user_id"].strip(),
                    event_type=row["event_type"].strip(),
                    description=row["description"].strip(),
                    category=row["category"].strip(),
                    direction=row["direction"].strip(),
                    amount=amt,
                    currency=row["currency"].strip(),
                    event_date=parse_date(row["event_date"]),
                    settlement_date=parse_date(row["settlement_date"]),
                    status=row["status"].strip(),
                    linked_event_id=row.get("linked_event_id", "").strip() or None,
                    flexibility=row.get("flexibility", "").strip() or None,
                    minimum_allowed_amount=min_amt,
                )
                events.append(evt)
        return events

    def load_payment_options(self) -> Dict[str, List[PaymentOption]]:
        filepath = self.dataset_dir / "request_payment_options.csv"
        options_by_request: Dict[str, List[PaymentOption]] = {}
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                req_id = row["request_id"].strip()
                n_pmts_str = row.get("number_of_payments", "").strip()
                n_pmts = int(n_pmts_str) if n_pmts_str and n_pmts_str.isdigit() else 1

                freq_str = row.get("payment_frequency_days", "").strip()
                freq_days = int(freq_str) if freq_str and freq_str.isdigit() else 30

                pmt_amt = to_decimal(row.get("payment_amount"))
                fin_fee = to_decimal(row.get("financing_fee"))
                total_payable = to_decimal(row.get("total_payable_amount"))
                if total_payable == Decimal("0") and pmt_amt > Decimal("0"):
                    total_payable = pmt_amt * n_pmts + fin_fee

                opt = PaymentOption(
                    payment_option_id=row["payment_option_id"].strip(),
                    request_id=req_id,
                    payment_method=row["payment_method"].strip(),
                    payment_amount=pmt_amt,
                    number_of_payments=n_pmts,
                    first_payment_date=parse_date(row["first_payment_date"]),
                    payment_frequency_days=freq_days,
                    financing_fee=fin_fee,
                    total_payable_amount=total_payable,
                )
                if req_id not in options_by_request:
                    options_by_request[req_id] = []
                options_by_request[req_id].append(opt)
        return options_by_request

    def load_exchange_rates(self) -> Dict[Tuple[date, str, str], Decimal]:
        filepath = self.dataset_dir / "exchange_rates.csv"
        rates: Dict[Tuple[date, str, str], Decimal] = {}
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_date = parse_date(row["rate_date"])
                from_c = row["from_currency"].strip()
                to_c = row["to_currency"].strip()
                rate_val = to_decimal(row["rate"])
                rates[(r_date, from_c, to_c)] = rate_val
        return rates

    def load_messages(self) -> List[Message]:
        filepath = self.dataset_dir / "messages.csv"
        messages = []
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                msg = Message(
                    message_id=row["message_id"].strip(),
                    user_id=row["user_id"].strip(),
                    request_id=row.get("request_id", "").strip() or None,
                    related_event_id=row.get("related_event_id", "").strip() or None,
                    sent_at=row.get("sent_at", "").strip(),
                    source_type=row.get("source_type", "").strip(),
                    message_text=row.get("message_text", "").strip(),
                )
                messages.append(msg)
        return messages

    def load_images(self) -> List[ImageRecord]:
        filepath = self.dataset_dir / "images.csv"
        images = []
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                img = ImageRecord(
                    image_id=row["image_id"].strip(),
                    user_id=row["user_id"].strip(),
                    request_id=row.get("request_id", "").strip() or None,
                    related_event_id=row.get("related_event_id", "").strip() or None,
                )
                images.append(img)
        return images
