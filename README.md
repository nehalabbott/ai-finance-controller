# ai-finance-controller
For reconcillation


# AI Finance Controller

A high-throughput, multi-source reconciliation engine built to detect revenue leaks, missing gateway settlements, and contractual fee discrepancies. By combining a deterministic algebraic filter with a batched LLM diagnostic agent, this system reconciles thousands of transactions in seconds with 100% recall on capital recovery.

## System Architecture

Piping raw transactional CSVs into an LLM is computationally expensive and prone to hallucinations. This project utilizes a highly optimized Two-Tier Architecture:

* **Tier 1: Deterministic Engine (`src/reconciler.py`)**
A fast, rule-based Python engine cross-references the Bank Ledger (net cash) against the Razorpay Settlement Report (gross/fee/tax). It computes mathematical parity based on the legal contract and filters out clean matches, isolating only genuine edge cases.
* **Tier 2: Agentic Diagnostic Layer (`src/agent.py`)**
The remaining exceptions are packaged into a single JSON array and sent to Gemini 3.6-flash via a batched payload. The agent references the merchant contract to classify edge cases (e.g., UPI fee waivers vs. gateway overcharges) and outputs an actionable `IGNORE` or `ESCALATE` recommendation.
* **Tier 3: Interactive Q&A (`src/qna_agent.py`)**
A streaming, natural-language terminal allowing finance operators to interrogate the final audit sheet and query specific transaction anomalies.

## Evaluation Metrics

Tested on a synthetic 30-day batch of 1,412 bank transactions and 56 gateway settlements containing intentionally injected anomalies.

| Metric | Result | Note |
| --- | --- | --- |
| **Capital Recovery Rate** | 100.00% | Caught all ₹4,127.51 of injected revenue leaks. |
| **Recall (Missing Funds)** | 100.00% | Zero false negatives. No leaked capital bypassed the agent. |
| **Precision** | 87.50% | Heavy bias toward safety (1 false positive escalated for manual review). |
| **Inference Time** | < 5 seconds | Achieved via single-payload JSON batching, bypassing rate limits. |

## Quick Start

**1. Set your API Key**

```powershell
$env:GEMINI_API_KEY="your_api_key_here"

```

**2. Run the Full Automated Pipeline**
Execute the deterministic engine, the AI diagnostic agent, the audit generator, and the evaluation harness in one click:

```powershell
python main.py

```

**3. Launch the Finance Q&A Chatbot**
Query your generated audit sheet using natural language:

```powershell
python src/qna_agent.py

```

## Repository Structure

* `/contracts` - Machine-readable legal JSON rules.
* `/data` - Synthetic bank ledgers and ground-truth validation keys.
* `/src` - Core engine, AI agents, and data generators.
* `/tests` - The evaluation harness proving submission metrics.
* `/output` - The final `reconciliation_audit_sheet.csv` generated for finance operators.
