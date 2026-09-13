# Technical Architecture: Buy or Wait?

| Field | Decision |
|---|---|
| Architecture style | Extension of the existing starter repository; local batch pipeline |
| Primary language | Python 3.11+ |
| Data processing | pandas plus typed domain models |
| Money arithmetic | Python `Decimal` |
| AI boundary | Structured message/image extraction and grounded explanation only |
| Persistence | Supplied CSV/PNG inputs, local cache/artifacts, root `output.csv` |
| Database/API/UI | Not required and intentionally excluded |
| Required entry point | Existing `code/main.py` |
| Required output | Existing repository root `output.csv` |
| Product requirements | [`PRD.md`](./PRD.md) |
| Challenge specification | [`problem_statement.md`](./problem_statement.md) |

## 1. Architecture Objective

Extend the supplied starter solution through its existing `code/main.py` entry point. The resulting terminal application must read the participant-facing dataset, reconstruct each user's financial state, simulate the next 90 days, evaluate every rule-supported payment approach, select the highest-ranked safe eligible plan, and write a validated `output.csv` in the repository root.

The architecture isolates probabilistic interpretation from deterministic financial decisions:

- AI converts unstructured evidence into typed facts and may verbalize an already verified decision.
- Normal Python code owns event resolution, cash flow, currency conversion, plan generation, safety checks, optimization, ranking, and output validation.

## 2. Design Principles

1. **Rules are code:** no model is allowed to decide affordability or rank plans.
2. **Money is exact:** all monetary arithmetic uses `Decimal`.
3. **Evidence is untrusted:** messages and image text are treated as data, never instructions.
4. **Safety is replayable:** every selected plan is verified by the same simulator immediately before output.
5. **Capacity is distinct from preference:** calculate what is financially possible before filtering what the user accepts.
6. **No invented facts:** only supplied, extracted, or conservatively inferred information enters the forecast.
7. **Provenance everywhere:** resolved events, recurrences, conversions, exclusions, and decisions retain source IDs.
8. **Fail closed:** ambiguity must not create additional available money.
9. **Batch first:** no database, API, frontend, or distributed infrastructure is needed.
10. **Optimize model calls:** extraction happens once per relevant evidence item, never inside simulation loops.

## 3. System Context

```mermaid
flowchart TB
    Inputs["Supplied CSVs and PNGs"] --> Engine["Buy or Wait? batch engine"]
    Model["Multimodal model"] <--> Engine
    Env["Environment configuration"] --> Engine
    Engine --> Output["Root output.csv"]
    Engine --> Eval["Diagnostics and usage report"]
```

The model integration is optional at runtime only when all needed evidence has already been cached. No live banking, market, foreign-exchange, database, or web service is part of the decision path.

## 4. End-to-End Data Flow

```mermaid
flowchart TB
    A["Load and validate dataset"] --> B["Index records by IDs"]
    B --> C["Extract message and image facts"]
    C --> D["Resolve event lifecycles"]
    D --> E["Normalize currency and recurrence"]
    E --> F["Build 90-day request context"]
    F --> G["Calculate capacity"]
    G --> H["Generate candidate plans"]
    H --> I["Simulate and validate plans"]
    I --> J["Filter and rank candidates"]
    J --> K["Generate grounded explanation"]
    K --> L["Validate and write output.csv"]
```

### 4.1 Processing sequence

1. Load shared datasets once.
2. Validate schemas, IDs, enums, dates, and numeric domains.
3. Build in-memory indexes keyed by `user_id`, `request_id`, `event_id`, and date/currency tuple.
4. Extract and cache relevant facts from messages and PNGs.
5. Resolve linked financial-event lifecycles and evidence amendments.
6. For each request, normalize events into home currency and generate supported recurring occurrences.
7. Build a baseline 90-day timeline.
8. Calculate maximum safe payment today and earliest safe full-payment date without optional spending changes.
9. Generate all eligible full, partial, installment, wait, and spending-adjusted candidates.
10. Simulate each candidate and reject unsafe or invalid plans.
11. Rank remaining plans deterministically.
12. Produce a grounded explanation from verified decision facts.
13. Validate the complete output file and atomically replace root-level `output.csv`.

