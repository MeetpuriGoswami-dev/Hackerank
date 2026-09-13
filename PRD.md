# Product Requirements Document: Buy or Wait?

| Field | Value |
|---|---|
| Product | Buy or Wait? |
| Challenge | HackerRank Orchestrate, September 2026 |
| Document status | Implementation-ready |
| Primary deliverable | Root-level `output.csv` |
| Runtime | Terminal-executable Python application |
| Forecast horizon | 90 calendar days per request |
| Existing implementation entry point | `code/main.py` |
| Repository | `https://github.com/interviewstreet/hackerrank-orchestrate-september26` |
| Source of truth | [`problem_statement.md`](./problem_statement.md) |
| Technical design | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |

## 1. Executive Summary

Buy or Wait? is an AI-assisted financial decision engine that determines whether a user can safely afford a requested expense and, when possible, recommends the safest eligible payment strategy.

The system must not decide affordability from the current balance alone. For every request it reconstructs the user's financial state from profiles, historical and future financial events, payment offers, exchange rates, messages, and images; forecasts cash flow for 90 days; generates valid payment candidates; verifies every candidate deterministically; ranks safe candidates using the mandated rules; and writes one prediction to `output.csv`.

The core financial decision must be deterministic. AI is used only where unstructured evidence must be converted into facts or a grounded explanation must be written. AI output never overrides the challenge rules.

## 2. Problem Statement

A user's current bank balance is not enough to answer questions such as “Can I afford this laptop?” Upcoming rent, recurring bills, confirmed income, pending debits, minimum cash reserves, payment preferences, deadlines, and flexible spending can materially change the answer.

The product must answer seven questions for every request:

1. What is the maximum amount safe to pay today?
2. Is the request affordable now, with a plan, later, or not within the forecast?
3. Which eligible payment method is safest?
4. What exact payment dates and amounts should be used?
5. What is the earliest safe date for one full payment?
6. Which permitted flexible expenses, if any, must change?
7. Which concrete financial facts justify the decision?

## 3. Product Goal

Generate a complete, valid, personalized, and reproducible affordability decision for every row in `dataset/requests.csv`, while protecting essential expenses and ensuring the user's projected balance never falls below `minimum_balance_to_keep` during the 90-day forecast.

### 3.1 Success definition

The product succeeds when:

- a single documented terminal command processes the supplied dataset;
- exactly one output row is produced for every evaluation request;
- every output passes schema and business-rule validation;
- every recommended plan is safe under the deterministic 90-day simulation;
- all recommendations use only supplied or reliably extracted facts;
- solved sample performance can be measured automatically;
- model use, tokens, and estimated costs are recorded for the final run.

### 3.2 Primary optimization target

Maximize agreement with hidden ground truth across:

- `amount_safe_to_pay`;
- `affordability_status`;
- `recommended_payment_method`;
- `payment_plan`;
- `earliest_date_for_full_payment`;
- `spending_changes_needed`;
- useful and internally consistent `decision_explanation` text.

## 4. Scope

### 4.1 In scope

- Load and validate every participant-facing CSV in `dataset/`.
- Join request, user, event, message, image, payment-option, and exchange-rate records.
- Recover blank financial-event amounts from linked PNG images.
- Interpret relevant messages and images as untrusted evidence.
- Resolve cancellations, settlements, amendments, delays, duplicates, and conflicts.
- Normalize eligible foreign-currency cash events into the user's home currency.
- Infer recurring income and expenses only when supported by history.
- Forecast daily balances for 90 calendar days from each request date.
- Calculate the maximum safe amount payable on the request date before optional spending changes.
- Find the earliest date within the forecast when one full payment becomes safe.
- Evaluate full-payment, exact supplied installment, partial-payment, wait, and permitted spending-change strategies.
- Rank safe and eligible plans using the required deterministic ordering.
- Generate concise grounded explanations.
- Write and validate root-level `output.csv`.
- Evaluate against `sample_requests.csv`.
- Track model usage and produce `code/evaluation/usage_report.md` for the final run.

