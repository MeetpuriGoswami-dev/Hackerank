import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional

from buy_or_wait.money import to_decimal
from buy_or_wait.models import Message


class MessageFactExtractor:

    def extract_message_facts(self, messages: List[Message]) -> Dict[str, Dict]:
        """Extracts structured financial facts from messages.

        Returns a mapping from event_id or user_id to fact dictionary.
        """
        # Map by related_event_id and user_id
        event_amendments: Dict[str, Dict] = {}
        user_salary_amendments: Dict[str, Dict] = {}
        terminated_income_users: set = set()

        for msg in messages:
            txt = msg.message_text
            uid = msg.user_id
            evt_id = msg.related_event_id

            # Check for salary/income amount changes
            # e.g., "gaji bulanan Anda naik menjadi IDR 42750000", "salary is EUR 1037.52", "reduced to EUR 1422.85", "salary of EUR 2717"
            amt_match = re.search(
                r"(?:menjadi|is|will be|reduced to|salary of)\s+(?:[A-Z]{3}\s+)?([\d,]+(?:\.\d+)?)",
                txt,
                re.IGNORECASE,
            )

            # Check for effective/settlement date
            # e.g., "berlaku mulai 2025-08-15", "expected on 2024-09-23", "credit date is 2026-01-15"
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", txt)

            # Check for contract end / termination
            txt_lower = txt.lower()
            if (
                "contract has ended" in txt_lower
                or "employment has ended" in txt_lower
                or "telah berakhir" in txt_lower
                or "no regular salary" in txt_lower
                or "no off-season income" in txt_lower
            ):
                terminated_income_users.add(uid)
                if evt_id:
                    event_amendments[evt_id] = {"status": "cancelled"}

            if evt_id:
                if evt_id not in event_amendments:
                    event_amendments[evt_id] = {}
                if amt_match:
                    try:
                        event_amendments[evt_id]["amount"] = to_decimal(amt_match.group(1))
                    except Exception:
                        pass
                if date_match:
                    try:
                        event_amendments[evt_id]["settlement_date"] = datetime.strptime(
                            date_match.group(1), "%Y-%m-%d"
                        ).date()
                    except Exception:
                        pass

            # User level salary updates (if related_event_id is not populated or targets user's salary)
            if "payroll" in txt.lower() or "gaji" in txt.lower() or "salary" in txt.lower() or "penggajian" in txt.lower():
                if uid not in user_salary_amendments:
                    user_salary_amendments[uid] = {}
                if amt_match:
                    try:
                        user_salary_amendments[uid]["amount"] = to_decimal(amt_match.group(1))
                    except Exception:
                        pass
                if date_match:
                    try:
                        user_salary_amendments[uid]["effective_date"] = datetime.strptime(
                            date_match.group(1), "%Y-%m-%d"
                        ).date()
                    except Exception:
                        pass

        return {
            "event_amendments": event_amendments,
            "user_salary_amendments": user_salary_amendments,
            "terminated_income_users": terminated_income_users,
        }