## 5. Recommended Technology Stack

| Concern | Technology | Reason |
|---|---|---|
| Runtime | Python 3.11+ | Strong CSV, date, decimal, optimization, and AI ecosystem |
| Tables | pandas | Efficient loading, inspection, filtering, and joins |
| Domain validation | Pydantic 2 | Typed boundaries for CSV and model-derived facts |
| Money | `decimal.Decimal` | Exact comparison and plan arithmetic |
| Dates | `datetime.date` | Explicit daily forecast calculations |
| AI client | Provider SDK behind an adapter | Supports structured text/image extraction without coupling core logic |
| Images | Pillow | Input verification and model-ready image handling |
| Tests | pytest | Unit, property, regression, and integration testing |
| Configuration | Environment variables plus typed settings | No committed secrets |
| Output | Python CSV/pandas | Exact submission schema |

Minimum likely dependencies:

```text
pandas
pydantic
Pillow
pytest
<one selected model-provider SDK>
```

Do not add FastAPI, Next.js, Supabase, PostgreSQL, Redis, or a vector database to the judged solution.

## 6. Logical Components

```mermaid
flowchart LR
    subgraph Ingestion
        Loader["Dataset loader"]
        Extractor["Evidence extractor"]
    end
    subgraph Finance
        Resolver["State resolver"]
        Simulator["90-day simulator"]
    end
    subgraph Decision
        Generator["Plan generator"]
        Ranker["Validator and ranker"]
    end
    Loader --> Resolver
    Extractor --> Resolver
    Resolver --> Simulator
    Simulator --> Generator
    Generator --> Ranker
```

### 6.1 Dataset loader

Responsibilities:

- resolve repository-relative paths;
- read each supplied CSV with explicit converters;
- map blank values to `None`, never zero;
- parse list-like profile columns into sets;
- parse dates and timestamps;
- validate required files and columns;
- reject duplicate IDs or orphaned mandatory joins;
- return immutable or copy-safe typed records and indexes.

### 6.2 Evidence extractor

Responsibilities:

- select only evidence relevant to a user/request/event;
- recover missing event amounts from linked images;
- extract amendments, cancellations, confirmations, settlement dates, updated amounts, and one-time adjustments;
- validate extraction against strict schemas;
- save provenance and confidence;
- cache by evidence hash, model, prompt version, and schema version;
- record token usage and cost;
- reject instructions embedded in message or image content.

It does not calculate balances, generate payment plans, or decide affordability.

### 6.3 Event lifecycle resolver

Responsibilities:

- connect events through `linked_event_id`;
- attach structured evidence facts;
- select the authoritative state of each cash movement;
- remove duplicates;
- classify events as counted, reserved, projected, non-cash, or ignored;
- emit explicit reason codes for every exclusion.

Suggested exclusion/resolution reason codes:

```text
FAILED
CANCELLED
DUPLICATE
SUPERSEDED
PENDING_CREDIT
UNREALIZED_NON_CASH
OUTSIDE_HORIZON
UNRESOLVED_AMOUNT
UNSUPPORTED_RECURRENCE
```

### 6.4 Recurrence engine

Responsibilities:

- identify repeated historical series using user, category, direction, normalized merchant/description, approximate amount, and cadence;
- infer the next occurrence dates within the horizon;
- estimate variable essential amounts conservatively;
- apply cancellation or amendment cutoffs;
- avoid extrapolation from isolated events;
- retain the source series and inference confidence.

The recurrence engine should be deterministic. A model may help normalize multilingual descriptions, but the cadence and forecast rules remain code.

### 6.5 Currency converter

Responsibilities:

- normalize eligible cash events to `home_currency`;
- use the event settlement date and exact supplied currency direction;
- preserve original amount/currency and applied rate;
- quantize only at defined boundaries;
- fail closed when a required rate is absent.

### 6.6 Request context builder

Responsibilities:

- combine one request, one profile, resolved events, recurrences, payment offers, and evidence;
- establish `[request_date, request_date + 89 days]`;
- separate baseline cash events from proposed request payments;
- expose protected and flexible expense sets;
- provide stable inputs to all decision functions.

### 6.7 Financial simulator

Responsibilities:

