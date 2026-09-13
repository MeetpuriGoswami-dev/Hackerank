import os
import sys
import time
from pathlib import Path

# Ensure code directory is on python path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(repo_root / "code") not in sys.path:
    sys.path.insert(0, str(repo_root / "code"))

from buy_or_wait.models import CandidatePlan
from buy_or_wait.ingestion.loader import DataLoader
from buy_or_wait.evidence.images import ImageEvidenceExtractor
from buy_or_wait.evidence.messages import MessageFactExtractor
from buy_or_wait.finance.currency import CurrencyConverter
from buy_or_wait.finance.lifecycle import EventLifecycleResolver
from buy_or_wait.finance.recurrence import RecurrenceEngine
from buy_or_wait.finance.simulator import FinanceSimulator
from buy_or_wait.decision.capacity import CapacityCalculator
from buy_or_wait.decision.candidates import CandidateGenerator
from buy_or_wait.decision.spending import SpendingOptimizer
from buy_or_wait.decision.ranking import PlanRanker
from buy_or_wait.decision.explanation import ExplanationGenerator
from buy_or_wait.output.formatter import OutputFormatter
from buy_or_wait.output.validator import OutputValidator
from buy_or_wait.output.writer import OutputWriter


def run_pipeline(dataset_dir: Path, output_file: Path, requests_filename: str = "requests.csv"):
    start_time = time.time()
    print(f"[Buy or Wait?] Loading dataset from {dataset_dir}...")

    loader = DataLoader(dataset_dir)
    requests = loader.load_requests(requests_filename)
    profiles = loader.load_profiles()
    events = loader.load_financial_events()
    payment_options = loader.load_payment_options()
    exchange_rates = loader.load_exchange_rates()
    messages = loader.load_messages()
    images = loader.load_images()

    print(f"[Buy or Wait?] Loaded {len(requests)} requests, {len(profiles)} profiles, {len(events)} events.")

    # 1. Evidence extraction
    image_extractor = ImageEvidenceExtractor()
    image_amounts = image_extractor.recover_event_amounts(images, dataset_dir / "media" / "images")

    message_extractor = MessageFactExtractor()
    message_facts = message_extractor.extract_message_facts(messages)
    event_amendments = message_facts["event_amendments"]
    user_salary_amendments = message_facts.get("user_salary_amendments", {})
    terminated_income_users = message_facts["terminated_income_users"]

    # 2. Finance components
    converter = CurrencyConverter(exchange_rates)
    resolver = EventLifecycleResolver(converter)
    recurrence_engine = RecurrenceEngine()
    simulator = FinanceSimulator()
    capacity_calc = CapacityCalculator(simulator)
    spending_opt = SpendingOptimizer(simulator)
    candidate_gen = CandidateGenerator()
    ranker = PlanRanker()
    explainer = ExplanationGenerator()
    formatter = OutputFormatter()
    validator = OutputValidator()
    writer = OutputWriter()

    decisions = []
    status_counts = {}

    print(f"[Buy or Wait?] Processing {len(requests)} requests...")

    for req in requests:
        uid = req.user_id
        prof = profiles[uid]

        # Resolve user events
        user_events = [e for e in events if e.user_id == uid]
        base_events = resolver.resolve_events_for_user(
            user_id=uid,
            events=user_events,
            profile=prof,
            image_amounts=image_amounts,
            message_amendments=event_amendments,
            request_date=req.request_date,
        )

        # Recurrence projection
        from datetime import timedelta
        horizon_end = req.request_date + timedelta(days=89)
        projected_events = recurrence_engine.infer_and_project_recurrences(
            historical_events=base_events,
            request_date=req.request_date,
            horizon_end_date=horizon_end,
            terminated_categories=set() if uid not in terminated_income_users else {"income", "salary"},
            user_salary_amendments=user_salary_amendments,
        )

        all_user_events = base_events + projected_events

        # Calculate capacities without spending changes
        amount_safe_today = capacity_calc.calculate_amount_safe_to_pay(
            request_date=req.request_date,
            requested_amount=req.requested_amount,
            desired_completion_date=req.desired_completion_date,
            profile=prof,
            base_events=all_user_events,
        )

        earliest_full_date = capacity_calc.calculate_earliest_date_for_full_payment(
            request_date=req.request_date,
            requested_amount=req.requested_amount,
            desired_completion_date=req.desired_completion_date,
            profile=prof,
            base_events=all_user_events,
        )

        # Retrieve payment options for request
        req_options = payment_options.get(req.request_id, [])

        # Generate candidates
        raw_candidates = candidate_gen.generate_candidates(
            request=req,
            profile=prof,
            payment_options=req_options,
            amount_safe_to_pay=amount_safe_today,
            earliest_date_for_full_payment=earliest_full_date,
        )

        # Simulate & find optimal spending changes for candidates
        safe_plans = []
        for cand in raw_candidates:
            # First simulate candidate without changes
            sim_res = simulator.simulate_90_days(
                request_date=req.request_date,
                requested_amount=req.requested_amount,
                desired_completion_date=req.desired_completion_date,
                profile=prof,
                base_events=all_user_events,
                plan=cand,
            )
            if sim_res.safe and not (cand.method == "full_payment" and amount_safe_today < req.requested_amount):
                safe_plans.append(cand)
            else:
                # Try finding spending changes to make candidate safe
                changes = spending_opt.find_minimal_spending_changes(
                    request_date=req.request_date,
                    requested_amount=req.requested_amount,
                    desired_completion_date=req.desired_completion_date,
                    profile=prof,
                    base_events=all_user_events,
                    candidate_plan=cand,
                )
                if changes is not None:
                    cand_with_changes = CandidatePlan(
                        method=cand.method,
                        payments=cand.payments,
                        changes=changes,
                        payment_option_id=cand.payment_option_id,
                        total_payable=cand.total_payable,
                        earliest_date_for_full_payment=cand.earliest_date_for_full_payment,
                    )
                    safe_plans.append(cand_with_changes)

        # Rank and select winning plan
        winning_plan = ranker.select_best_plan(safe_plans, req.desired_completion_date)
        affordability_status = ranker.determine_affordability_status(winning_plan, req.request_date)

        # Re-simulate winning plan for explanation trace
        final_sim = simulator.simulate_90_days(
            request_date=req.request_date,
            requested_amount=req.requested_amount,
            desired_completion_date=req.desired_completion_date,
            profile=prof,
            base_events=all_user_events,
            plan=winning_plan,
        )

        # Generate explanation
        explanation = explainer.generate_explanation(
            request=req,
            profile=prof,
            plan=winning_plan,
            sim_result=final_sim,
            base_events=all_user_events,
        )

        # Format decision
        decision = formatter.format_decision(
            request=req,
            amount_safe_to_pay=amount_safe_today,
            affordability_status=affordability_status,
            winning_plan=winning_plan,
            earliest_date_for_full_payment=earliest_full_date,
            explanation=explanation,
        )

        decisions.append(decision)
        status_counts[affordability_status] = status_counts.get(affordability_status, 0) + 1

    # Validate output
    val_errors = validator.validate_decisions(decisions, requests)
    if val_errors:
        print(f"[Buy or Wait?] Validation errors ({len(val_errors)}):")
        for err in val_errors[:10]:
            print(f"  - {err}")
        raise ValueError("Output validation failed!")

    # Write output CSV
    writer.write_output_csv(decisions, output_file)
    elapsed = time.time() - start_time

    print(f"[Buy or Wait?] Successfully generated {output_file} in {elapsed:.2f}s.")
    print(f"[Buy or Wait?] Status breakdown: {status_counts}")


def timedelta_days(days: int):
    from datetime import timedelta
    return timedelta(days=days)


def main():
    dataset_dir = repo_root / "dataset"
    output_file = repo_root / "output.csv"
    run_pipeline(dataset_dir, output_file, "requests.csv")


if __name__ == "__main__":
    main()
