# Buy or Wait? — AI Financial Decision Agent

Starter entry point and implementation for the HackerRank Orchestrate (September 2026) challenge: **Buy or Wait?**.

## 1. Approach Overview

The system reconstructs the user's financial position from structured profiles, historical financial events, fixed dated exchange rates, seller payment options, and unstructured message/image evidence.

### Core Components
1. **Evidence Extraction** (`code/buy_or_wait/evidence/`):
   - `ImageEvidenceExtractor`: Uses OCR and Regex to recover missing event amounts from receipts/invoices in `dataset/media/images/`.
   - `MessageFactExtractor`: Resolves event amendments, cancellations, salary date changes, and employment terminations from user chat messages.

2. **Cash Flow & Recurrence Engine** (`code/buy_or_wait/finance/`):
   - `EventLifecycleResolver`: Converts multi-currency events to home currency on settlement date, handles pending debits, settled income, and message amendments.
   - `RecurrenceEngine`: Infers recurring monthly streams, excludes one-off bonuses/gifts/commission payouts, and projects essential daily variable spending over a 90-day horizon.
   - `FinanceSimulator`: Simulates daily available cash balance over 90 days, checking that `daily_balance >= minimum_balance_to_keep`.

3. **Decision & Optimization Engine** (`code/buy_or_wait/decision/`):
   - `CapacityCalculator`: Computes `amount_safe_to_pay` today and `earliest_date_for_full_payment`.
   - `CandidateGenerator`: Evaluates payment strategies (`full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended`).
   - `SpendingOptimizer`: Finds minimal non-protected spending change actions (`stop:<event_id>`, `reduce_to:<event_id>:<amount>`).
   - `PlanRanker`: Ranks safe candidate plans lexicographically.
   - `ExplanationGenerator`: Produces concise, grounded decision explanations.

---

## 2. Setup & Execution Instructions

### Prerequisites
- Python 3.10+ installed

### Setup Environment
```bash
# Clone repository and navigate to root
cd hackerrank-orchestrate-september26

# Install dependencies (if needed)
pip install -r code/requirements.txt
```

### Run Pipeline (Full Evaluation Dataset)
To process `dataset/requests.csv` and output `output.csv` at repository root:
```bash
python code/main.py
```

### Run Unit Tests
```bash
python -m pytest code/tests -q
```

### Run Sample Benchmark Evaluation
```bash
python code/evaluation/main.py
```

---

## 3. Directory Structure inside `code/`
```text
code/
├── main.py                     # Entry point for production pipeline
├── requirements.txt            # Python dependencies
├── README.md                   # Setup instructions and approach overview
├── buy_or_wait/                # Core Python package
│   ├── models.py               # Data models & schemas
│   ├── money.py                # Money quantization & decimal utilities
│   ├── decision/               # Capacity, candidate generation, spending optimizer, plan ranker
│   ├── evidence/               # OCR image & message fact extractors
│   ├── finance/                # Currency conversion, lifecycle resolver, recurrence, simulator
│   ├── ingestion/              # CSV loader
│   └── output/                 # Formatter, validator, CSV writer
├── evaluation/
│   ├── main.py                 # Evaluation script against sample_requests.csv
│   └── usage_report.md         # Model usage & cost report
└── tests/
    ├── conftest.py             # Pytest fixtures
    └── test_engine.py          # Unit tests
```