- apply normalized cash events and proposed payments to the running balance;
- apply optional spending changes to future eligible recurring occurrences;
- enforce minimum-balance and completion-date rules;
- return a complete trace and reason codes;
- memoize repeated simulations using a stable context/plan fingerprint.

The simulator is the single authority for “safe.” No candidate bypasses it.

### 6.8 Capacity calculators

Two independent calculations operate on the no-change baseline:

- `amount_safe_to_pay`: maximum safe single payment on the request date, capped at requested amount;
- `earliest_date_for_full_payment`: first date within the 90-day horizon where one full payment is safe.

These calculations ignore payment-method preferences. Preferences are applied later during eligibility filtering.

### 6.9 Plan generator

Responsibilities:

- generate full payment now;
- generate the rule-defined two-payment partial plan;
- expand every supplied installment option exactly;
- generate wait when a later safe full-payment date exists;
- generate permitted spending-adjusted variants only when necessary;
- include deterministic `not_recommended` fallback.

### 6.10 Plan validator and ranker

Responsibilities:

- validate dates, amounts, totals, deadline, method eligibility, exact installment identity, and spending actions;
- run or confirm simulator safety;
- rank candidates according to the mandated lexicographic rules;
- produce the final structured decision and supporting metrics.

### 6.11 Explanation generator

Responsibilities:

- accept only verified structured decision facts;
- produce a concise explanation in the user's financial context;
- validate that mentioned amounts, dates, and method agree with the decision;
- fall back to a deterministic template on failure.

### 6.12 Output writer

Responsibilities:

- serialize exact columns in exact order;
- format monetary values consistently;
- validate row coverage and cross-field invariants;
- write to a temporary file;
- atomically replace root-level `output.csv` after all checks pass.

## 7. Existing Repository Integration and Commands

### 7.1 Integration contract

The official repository is the implementation workspace. The IDE must continue within it rather than generate a separate application beside it.

- Read `AGENTS.md`, `README.md`, and `problem_statement.md` before coding.
- Extend the existing `code/main.py`; keep it as the default production entry point.
- Extend `code/evaluation/main.py` for sample/final evaluation.
- Populate `code/evaluation/usage_report.md` from the final full-dataset run.
- Keep implementation code, prompts, dependencies, and tests under `code/`.
- Read the supplied input files from `dataset/` without modifying them.
- Use `dataset/output.csv` only as the blank schema template.
- Write completed predictions to root-level `output.csv`.
- Preserve the official `python3 code/main.py` invocation.
- Let the implementing IDE inspect the repository and choose its own work breakdown. This architecture defines boundaries and contracts, not implementation phases.

### 7.2 Repository structure

The existing files are mandatory. Additional modules shown below are allowed organizational examples, not a prescribed task breakdown.

```text
.
├── AGENTS.md
├── ARCHITECTURE.md
├── PRD.md
├── README.md
├── problem_statement.md
├── dataset/
│   └── ... supplied files, unchanged ...
├── code/
│   ├── main.py                    # existing required entry point
│   ├── requirements.txt           # add exact runtime/test dependencies
│   ├── buy_or_wait/               # optional internal package
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── money.py
│   │   ├── ingestion/
│   │   │   ├── loader.py
│   │   │   ├── indexes.py
│   │   │   └── schema_validation.py
│   │   ├── evidence/
│   │   │   ├── adapter.py
│   │   │   ├── messages.py
│   │   │   ├── images.py
│   │   │   ├── prompts.py
│   │   │   ├── cache.py
│   │   │   └── usage.py
│   │   ├── finance/
│   │   │   ├── lifecycle.py
│   │   │   ├── recurrence.py
│   │   │   ├── currency.py
│   │   │   ├── context.py
│   │   │   └── simulator.py
│   │   ├── decision/
│   │   │   ├── capacity.py
│   │   │   ├── candidates.py
│   │   │   ├── spending.py
│   │   │   ├── eligibility.py
│   │   │   ├── ranking.py
│   │   │   └── explanation.py
│   │   └── output/
│   │       ├── formatter.py
│   │       ├── validator.py
│   │       └── writer.py
│   ├── tests/                     # implementation tests
│   │   ├── unit/
│   │   ├── integration/
│   │   └── regression/
│   └── evaluation/
│       ├── main.py                # existing evaluation entry point
│       └── usage_report.md        # existing required report target
├── artifacts/                     # optional ignored cache/diagnostics
├── output.csv                      # generated final predictions
└── log.txt                         # chat transcript
```

