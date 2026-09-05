# Architecture & Design Specifications: O'Chicken AI Finance Controller

## 1. System Overview

The **O'Chicken AI Finance Controller** is an automated multi-source reconciliation and exception-resolution engine. It reconciles high-volume bank settlement statements against payment gateway payout reports and legal fee contracts.

Rather than treating LLMs as brute-force processors for structured tabular math, the system employs a **Multi-Tier Hybrid Architecture**:
* **Tier 1 (Deterministic Engine):** Sub-20ms algebraic verification, GST parity, duplicate detection, and contract-boundary matching.
* **Tier 2 (Agentic Diagnostic Layer):** Batched Groq inference (`openai/gpt-oss-120b`) enforcing a structured operational schema (`root_cause`, `confidence`, `recommended_action`, `human_approval_required`).
* **Tier 3 (Real-Time Webhook Gateway):** FastAPI endpoint with HMAC-SHA256 signature verification, event-ID deduplication (idempotency), and a Razorpay payload adapter.
* **Tier 4 (Operator Hub & Settlement Q&A):** Streamlit interface featuring a prioritized highest-risk action queue and natural language contract exploration.

```text
                  +--------------------------+
                  |  ochicken_contract.json  |
                  +-------------+------------+
                                |
[ Bank Statement CSV ]          |          [ Gateway Settlement CSV ]
(1,400+ Raw Transactions)       |          (Gross, Fees, Tax, Net)
          \                     |                     /
           \                    v                    /
            +---------------------------------------+
            |      Tier 1: Deterministic Engine     |
            |   (Algebraic Recon, GST & Duplicates) |
            +-------------------+-------------------+
                                |
             +------------------+------------------+
             |                                     |
       [ Clean Matches ]                  [ Flagged Exceptions ]
       (Auto-Reconciled)                  (Isolate Discrepancies)
                                                   |
                                                   v
                                  +---------------------------------+
                                  |   Tier 2: Agentic Diagnostics   |
                                  |   (Groq / GPT-OSS 120B Batch)   |
                                  +----------------+----------------+
                                                   |
                        +--------------------------+--------------------------+
                        |                          |                          |
                        v                          v                          v
          +---------------------------+ +---------------------+ +---------------------------+
          | reconciliation_audit_     | |  src/alerts.py      | |    tests/eval_harness.py  |
          | sheet.csv                 | |  (Operations Triage)| | (Precision, Recall, ROI)  |
          +-------------+-------------+ +---------------------+ +---------------------------+
                        |
                        v
          +---------------------------+
          |  Tier 4: Streamlit App    |
          |  (Action Queue & Q&A)     |
          +---------------------------+

-----------------------------------------------------------------------------------------------
[ Live Gateway Callbacks ] ---> [ Tier 3: FastAPI Webhook ] ---> [ HMAC-SHA256 / Idempotency ]