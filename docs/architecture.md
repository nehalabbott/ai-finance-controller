# Architecture & Design Specifications: O'Chicken AI Finance Controller

## 1. System Overview

The **O'Chicken AI Finance Controller** is an automated multi-source reconciliation and exception-resolution engine. It reconciles high-volume bank settlement statements against payment gateway payout reports and legal fee contracts.

Rather than treating LLMs as brute-force processors for structured tabular math, the system employs a **Two-Tier Hybrid Architecture**:
* **Tier 1 (Deterministic Engine):** Fast, high-throughput algebraic matching and primary-key alignment.
* **Tier 2 (Agentic Diagnostic Layer):** Targeted, context-aware LLM reasoning strictly applied to flagged variances and edge cases.

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
            |       Tier 1: Deterministic Engine     |
            |       (Algebraic Recon & Outer Join)  |
            +-------------------+-------------------+
                                |
             +------------------+------------------+
             |                                     |
       [ Clean Matches ]                  [ Flagged Exceptions ]
       (Auto-Reconciled)                  (34 Anomaly Records)
                                                   |
                                                   v
                                  +---------------------------------+
                                  |   Tier 2: Agentic Diagnostics   |
                                  |   (Gemini Batch Reasoning)      |
                                  +----------------+----------------+
                                                   |
                        +--------------------------+--------------------------+
                        |                                                     |
                        v                                                     v
          +---------------------------+                         +---------------------------+
          | reconciliation_audit.csv  |                         |    tests/eval_harness.py  |
          | (Actionable Finance Ops)  |                         | (Precision, Recall, ₹ ROI)|
          +---------------------------+                         +---------------------------+