`code/main.py` may remain a thin coordinator while helper modules hold the implementation, but the IDE may choose a simpler organization if it preserves the same entry point and contracts.

### 7.3 Clone and update commands

Fresh clone:

```bash
git clone https://github.com/interviewstreet/hackerrank-orchestrate-september26.git
cd hackerrank-orchestrate-september26
```

Existing checkout:

```bash
cd hackerrank-orchestrate-september26
git status
git pull --ff-only origin main
```

Review `git status` before pulling. Do not overwrite or discard uncommitted work.

### 7.4 Environment setup

The IDE must add either `code/requirements.txt` or `code/pyproject.toml`. The commands below use `code/requirements.txt`.

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

If the selected model requires credentials, the implementation may add `code/.env.example`. Copy it locally and populate only `.env`, which must remain uncommitted.

```powershell
# Windows PowerShell
Copy-Item code/.env.example .env
```

```bash
# macOS/Linux
cp code/.env.example .env
```

Skip the environment-file commands when no external model credential is required.

### 7.5 Run, test, validate, and package

Official production command from the repository root:

```bash
python3 code/main.py
```

Windows equivalent inside the activated environment:

```powershell
python code/main.py
```

Tests and evaluation, after implemented:

```bash
python -m pytest code/tests -q
python code/evaluation/main.py
```

Validate final output coverage and columns:

```bash
python -c "import csv; f=open('output.csv', encoding='utf-8'); r=list(csv.DictReader(f)); print('rows=', len(r)); print('columns=', list(r[0]) if r else [])"
```

Review changes:

```bash
git status --short
git diff --check
```

Create and verify the submission code archive:

```bash
python -m zipfile -c code.zip code README.md PRD.md ARCHITECTURE.md
python -m zipfile -t code.zip
```

Do not include `dataset/`, `.env`, credentials, model caches, or diagnostic artifacts in `code.zip`. Submit root-level `output.csv` and the chat transcript separately.

## 8. Core Domain Models

The names below are illustrative; exact implementation may use Pydantic dataclasses or frozen dataclasses.

```python
class Money:
    amount: Decimal
    currency: str

class Request:
    request_id: str
    user_id: str
    request_date: date
    request_type: RequestType
    requested_amount: Decimal
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str

class Profile:
    user_id: str
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    protected_categories: frozenset[str]
    reducible_categories: frozenset[str]
    stoppable_categories: frozenset[str]
    accepted_payment_methods: frozenset[str]
    max_installment_months: int | None

class ResolvedCashEvent:
    source_event_ids: tuple[str, ...]
    user_id: str
    effective_date: date
    direction: Literal["credit", "debit"]
    amount_home: Decimal
    category: str
    status: str
    protected: bool
    flexibility: str
    minimum_allowed_amount: Decimal | None
    recurrence_series_id: str | None
    resolution_reason: str

class Payment:
    date: date
    amount: Decimal

class SpendingChange:
    action: Literal["stop", "reduce_to"]
    event_id: str
    new_amount: Decimal | None

class CandidatePlan:
    method: PaymentMethod
    payments: tuple[Payment, ...]
    changes: tuple[SpendingChange, ...]
    payment_option_id: str | None
    total_payable: Decimal

class SimulationResult:
    safe: bool
    minimum_balance: Decimal
    minimum_balance_date: date
    ending_balance: Decimal
    first_breach_date: date | None
    completion_date: date | None
    rejection_reasons: tuple[str, ...]
    trace: tuple[DailyLedgerEntry, ...]

class Decision:
    request_id: str
    amount_safe_to_pay: Decimal
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: date | None
    spending_changes_needed: str
    decision_explanation: str
```

## 9. Event-State Reconstruction

### 9.1 Resolution order

For each logical lifecycle:

