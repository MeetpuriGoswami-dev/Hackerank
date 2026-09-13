# Model Usage & Cost Report: Buy or Wait?

| Field | Value |
|---|---|
| Challenge | HackerRank Orchestrate, September 2026 |
| Application | Buy or Wait? AI Financial Decision Agent |
| Run Date | 2026-09-13 |
| Dataset | `dataset/requests.csv` (250 requests) |
| System Architecture | Deterministic Simulation Core + Gemini Multimodal Evidence Extraction |

## 1. Executive Summary

This report documents actual AI model calls, token consumption, and estimated cost for the final full-dataset run processing all 250 evaluation requests.

The financial decision engine utilizes a **deterministic core** for cash-flow reconstruction, 90-day balance simulation, capacity calculation, candidate plan generation, spending optimization, and lexicographical ranking. When `GEMINI_API_KEY` is present, Google Gemini (`gemini-2.5-flash`) is invoked for multimodal evidence extraction (PNG amounts & multilingual message facts) and decision explanation formatting.

## 2. Model Usage Breakdown (Actual Telemetry)

| Provider | Model Name | Primary Task | Model Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|---|---|
| Google / Gemini | gemini-2.5-flash | Multimodal Evidence Extraction & OCR | 0 | 0 | 0 | 0 | $0.0000 |
| Google / Gemini | gemini-2.5-flash | Multilingual Message Fact Parsing | 0 | 0 | 0 | 0 | $0.0000 |
| **Total** | | | **0** | **0** | **0** | **0** | **$0.0000** |

> **Note on Telemetry**: In environments where `GEMINI_API_KEY` is not populated or cached extractions are reused, the pipeline operates with zero live API calls. Telemetry counters capture actual model response metadata when live API calls occur.

## 3. Per-Request Metrics (250 Requests)

- **Total Model Calls:** 0
- **Total Input Tokens:** 0
- **Total Output Tokens:** 0
- **Total Tokens:** 0
- **Average Input Tokens / Request:** 0.0 tokens
- **Average Output Tokens / Request:** 0.0 tokens
- **Average Total Tokens / Request:** 0.0 tokens
- **Total Estimated Run Cost:** $0.0000 USD
- **Average Cost / Request:** $0.000000 USD

## 4. Cost Assumptions & Pricing Standard

- **Gemini 2.5 Flash Pricing Standard:**
  - Input: $0.075 per 1,000,000 tokens
  - Output: $0.30 per 1,000,000 tokens
- **Caching Optimization:** Evidence extraction results are cached locally by content hash and model version in `.cache_image_extracts/`, eliminating redundant API calls on subsequent runs.
- **Credentials & Privacy:** No API keys, tokens, session cookies, or private credentials are included in this repository or submitted artifacts.
