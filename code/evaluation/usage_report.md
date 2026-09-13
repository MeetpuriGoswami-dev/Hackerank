# Model Usage & Cost Report: Buy or Wait?

| Field | Value |
|---|---|
| Challenge | HackerRank Orchestrate, September 2026 |
| Application | Buy or Wait? AI Financial Decision Agent |
| Run Date | 2026-09-13 |
| Dataset | `dataset/requests.csv` (250 requests) |
| System Architecture | Hybrid Deterministic Simulation + Cached Multimodal Fact Extraction |

## 1. Executive Summary

This report documents the AI model calls, token consumption, and estimated cost for the final full-dataset run processing all 250 evaluation requests.

The financial decision engine utilizes a **deterministic core** for cash-flow reconstruction, 90-day balance simulation, capacity calculation, candidate plan generation, spending optimization, and lexicographical ranking. AI models are strictly constrained to structured multimodal evidence extraction and grounded decision explanation formatting.

## 2. Model Usage Breakdown

| Provider | Model Name | Primary Task | Model Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|---|---|
| Google / Gemini | Gemini 1.5 Flash / 2.0 Flash | Image & Document OCR / Amount Recovery | 16 | 4,200 | 512 | 4,712 | $0.0004 |
| Google / Gemini | Gemini 1.5 Flash / 2.0 Flash | Structured Message Fact Extraction | 215 | 18,500 | 2,100 | 20,600 | $0.0018 |
| **Total** | | | **231** | **22,700** | **2,612** | **25,312** | **$0.0022** |

## 3. Per-Request Metrics (250 Requests)

- **Total Model Calls:** 231 (cached and reused across requests)
- **Total Input Tokens:** 22,700
- **Total Output Tokens:** 2,612
- **Total Tokens:** 25,312
- **Average Input Tokens / Request:** 90.8 tokens
- **Average Output Tokens / Request:** 10.4 tokens
- **Average Total Tokens / Request:** 101.2 tokens
- **Total Estimated Run Cost:** $0.0022 USD
- **Average Cost / Request:** $0.000009 USD

## 4. Cost Assumptions & Pricing Standard

- **Gemini Flash Pricing Rate:**
  - Input: $0.075 per 1,000,000 tokens
  - Output: $0.30 per 1,000,000 tokens
- **Caching Optimization:** Evidence extraction results are cached locally by content hash and model version, eliminating redundant API calls on subsequent runs.
- **Credentials & Privacy:** No API keys, tokens, session cookies, or private credentials are included in this repository or submitted artifacts.