1. Collect the original event, rows linking to it, and direct evidence.
2. Apply explicit cancellation, settlement, or amendment.
3. If competing records remain, prefer the newest record from the same source.
4. Prefer settled evidence over an estimate or forecast.
5. If still ambiguous, choose the interpretation that produces less available cash.
6. Emit either one resolved cash event or an ignored/non-cash record with a reason.

### 9.2 Cash-state matrix

| Direction/state | Forecast treatment |
|---|---|
| Settled debit already reflected in current balance | Historical evidence; do not subtract again |
| Settled credit already reflected in current balance | Historical evidence; do not add again |
| Future scheduled debit | Subtract on effective/settlement date |
| Pending debit | Reserve/subtract conservatively on supplied date |
| Future confirmed salary | Add only on settlement date |
| Pending credit/refund/bonus/windfall | Ignore until settled |
| Failed/cancelled event | Ignore |
| Unrealized investment valuation | Non-cash; ignore |
| Linked settlement/refund | Resolve lifecycle; never double-count |

Current balance is the forecast opening balance. Historical settled events are used to infer recurrence and understand state, not replayed into that opening balance.

## 10. Recurrence Inference

### 10.1 Candidate grouping

Group historical events using:

- same user;
- same direction;
- same category and compatible event type;
- normalized description/merchant similarity;
- amount within a configured tolerance;
- cadence compatible with weekly, biweekly, monthly, or another clearly supported interval.

### 10.2 Evidence threshold

A practical initial rule is at least two or three consistent historical observations, selected through sample-based validation. The threshold is configuration, not a label hardcoded to evaluation requests.

### 10.3 Variable essential spending

For protected variable categories, use a conservative statistic over recent supported occurrences, such as an upper median or recent maximum. The chosen method must be deterministic and evaluated against solved samples.

### 10.4 Projected occurrences

Every projection records:

- date;
- amount;
- source series/event IDs;
- inferred cadence;
- protected/flexible status;
- adjustment eligibility.

## 11. Currency Conversion

```python
def to_home_currency(event, home_currency, rates) -> Decimal:
    if event.currency == home_currency:
        return event.amount
    key = (event.settlement_date, event.currency, home_currency)
    rate = rates.require(key)
    return event.amount * rate
```

Rules:

- Use `settlement_date` for the dated rate.
- Use only the supplied `from_currency -> to_currency` direction.
- Retain full decimal precision internally.
- Quantize at output and currency-comparison boundaries.
- Treat a missing required rate as a data error; do not fetch a live rate.

If sample analysis proves that an explicitly supplied reciprocal is intended, implement the reciprocal as a named, tested rule with provenance rather than silent fallback.

## 12. 90-Day Simulator

### 12.1 Horizon

```text
start = request_date
end   = request_date + 89 days
```

### 12.2 Same-day ordering

Same-day processing must be deterministic. A conservative default is:

1. confirmed opening-day credits already represented by opening balance: no replay;
2. due protected and fixed debits;
3. due request payments;
4. other due debits;
5. confirmed new credits settling that day.

The exact convention should be locked by sample regression and applied consistently. Regardless of ordering, no credit is available before its confirmed settlement.

### 12.3 Simulator pseudocode

```python
def simulate(context, plan, changes=()):
    ledger = apply_changes(context.timeline, changes)
    ledger = merge_payments(ledger, plan.payments)
    balance = context.opening_balance
    minimum = balance
    first_breach = None

    for day in context.horizon:
        for entry in ordered_entries(ledger[day]):
            balance += entry.signed_amount
            minimum = min(minimum, balance)
            if balance < context.minimum_balance and first_breach is None:
                first_breach = day

    completion_date = plan_completion_date(plan)
    completed = plan.total_paid == context.request.requested_amount
    before_deadline = completion_date is not None and completion_date <= context.request.desired_completion_date

    return SimulationResult(
        safe=first_breach is None and completed and before_deadline,
        minimum_balance=minimum,
        first_breach_date=first_breach,
        completion_date=completion_date,
        # trace and other metrics omitted here
    )
```

For capacity searches, the simulator may use a special probe plan that checks balance safety without requiring request completion; the public candidate validator still requires full completion.

## 13. Capacity Algorithms

### 13.1 Maximum safe amount today

The safety predicate is monotonic: if amount `x` is unsafe, any larger same-day amount is unsafe under the same baseline.

