from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from buy_or_wait.models import CandidatePlan, Payment, PaymentOption, Profile, Request
from buy_or_wait.money import quantize_money


class CandidateGenerator:

    def generate_candidates(
        self,
        request: Request,
        profile: Profile,
        payment_options: List[PaymentOption],
        amount_safe_to_pay: Decimal,
        earliest_date_for_full_payment: Optional[date],
    ) -> List[CandidatePlan]:
        candidates: List[CandidatePlan] = []

        user_methods = profile.payment_methods_user_will_consider

        # 1. Full Payment Now
        if "full_payment" in user_methods:
            full_plan = CandidatePlan(
                method="full_payment",
                payments=[Payment(payment_date=request.request_date, amount=request.requested_amount)],
                changes=[],
                total_payable=request.requested_amount,
                earliest_date_for_full_payment=earliest_date_for_full_payment,
            )
            candidates.append(full_plan)

        # 2. Partial Payment (exactly 2 payments)
        if (
            request.allows_partial_payment
            and "partial_payment" in user_methods
            and Decimal("0") < amount_safe_to_pay < request.requested_amount
            and earliest_date_for_full_payment is not None
            and earliest_date_for_full_payment <= request.desired_completion_date
        ):
            rem_amount = request.requested_amount - amount_safe_to_pay
            partial_plan = CandidatePlan(
                method="partial_payment",
                payments=[
                    Payment(payment_date=request.request_date, amount=amount_safe_to_pay),
                    Payment(payment_date=earliest_date_for_full_payment, amount=rem_amount),
                ],
                changes=[],
                total_payable=request.requested_amount,
                earliest_date_for_full_payment=earliest_date_for_full_payment,
            )
            candidates.append(partial_plan)

        # 3. Installments from supplied payment options
        if "installments" in user_methods:
            for opt in payment_options:
                # Check max_installment_months if specified
                if profile.max_installment_months is not None:
                    if opt.number_of_payments > profile.max_installment_months:
                        continue

                # Expand dates and payments
                pmts: List[Payment] = []
                freq = opt.payment_frequency_days
                total_opt = opt.total_payable_amount
                base_pmt = opt.payment_amount

                for i in range(opt.number_of_payments):
                    pmt_date = opt.first_payment_date + timedelta(days=freq * i)
                    if i == opt.number_of_payments - 1:
                        # Reconcile final payment
                        pmt_amt = total_opt - (base_pmt * (opt.number_of_payments - 1))
                    else:
                        pmt_amt = base_pmt

                    pmts.append(Payment(payment_date=pmt_date, amount=pmt_amt))

                inst_plan = CandidatePlan(
                    method="installments",
                    payments=pmts,
                    changes=[],
                    payment_option_id=opt.payment_option_id,
                    total_payable=total_opt,
                    earliest_date_for_full_payment=earliest_date_for_full_payment,
                )
                candidates.append(inst_plan)

        # 4. Wait for full payment later
        if (
            "full_payment" in user_methods
            and earliest_date_for_full_payment is not None
            and earliest_date_for_full_payment > request.request_date
            and earliest_date_for_full_payment <= request.desired_completion_date
        ):
            wait_plan = CandidatePlan(
                method="wait",
                payments=[
                    Payment(
                        payment_date=earliest_date_for_full_payment,
                        amount=request.requested_amount,
                    )
                ],
                changes=[],
                total_payable=request.requested_amount,
                earliest_date_for_full_payment=earliest_date_for_full_payment,
            )
            candidates.append(wait_plan)

        return candidates