### 4.2 Out of scope

- Web or mobile UI.
- User authentication or account management.
- Supabase, PostgreSQL, or any other database.
- FastAPI or another web API.
- Live banking connectivity.
- Live foreign-exchange, market, or merchant data.
- Voice-note processing.
- Asset-price prediction or securities recommendations.
- Invented payment plans, income, expenses, dates, or financial facts.
- Organizer-only data or hardcoded evaluation labels.

## 5. Users and Stakeholders

| Stakeholder | Need |
|---|---|
| End user represented by a request | A safe, personalized and understandable affordability decision |
| Participant/developer | A modular, testable pipeline that can be improved quickly |
| HackerRank evaluator | Deterministic, correctly formatted predictions for all requests |
| Challenge reviewer | Reproducible code, setup instructions, model-usage report, and transcript |

The submitted system is a batch decision engine. A consumer-facing interface is not required.

## 6. Existing Repository Contract

This project must be implemented inside the supplied HackerRank starter repository. It is not a request to scaffold a separate application or replace the existing repository structure.

The IDE implementing this PRD must:

- read `AGENTS.md`, `README.md`, and `problem_statement.md` before changing code;
- continue from the existing `code/main.py` entry point;
- use `code/evaluation/main.py` for evaluation logic and update `code/evaluation/usage_report.md` for the final run;
- keep all solution source files under `code/`;
- read inputs only from the existing `dataset/` directory;
- leave every supplied dataset file unchanged;
- write final predictions to `output.csv` in the repository root, not to `dataset/output.csv`;
- preserve the official command `python3 code/main.py`;
- add only the helper modules, tests, prompts, dependency files, and configuration required by the implementation;
- inspect the current repository state before deciding its own implementation task breakdown.

The IDE may decide how to divide and sequence implementation work. This PRD defines the required outcome and constraints; it intentionally does not prescribe phases or a build order.

### 6.1 Clone or open the repository

Fresh clone:

```bash
git clone https://github.com/interviewstreet/hackerrank-orchestrate-september26.git
cd hackerrank-orchestrate-september26
```

If the repository is already cloned:

```bash
cd hackerrank-orchestrate-september26
git status
git pull --ff-only origin main
```

Do not run `git pull` while uncommitted local work would be overwritten or conflicted. Review `git status` first.

### 6.2 Python environment and dependencies