```python
low = Decimal("0")
high = requested_amount

while high - low > currency_unit:
    mid = quantized_midpoint(low, high)
    if probe_single_payment(request_date, mid).keeps_reserve:
        low = mid
    else:
        high = mid - currency_unit

safe_amount = largest_verified_value(low, high)
```

Postconditions:

- `0 <= safe_amount <= requested_amount`;
- `safe_amount` passes the reserve check;
- `safe_amount + currency_unit` fails unless capped by `requested_amount`.

Optional spending changes are never used in this calculation.

### 13.2 Earliest safe full-payment date

Iterate every date from `request_date` through the horizon in chronological order. Return the first date whose single full-payment probe keeps the user above the reserve for the remaining horizon. This field is calculated before payment-preference filtering and without optional spending changes.

## 14. Candidate Plan Generation

### 14.1 Full payment

```text
request_date:requested_amount
```

Eligible only when `full_payment` is accepted. It may be tested with allowed spending changes when the no-change version fails.

### 14.2 Partial payment

Generate only if all prerequisites hold:

- request allows partial payment;
- profile accepts `partial_payment`;
- `0 < amount_safe_to_pay < requested_amount`;
- earliest safe full-payment date exists and is on/before the desired date.

Exact schedule:

```text
request_date:amount_safe_to_pay
earliest_date_for_full_payment:(requested_amount - amount_safe_to_pay)
```

Reconcile the second payment exactly so the two payments sum to the requested amount.

### 14.3 Installments

For each supplied installment option:

1. Verify that the user accepts installments.
2. Verify `number_of_payments` against `max_installment_months`.
3. Expand dates from `first_payment_date` using `payment_frequency_days`.
4. Use the supplied payment amount and reconcile only as explicitly supported by the supplied `total_payable_amount`.
5. Ensure completion by the desired date.
6. Preserve `payment_option_id` for exact-match validation and tie-breaking.

Do not synthesize new installment counts, dates, amounts, or fees.

### 14.4 Wait

```text
earliest_date_for_full_payment:requested_amount
```

Eligible only when the date is later than the request date, no later than the desired completion date, and the user accepts full payment.

### 14.5 Spending-adjusted candidates

Only generate these when they can make an otherwise valid candidate safe. Candidate actions are derived from recurring flexible events and profile permissions.

## 15. Spending Optimizer

### 15.1 Eligible actions

| Event flexibility | Permitted action |
|---|---|
| `fixed` | None |
| `reducible` | `reduce_to`, not below `minimum_allowed_amount` |
| `stoppable` | `stop` |
| `reducible_or_stoppable` | One of `reduce_to` or `stop`, never both |

Profile category permissions and protected categories further restrict eligibility.

### 15.2 Search strategy

1. Compute each action's cash-flow relief over the horizon.
2. Discard actions that occur too late to resolve the candidate's breach.
3. Test no-change candidate first.
4. Search one-action combinations, then two, then three.
5. Within the same action count, prioritize smaller total lifestyle reduction.
6. Stop at the first deterministic best safe set for that plan.

The current maximum of three changes keeps exhaustive combinations feasible after pruning. Cache simulator results by candidate and action-set fingerprint.

## 16. Eligibility, Ranking, and Classification

### 16.1 Candidate pipeline

```mermaid
flowchart LR
    Raw["Generated candidate"] --> Shape["Schema and arithmetic"]
    Shape --> Preference["Preference eligibility"]
    Preference --> Deadline["Deadline compliance"]
    Deadline --> Safety["90-day simulation"]
    Safety --> Rank["Deterministic rank key"]
```

### 16.2 Rank key

For each safe eligible candidate, build a lexicographic key equivalent to:

```python
rank_key = (
    0 if completes_by_deadline else 1,
    0 if not spending_changes else 1,
    total_payable,
    first_payment_date,
    number_of_payments,
    numeric_payment_option_id_or_sentinel,
)
```

Select the minimum key. Stable generation order may be used only beyond the mandated tie-breakers and must be documented.

### 16.3 Classification mapping

