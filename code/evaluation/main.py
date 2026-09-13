import csv
import sys
import time
from pathlib import Path

# Ensure code directory is on python path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(repo_root / "code") not in sys.path:
    sys.path.insert(0, str(repo_root / "code"))

import importlib.util
spec = importlib.util.spec_from_file_location("prod_main", repo_root / "code" / "main.py")
prod_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prod_main)
run_pipeline = prod_main.run_pipeline
from buy_or_wait.money import to_decimal


def evaluate_sample_requests():
    dataset_dir = repo_root / "dataset"
    sample_csv = dataset_dir / "sample_requests.csv"
    temp_output = repo_root / "code" / "evaluation" / "sample_output.csv"

    print("[Evaluation] Running production pipeline against 25 solved sample requests...")
    run_pipeline(dataset_dir, temp_output, "sample_requests.csv")

    # Load ground truth from sample_requests.csv
    ground_truth = []
    with open(sample_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ground_truth.append(r)

    # Load predictions from temp_output
    predictions = []
    with open(temp_output, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            predictions.append(r)

    pred_map = {p["request_id"]: p for p in predictions}

    total = len(ground_truth)
    matches = {
        "amount_safe_to_pay": 0,
        "affordability_status": 0,
        "recommended_payment_method": 0,
        "payment_plan": 0,
        "earliest_date_for_full_payment": 0,
        "spending_changes_needed": 0,
        "exact_row_match": 0,
    }

    mismatches = []

    for gt in ground_truth:
        rid = gt["request_id"]
        pred = pred_map.get(rid)
        if not pred:
            mismatches.append(f"Missing prediction for {rid}")
            continue

        row_match = True
        field_diffs = []

        # 1. amount_safe_to_pay
        gt_safe = to_decimal(gt["amount_safe_to_pay"])
        pr_safe = to_decimal(pred["amount_safe_to_pay"])
        if abs(gt_safe - pr_safe) < 0.01:
            matches["amount_safe_to_pay"] += 1
        else:
            row_match = False
            field_diffs.append(f"amount_safe_to_pay: expected {gt_safe}, got {pr_safe}")

        # 2. affordability_status
        if gt["affordability_status"].strip() == pred["affordability_status"].strip():
            matches["affordability_status"] += 1
        else:
            row_match = False
            field_diffs.append(f"affordability_status: expected {gt['affordability_status']}, got {pred['affordability_status']}")

        # 3. recommended_payment_method
        if gt["recommended_payment_method"].strip() == pred["recommended_payment_method"].strip():
            matches["recommended_payment_method"] += 1
        else:
            row_match = False
            field_diffs.append(f"recommended_payment_method: expected {gt['recommended_payment_method']}, got {pred['recommended_payment_method']}")

        # 4. payment_plan
        if gt["payment_plan"].strip() == pred["payment_plan"].strip():
            matches["payment_plan"] += 1
        else:
            row_match = False
            field_diffs.append(f"payment_plan: expected {gt['payment_plan']}, got {pred['payment_plan']}")

        # 5. earliest_date_for_full_payment
        if gt["earliest_date_for_full_payment"].strip() == pred["earliest_date_for_full_payment"].strip():
            matches["earliest_date_for_full_payment"] += 1
        else:
            row_match = False
            field_diffs.append(f"earliest_date_for_full_payment: expected '{gt['earliest_date_for_full_payment']}', got '{pred['earliest_date_for_full_payment']}'")

        # 6. spending_changes_needed
        if gt["spending_changes_needed"].strip() == pred["spending_changes_needed"].strip():
            matches["spending_changes_needed"] += 1
        else:
            row_match = False
            field_diffs.append(f"spending_changes_needed: expected '{gt['spending_changes_needed']}', got '{pred['spending_changes_needed']}'")

        if row_match:
            matches["exact_row_match"] += 1
        else:
            mismatches.append(f"{rid}: " + " | ".join(field_diffs))

    print("\n" + "=" * 60)
    print(" SAMPLE REQUESTS EVALUATION REPORT ")
    print("=" * 60)
    print(f"Total Evaluated: {total}")
    for k, v in matches.items():
        pct = (v / total) * 100
        print(f"  - {k}: {v}/{total} ({pct:.1f}%)")

    if mismatches:
        print("\nMismatches detail:")
        for m in mismatches:
            print(f"  [X] {m}")
    else:
        print("\n[SUCCESS] 100% Perfect Match on all 25 solved sample requests!")
    print("=" * 60)

    # Clean up temp file
    if temp_output.exists():
        temp_output.unlink()


def main():
    evaluate_sample_requests()


if __name__ == "__main__":
    main()