The implementation must add a dependency file at `code/requirements.txt` or `code/pyproject.toml`. Commands below assume `code/requirements.txt`.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r code/requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r code/requirements.txt
```

If a model API is used, copy the committed environment-variable template and provide values locally. Never commit the populated `.env` file.

Windows PowerShell:

```powershell
Copy-Item code/.env.example .env
```

macOS/Linux:

```bash
cp code/.env.example .env
```

The `.env.example` step is needed only if the final implementation uses external model credentials.

### 6.3 Required execution commands

Run the starter-compatible solution from the repository root:

```bash
python3 code/main.py
```

Inside an activated Windows virtual environment, the equivalent command is:

```powershell
python code/main.py
```

Run tests and the evaluation script after the IDE implements them:

```bash
python -m pytest code/tests -q
python code/evaluation/main.py
```

Check that the final output exists and contains 250 data rows plus the exact header:

```bash
python -c "import csv; f=open('output.csv', encoding='utf-8'); r=list(csv.DictReader(f)); print('rows=', len(r)); print('columns=', list(r[0]) if r else [])"
```

Review repository changes before packaging:

```bash
git status --short
git diff --check
```

Create and verify the code archive without including `dataset/`, `.env`, credentials, or local caches:

```bash
python -m zipfile -c code.zip code README.md PRD.md ARCHITECTURE.md
python -m zipfile -t code.zip
```

The root-level `output.csv` and `log.txt`/chat transcript are submitted separately as required by the challenge.

## 7. Dataset Contract

### 7.1 Observed dataset inventory

| File | Rows | Role |
|---|---:|---|
| `dataset/requests.csv` | 250 | Evaluation requests requiring predictions |
| `dataset/sample_requests.csv` | 25 | Solved public examples for format and behavior validation |
| `dataset/financial_profiles.csv` | 275 | User balance, reserve, priorities, flexibility, and payment preferences |
| `dataset/financial_events.csv` | 25,342 | Cash and non-cash event history and scheduled/pending events |
| `dataset/request_payment_options.csv` | 790 | Supplied full-payment and installment offers |
| `dataset/exchange_rates.csv` | 134 | Fixed dated currency conversions |
| `dataset/messages.csv` | 215 | Unstructured supporting evidence |
| `dataset/images.csv` | 16 | Image-to-user/request/event relationships |
| `dataset/media/images/*.png` | 16 | Financial documents used as evidence |
| `dataset/output.csv` | 250 blank rows | Output template only |

The current dataset uses INR, ZAR, IDR, USD, and EUR. Data counts are descriptive, not constraints; the implementation must discover records dynamically.

### 7.2 Join rules

| Key | Use |
|---|---|
| `user_id` | Join a request to its profile, financial events, and user-level evidence |
| `request_id` | Join a request to payment offers and request-level evidence |
| `event_id` / `related_event_id` | Connect messages or images to a specific financial event |
| `linked_event_id` | Connect stages in the same transaction or investment lifecycle |
| `rate_date`, `from_currency`, `to_currency` | Select the supplied dated currency conversion |
| `image_id` | Resolve `dataset/media/images/<image_id>.png` |

All input dates are parsed as `YYYY-MM-DD`; message timestamps are parsed as UTC ISO-8601 timestamps.

### 7.3 Input schemas

#### `requests.csv`

`request_id`, `user_id`, `request_date`, `request_type`, `requested_amount`, `desired_completion_date`, `allows_partial_payment`, `request_text`

Allowed request types: `purchase`, `travel`, `education`, `family_transfer`, `debt_repayment`, `investment`, `housing`, `emergency_expense`, and `other`.

#### `financial_profiles.csv`

`user_id`, `home_currency`, `current_available_balance`, `minimum_balance_to_keep`, `financial_priorities`, `expense_categories_to_protect`, `expense_categories_user_is_willing_to_reduce`, `expense_categories_user_is_willing_to_stop`, `payment_methods_user_will_consider`, `max_installment_months`

Pipe-delimited profile fields must be parsed into normalized sets. A blank `max_installment_months` means installments are not considered.

#### `financial_events.csv`

`event_id`, `user_id`, `event_type`, `description`, `category`, `direction`, `amount`, `currency`, `event_date`, `settlement_date`, `status`, `linked_event_id`, `flexibility`, `minimum_allowed_amount`

Observed event types include expense, subscription, income, debt payment, refund, investment purchase, investment sale, and investment valuation. Observed statuses include settled, pending, scheduled, cancelled, failed, and unrealized. The engine must use rule-based semantics rather than assuming that every row changes available cash.

#### `request_payment_options.csv`

`payment_option_id`, `request_id`, `payment_method`, `payment_amount`, `number_of_payments`, `first_payment_date`, `payment_frequency_days`, `financing_fee`, `total_payable_amount`

Installment schedules must be reproduced exactly from these fields and may not be invented or altered.

#### `exchange_rates.csv`

`rate_date`, `from_currency`, `to_currency`, `rate`

#### `messages.csv`

`message_id`, `user_id`, `request_id`, `related_event_id`, `sent_at`, `source_type`, `message_text`

#### `images.csv`

`image_id`, `user_id`, `request_id`, `related_event_id`

## 8. Required Output Contract

The application must write `output.csv` in the repository root with these columns in this exact order:

| Column | Requirement |
|---|---|
| `request_id` | Copied from the corresponding evaluation request |
| `amount_safe_to_pay` | Largest amount safe on `request_date`, before optional spending changes, capped to `[0, requested_amount]` |
| `affordability_status` | `affordable_now`, `affordable_with_plan`, `affordable_later`, or `not_affordable` |
| `recommended_payment_method` | `full_payment`, `partial_payment`, `installments`, `wait`, or `not_recommended` |
| `payment_plan` | Chronological `YYYY-MM-DD:amount` entries separated by `\|`, or `none` |
| `earliest_date_for_full_payment` | First safe full-payment date within the forecast, otherwise blank |
| `spending_changes_needed` | Up to three permitted actions separated by `\|`, or `none` |
| `decision_explanation` | Short, grounded explanation of the recommendation |

### 8.1 Output invariants

- Output contains 250 data rows for the current dataset and exactly one row per input `request_id`.
- Output row order follows `dataset/requests.csv`.
- `0 <= amount_safe_to_pay <= requested_amount`.
- Money is serialized without currency symbols or thousands separators and rounded consistently to at most two decimal places.
- `payment_plan` entries are chronological.
- `affordable_now` implies:
  - full requested amount is safe on `request_date` without spending changes;
  - the user accepts `full_payment`;
  - `earliest_date_for_full_payment == request_date`.
- `partial_payment` implies:
  - status is `affordable_with_plan`;
  - the request allows partial payment;
  - the user accepts partial payment;
  - `0 < amount_safe_to_pay < requested_amount`;
  - the plan has exactly two payments;
  - payment one equals `amount_safe_to_pay` on `request_date`;
  - payment two equals the exact remainder on `earliest_date_for_full_payment`;
  - both payments sum to `requested_amount`;
  - the second payment is no later than `desired_completion_date`.
- `installments` exactly matches one supplied payment option and respects user preferences and `max_installment_months`.
- `wait` is eligible only when a full payment becomes safe later and the user accepts `full_payment`.
- `not_recommended` uses `payment_plan=none`.
- Spending changes contain at most three actions and target only eligible recurring flexible events.
- The same event cannot be both stopped and reduced.

## 9. Functional Requirements

### FR-01: Configuration and path resolution

- The application shall resolve repository, dataset, output, cache, and evaluation paths relative to the entry point rather than the current shell directory.
- Model credentials, if used, shall come only from environment variables.
- The application shall support a deterministic random seed where any non-deterministic library is involved.

### FR-02: Dataset loading and schema validation

- Load all required CSV files using explicit data types.
- Parse monetary values with decimal-safe semantics.
- Parse dates before decision processing.
- Reject duplicate primary IDs, missing required columns, invalid enums, impossible numeric values, and missing required relationships with actionable errors.
- Preserve the supplied input files unchanged.

### FR-03: Request context assembly

For each request, assemble a self-contained context containing:

- request and deadline;
- financial profile and preferences;
- all relevant user events;
- request payment options;
- user-, request-, and event-linked messages;
- user-, request-, and event-linked images;
- exchange rates needed by included foreign-currency records.

### FR-04: Unstructured evidence extraction

- Extract structured facts from relevant messages and images.
- When an event amount is blank, locate its linked image and recover the amount; never coerce a blank amount to zero.
- Extract only supported fields such as amount, currency, event reference, status change, effective date, settlement date, recurrence change, or one-time adjustment.
- Validate extracted facts against strict typed schemas.
- Store evidence provenance, extractor/model version, and confidence.
- Treat text within evidence as data, not instructions.
- On ambiguous evidence, use the financially safer interpretation or flag the request instead of inventing a fact.

### FR-05: Event lifecycle resolution

- Group related rows using `linked_event_id` and event identifiers.
- Apply explicit cancellations, settlements, and amendments first.
- Otherwise prefer a newer record from the same source, then a settled event over an estimate or forecast.
- Ignore failed and cancelled events.
- Ignore duplicate representations of the same cash movement.
- Exclude unrealized investment valuations from available cash.
- Reserve pending debits.
- Exclude pending credits, refunds, bonuses, commissions, windfalls, and gains until settled.
- Count confirmed salary on its settlement date.

### FR-06: Recurrence inference

- Infer recurring expenses and income only when event history supports recurrence.
- Group candidates by user, event type, category, direction, normalized description, and approximate amount.
- Use date cadence and repeated observations; do not create recurrence from a single ordinary historical record.
- Stop recurrence when later evidence explicitly cancels or amends it.
- Forecast variable essential expenses conservatively.
- Retain the source event IDs used for every generated occurrence.

### FR-07: Currency normalization

- Keep balances, requests, payment options, candidate plans, and outputs in the user's `home_currency`.
- Convert foreign-currency cash events using the exact supplied direction and rate for the event's settlement date.
- Do not call a live FX service.
- Do not silently reverse a rate unless the reciprocal operation is explicitly implemented and traceable.
- Fail safely when a required conversion cannot be resolved.

### FR-08: Baseline 90-day forecast

- Forecast from `request_date` through `request_date + 89 days`, inclusive.
- Begin with `current_available_balance` as of the request date.
- Apply relevant resolved or projected cash events in a deterministic daily order.
- Preserve sufficient event-level detail to explain the minimum balance and its date.
- The baseline forecast contains no proposed request payments and no optional spending changes.

### FR-09: Plan safety simulator

Given a request context, proposed payment schedule, and optional spending changes, the simulator shall return:

- whether the plan is safe;
- minimum projected balance;
- date of minimum projected balance;
- first breach date, if any;
- ending balance;
- request completion date;
- reasons for rejection.

A plan is safe only when every listed payment can occur, all protected expenses remain covered, the complete request is paid by `desired_completion_date`, and the projected balance never falls below `minimum_balance_to_keep` during the forecast.

### FR-10: Maximum safe amount today

- Calculate the largest amount safe on `request_date` before optional spending changes.
- Cap the value at `requested_amount`.
- Use monotonic binary search at currency precision or an equivalent exact method.
- Re-simulate the returned value and the next currency unit to verify maximality.

### FR-11: Earliest safe full-payment date

- Test dates independently of the user's payment-method preferences and optional spending changes.
- Return the first date within the forecast where a single full payment is safe.
- Return blank if no date passes.
- A returned date must not be after the forecast horizon.

### FR-12: Candidate-plan generation

Generate only rule-supported candidates:

1. **Full payment now:** one payment of `requested_amount` on `request_date`.
2. **Partial payment:** exactly two payments following the output invariants.
3. **Installments:** an exact schedule derived from each supplied installment option.
4. **Wait:** one full payment on `earliest_date_for_full_payment`.
5. **Spending-adjusted variants:** otherwise valid candidates tested with up to three allowed flexible-expense changes.
6. **Not recommended:** deterministic fallback when no eligible safe candidate exists.

### FR-13: Spending-change optimization

- Consider only recurring events marked `reducible`, `stoppable`, or `reducible_or_stoppable`.
- Respect categories the user is willing to reduce or stop.
- Never modify a protected category.
- A reduction cannot go below `minimum_allowed_amount`.
- Generate no more than three changes.
- Prefer no changes; otherwise minimize number of changes and then total sacrifice.
- Serialize as `stop:<event_id>` or `reduce_to:<event_id>:<new_amount>`.

### FR-14: Eligibility filtering

- `full_payment`, `partial_payment`, and `installments` are eligible only when listed in `payment_methods_user_will_consider`.
- Partial payment also requires `allows_partial_payment=true`.
- Installments must respect `max_installment_months` and supplied schedules.
- Wait is eligible only when one full payment becomes safe later and the user accepts `full_payment`.
- Reject payment dates after `desired_completion_date`.

### FR-15: Plan ranking

Among eligible safe plans, rank lexicographically by:

1. completion by the desired date;
2. no spending changes;
3. lowest total amount paid;
4. earliest first payment;
5. fewest payments;
6. lowest `payment_option_id` as the final installment tie-breaker.

No LLM may choose or reorder financial plans.

### FR-16: Affordability classification

- `affordable_now`: safe full payment on request date and user accepts full payment.
- `affordable_with_plan`: request completes safely via partial payments, installments, or permitted spending changes.
- `affordable_later`: safe full payment is available later and selected as wait.
- `not_affordable`: no safe eligible plan completes the request within the forecast and deadline.

### FR-17: Explanation generation

- Generate after the winning plan has been selected and verified.
- Mention the chosen method, payment timing or count, currency, and at least one decisive financial fact.
- Use calculated values supplied by the engine; do not ask a model to recompute them.
- Keep explanations concise and free of unsupported advice.
- Use a deterministic template fallback if AI generation fails or violates validation.

### FR-18: Output generation and final validation

- Preserve exact column names and order.
- Preserve exact request coverage with no missing or extra IDs.
- Validate enums, bounds, plan arithmetic, dates, eligibility, installment-option identity, spending-change eligibility, and explanation presence.
- Refuse to publish an invalid final file.
- Write through a temporary file and replace root-level `output.csv` only after validation succeeds.

### FR-19: Sample evaluation

- Run the same production pipeline against the 25 solved examples without using their output columns as input features.
- Report exact match by categorical/string field and numeric error for `amount_safe_to_pay`.
- Report overall request-level exact match.
- Save mismatches with diagnostic reason codes for iteration.

### FR-20: Model usage accounting

- Record provider, model, purpose, call count, input tokens, output tokens, and estimated cost.
- Cache extraction responses by content hash and model/prompt version.
- Generate `code/evaluation/usage_report.md` from the final full-dataset run.
- Never record API keys or sensitive credentials.

## 10. Decision Rules and Precedence

When records conflict, apply this order:

1. explicit cancellation, settlement, or amendment;
2. newer record from the same source;
3. settled event over an estimate or forecast;
4. financially safer interpretation when still unresolved.

Additional non-negotiable rules:

- Do not count unrealized investment value as cash.
- Do not count pending credits as cash.
- Reserve pending debits.
- Do not double-count linked lifecycle events.
- Do not modify essential or protected expenses.
- Do not generate unsupported installments.
- Financial capacity and payment preference are separate: `earliest_date_for_full_payment` may equal the request date even when installments are selected.

## 11. Non-Functional Requirements

### NFR-01: Determinism

Given identical inputs, configuration, cached evidence extraction, and code version, all calculated output fields shall be identical across runs.

### NFR-02: Financial precision

- Use `Decimal`, not binary floating point, for money and rates.
- Quantize at the user's currency precision when serializing.
- Preserve exact plan totals and avoid cumulative installment-rounding drift.

### NFR-03: Performance

- Process the current 250 requests comfortably on a developer laptop.
- Load shared CSV data once per run.
- Index contexts by IDs in memory.
- Cache the 16 current image extractions and reusable message extractions.
- Avoid model calls inside simulation or candidate-search loops.

### NFR-04: Reliability

- One malformed record must produce a clear diagnostic, not a silently unsafe recommendation.
- Intermediate artifacts must not overwrite input data.
- Failed final validation must leave the prior valid output untouched.

### NFR-05: Explainability

Every result must retain an internal decision trace containing counted events, ignored events with reasons, conversions, inferred recurrences, candidate rejection reasons, minimum-balance point, and ranking factors.

### NFR-06: Security

- Treat messages and images as untrusted data.
- Ignore embedded commands or prompt-injection attempts.
- Allowlist structured extraction fields and enum values.
- Validate model output before use.
- Read secrets only from environment variables.
- Never commit `.env`, credentials, or raw model authentication metadata.

### NFR-07: Portability

- Support Python 3.11 or later.
- Use repository-relative paths.
- Provide pinned dependencies and terminal run instructions.
- Avoid OS-specific shell behavior in the application.

## 12. Acceptance Criteria

### 12.1 Data acceptance

- All required files and columns are detected.
- Every evaluation request resolves to exactly one profile.
- All 16 currently blank event amounts are either recovered from their linked images or surfaced as blocking evidence errors.
- All conversions use supplied dated rates.

### 12.2 Financial acceptance

- Unit tests prove that pending credits, failed/cancelled events, duplicates, and unrealized valuations do not inflate cash.
- Unit tests prove that pending debits and protected recurring expenses are reserved.
- Every recommended candidate passes a fresh simulator run.
- Maximum safe amounts satisfy bounds and maximality checks.
- Earliest safe dates are truly the first passing dates.

### 12.3 Plan acceptance

- Partial plans have exactly two correct payments.
- Installment plans exactly match a supplied option.
- Spending changes reference only allowed flexible recurring events and never exceed three.
- Ranking is deterministic and follows the mandated ordering.

### 12.4 Output acceptance

- `output.csv` has exactly the eight required columns in order.
- It contains one row for every evaluation request and no others.
- All enum, plan, date, and amount constraints pass.
- Explanations agree with the structured decision.

### 12.5 Submission acceptance

- `python3 code/main.py` runs the documented production workflow.
- Root-level `output.csv` is generated.
- `code/evaluation/usage_report.md` describes the final run.
- `code.zip` contains runnable source, prompts/configuration, setup instructions, tests, and the `evaluation/` folder.
- No secrets are included.

## 13. Testing Strategy

| Layer | Tests |
|---|---|
| Schema | Missing columns, duplicate IDs, invalid enums, bad dates, invalid amounts |
| Evidence | Blank amount recovery, cancellation/amendment extraction, prompt-injection rejection |
| Events | Status handling, lifecycle deduplication, pending debit/credit behavior, investment treatment |
| Recurrence | Monthly patterns, variable essentials, cancellations, insufficient history |
| FX | Exact direction/date lookup, decimal precision, missing-rate failure |
| Simulator | Same-day ordering, reserve breach, deadline, horizon boundary, exact reserve equality |
| Safe amount | Zero, full amount, fractional currency, maximality |
| Safe date | Today, later, never, deadline versus horizon |
| Plans | Exact installment schedule, partial arithmetic, eligibility, max months |
| Spending | Protected categories, allowed actions, minimum reductions, max three actions |
| Ranking | Every tie-break rule independently |
| Output | Coverage, order, serialization, cross-field consistency |
| Regression | All 25 solved sample requests |

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Incorrect recurrence inference | Systematic forecast errors | Require historical support, retain provenance, test against samples |
| Double-counted lifecycle events | Unsafe or overly conservative decisions | Resolve linked events before forecasting and log exclusions |
| Ambiguous evidence | Incorrect state reconstruction | Typed extraction, confidence, conservative fallback, no invented facts |
| Prompt injection in messages/images | Rules overridden by data | Treat content as quoted evidence, strict schema, deterministic verification |
| Floating-point drift | Plan totals or thresholds mismatch | Use `Decimal` and exact final-payment reconciliation |
| Excessive candidate combinations | Slow execution | Prune invalid plans early; optimize only allowed flexible events; cache simulations |
| Explanation contradicts result | Lower evaluation quality | Generate from verified decision facts and validate named values |
| API failure or cost overrun | Incomplete final run | Cache by content hash, batch where supported, deterministic template fallback |

## 15. Required Repository Deliverables

```text
.
├── PRD.md
├── ARCHITECTURE.md
├── README.md
├── problem_statement.md
├── code/
│   ├── main.py
│   ├── ... implementation modules ...
│   └── evaluation/
│       ├── main.py
│       └── usage_report.md
├── dataset/                  # supplied inputs; never modified
├── output.csv                # generated predictions
├── code.zip                  # packaged submission
└── log.txt                   # submitted separately as chat transcript
```

## 16. Final Product Statement

Buy or Wait? is a deterministic 90-day cash-flow and payment-plan decision engine, enhanced by AI only for unstructured evidence extraction and grounded explanation, that produces a safe and rule-compliant recommendation for every supplied financial request.