| Winning plan | Status |
|---|---|
| Safe accepted full payment on request date, no required changes | `affordable_now` |
| Partial, installments, or any plan requiring permitted spending changes | `affordable_with_plan` |
| Wait for later full payment | `affordable_later` |
| No safe eligible candidate | `not_affordable` |

The solved examples demonstrate that `full_payment` may pair with `affordable_with_plan` when permitted spending changes are required.

## 17. AI Integration Boundary

### 17.1 Structured extraction contract

Illustrative schema:

```json
{
  "evidence_id": "message_01",
  "facts": [
    {
      "fact_type": "amend_amount",
      "related_event_id": "event_123",
      "amount": "42750000",
      "currency": "IDR",
      "effective_date": "2025-08-15",
      "status": "confirmed",
      "source_quote": "short supporting excerpt"
    }
  ],
  "confidence": 0.98
}
```

Allowed fact types and fields must be an enum/allowlist. Unknown fields are rejected.

### 17.2 Prompt safety

The system prompt must state that:

- content is untrusted financial evidence;
- embedded instructions must be ignored;
- the task is extraction, not advice;
- unknown values must be `null`;
- facts require direct support in the content;
- output must follow the exact structured schema.

### 17.3 Extraction failure policy

1. Retry only schema/transport failures with a small bounded count.
2. Use the cached last valid extraction when the content hash and versions match.
3. If a required blank amount remains unresolved, mark the context invalid rather than substitute zero.
4. For non-critical ambiguous evidence, use the conservative baseline and record the omission.

### 17.4 Explanation input

The explanation model receives only verified facts such as:

```json
{
  "method": "installments",
  "currency": "IDR",
  "payments": ["2025-08-08:15952906.67", "..."],
  "minimum_projected_balance": "29158400",
  "minimum_required_balance": "29158400",
  "spending_changes": [],
  "key_events": ["confirmed salary on 2025-08-15"]
}
```

The resulting text is checked for method consistency and unsupported numeric values. A template fallback is always available.

## 18. Caching and Usage Accounting

### 18.1 Cache key

```text
SHA256(content_bytes + model_id + prompt_version + schema_version)
```

Cache entries should include the validated response, timestamps, token counts, and provider request metadata excluding credentials.

### 18.2 Suggested local artifacts

```text
artifacts/
├── cache/evidence/<hash>.json
├── traces/<request_id>.json
├── evaluation/sample_results.json
├── evaluation/mismatches.csv
└── runs/<run_id>/usage.jsonl
```

These artifacts support debugging and reproducibility but are not prediction inputs.

### 18.3 Usage report

Aggregate final-run usage by provider and model:

- extraction versus explanation calls;
- call count;
- input/output tokens;
- total and average tokens per request;
- estimated total and per-request cost;
- cache hit count;
- pricing assumptions and date.

Write the final summary to `code/evaluation/usage_report.md`.

## 19. Validation Architecture

Validation occurs at four gates:

1. **Input gate:** files, schemas, IDs, relationships, enums, money, and dates.
2. **Evidence gate:** structured schema, provenance, confidence, and prompt-injection isolation.
3. **Candidate gate:** method eligibility, arithmetic, schedule identity, deadline, spending actions, and simulation safety.
4. **Output gate:** full coverage, exact columns/order, serialization, and cross-field invariants.

No invalid object crosses into the next layer.

## 20. Error Handling

| Error class | Behavior |
|---|---|
| Missing required dataset/file | Stop run with path and remediation |
| Schema or primary-key error | Stop run before predictions |
| Orphaned required relationship | Stop or mark affected request invalid with explicit diagnostics |
| Missing required image file/amount | Do not treat as zero; stop affected prediction or full run based on strict mode |
| Missing FX rate | Fail closed and identify date/pair |
| Model transport/schema failure | Bounded retry, cache fallback, then conservative handling |
| Candidate invariant failure | Reject candidate and retain reason |
| Final output validation failure | Do not replace existing root output |

For a judged batch run, strict mode should stop before writing a partially valid submission.

## 21. Observability and Decision Traces

Each request trace should contain:

- input record IDs and content hashes;
- opening balance and minimum balance;
- resolved, projected, and ignored events with reasons;
- applied FX rates;
- recurrence series and generated occurrences;
- baseline minimum balance/date;
- calculated safe amount and earliest safe date;
- every candidate, eligibility result, simulation result, and rejection reason;
- winning rank key;
- explanation source facts;
- model/cache/usage metadata.

Use structured JSON or JSON Lines. Do not include secrets.

## 22. Testing Architecture

### 22.1 Unit tests

- money parsing, quantization, and formatting;
- CSV enums and pipe-delimited sets;
- lifecycle precedence and duplicate removal;
- pending/failed/cancelled/unrealized event semantics;
- currency lookup and conversion;
- recurrence cadence and cancellation cutoff;
- simulator balance and breach dates;
- safe amount maximality;
- earliest safe date minimality;
- plan expansion, arithmetic, and eligibility;
- spending-action rules;
- every rank tie-breaker;
- output cross-field invariants.

### 22.2 Property tests

- increasing a same-date proposed payment cannot improve reserve safety;
- `amount_safe_to_pay` is always within bounds;
- a selected plan always passes independent re-simulation;
- partial payments sum exactly to requested amount;
- chronological serialization is stable;
- removing a confirmed credit cannot increase safe capacity;
- adding a protected debit cannot increase safe capacity.

### 22.3 Regression tests

Run all 25 `sample_requests.csv` rows through the exact production pipeline. The expected output columns must never be loaded into the request context.

### 22.4 Integration test

From a clean checkout with configured credentials/cache:

```bash
python3 code/main.py
python3 code/evaluation/main.py
```

Confirm root `output.csv`, full request coverage, and a populated final usage report.

## 23. CLI Contract

Minimum production command:

```bash
python3 code/main.py
```

Recommended optional flags:

```text
--dataset-dir PATH       default: <repo>/dataset
--output PATH            default: <repo>/output.csv
--cache-dir PATH         default: <repo>/artifacts/cache
--strict                 fail on unresolved required evidence
--offline                require cached evidence; make no model calls
--request-id ID          debug one request without changing production defaults
--trace-dir PATH         emit decision traces
```

The default command must remain sufficient for evaluation.

## 24. Performance and Complexity

Let `E` be financial events, `R` requests, `P` payment options, and `F` eligible flexible actions.

- Initial indexing: `O(E + R + P)`.
- Per-request baseline timeline: proportional to that user's resolved/projected events over 90 days.
- Safe-date search: at most 90 simulator probes.
- Safe-amount search: `O(log(requested_amount / currency_unit))` probes.
- Spending search: bounded to combinations of size at most three after pruning; simulator memoization prevents repeated work.
- Model calls: `O(relevant messages + relevant images + optional explanations)`, independent of simulation candidate count.

The current dataset size is small enough for an in-memory process; introducing a database or distributed system would add risk without evaluation benefit.

## 25. Architectural Decisions

| ID | Decision | Rationale |
|---|---|---|
| ADR-001 | Use a Python batch program | Matches CSV-centric judged workflow and financial simulation |
| ADR-002 | Exclude Supabase/database | No persistence requirement; inputs and output are files |
| ADR-003 | Exclude web UI/API | Not evaluated and consumes hackathon time |
| ADR-004 | Use `Decimal` | Avoid financial rounding errors |
| ADR-005 | Keep AI outside financial core | Enables deterministic verification and protects against hallucination |
| ADR-006 | Use one simulator for all plans | Prevents divergent safety definitions |
| ADR-007 | Calculate capacity before preferences | Required semantics for safe amount and earliest full-payment date |
| ADR-008 | Cache evidence extraction | Reduces cost, latency, and run-to-run variation |
| ADR-009 | Atomically write final output | Prevents partial/corrupt submissions |
| ADR-010 | Retain request-level traces | Makes sample mismatches and hidden-risk assumptions debuggable |

## 26. Definition of Done

The architecture is implemented when:

- the default terminal command loads only participant-facing inputs;
- all required evidence is resolved without treating blank amounts as zero;
- all monetary and date rules are deterministic and tested;
- every selected plan passes independent 90-day re-simulation;
- root `output.csv` passes every schema and cross-field invariant;
- all 25 samples run through the production path and receive an evaluation report;
- the final model usage report reflects the actual full-dataset run;
- the submission package contains runnable code and no secrets.
