# Architecture & Design Specifications: O'Chicken AI Finance Controller

## 1. System Overview

The **O'Chicken AI Finance Controller** is an automated multi-source reconciliation and exception-resolution engine. It reconciles high-volume bank settlement statements against payment gateway payout reports and legal fee contracts.

Rather than treating LLMs as brute-force processors for structured tabular math, the system employs a **Two-Tier Hybrid Architecture**:
* **Tier 1 (Deterministic Engine):** Fast, high-throughput algebraic matching and primary-key alignment.
* **Tier 2 (Agentic Diagnostic Layer):** Targeted, context-aware LLM reasoning strictly applied to flagged variances and edge cases.
+--------------------------+
              | ochicken_contract.json   |
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

## 2. Core Design Decisions

### A. Multi-Source Triangulation
Single-source matching fails in production because a bank ledger only records net credited cash—never the underlying gross transaction value or deducted gateway commissions.
* **Source A (Bank Statement):** Ground reality of funds received (`deposit_amt`).
* **Source B (Gateway Settlement):** Intermediary ledger showing gross capture, gateway fees, and applied GST.
* **Source C (Merchant Contract):** Definitive business rules (e.g., base 2.0% MDR, promo windows at 1.5%, UPI fee waivers, minimum volume thresholds).

### B. Compute Separation & Cost Optimization
* **The Anti-Pattern:** Piping 1,400+ transaction rows directly into an LLM context window is computationally wasteful, slow, and prone to floating-point arithmetic errors.
* **Our Approach:** Tier 1 processes clean transactions in milliseconds via vector operations. Only the remaining ambiguous exceptions are dispatched to Tier 2, reducing LLM token consumption by over 95%.

### C. Single-Payload Batch Inference
* Sequential `for`-loop API calls introduce severe network round-trip overhead and risk rate-limit exhaustion (HTTP 429).
* Tier 2 packages all flagged exception records into a unified JSON array payload. A single batched prompt processes the entire batch concurrently, dropping diagnostic latency from minutes to sub-5 seconds.

---

## 3. Component Pipeline

### `src/generate_data.py`
Simulates a representative 30-day settlement cycle (1,400+ ledger entries) featuring realistic banking patterns: card terminal deposits, batch payout batches, high-frequency direct UPI credits, and NEFT vendor debits. Injects realistic edge cases:
* Contractual promotional rate switches.
* GST base miscalculations (gross vs fee base).
* Accidental double deductions.
* Commission charged on fee-exempt UPI batches.
* Gateway dropped records (missing settlement entries).

### `contracts/ochicken_contract.json`
Machine-readable configuration containing legal fee clauses:
* `card_terminal_settlement`: Standard MDR (2.0%) + GST (18%).
* `promotional_clause`: 1.5% MDR between July 15, 2026 and July 31, 2026.
* `razorpay_payout_batch`: 2.0% commission; 0% commission on UPI routes and transactions below ₹1,000.

### `src/reconciler.py` (Tier 1)
Performs deterministic outer joins across data sources. Evaluates mathematical parity:
$$\text{Expected Net} = \text{Gross} - \text{MDR} - \text{GST}$$
Flags records deviating from base formulas into `output/tier1_exceptions.csv`.

### `src/agent.py` (Tier 2)
Ingests exception rows alongside contract constraints. Employs Gemini to classify root causes:
* `UPI_WAIVER` / `PROMO_RATE` $\rightarrow$ Valid variances; action: `IGNORE`.
* `GATEWAY_OVERCHARGE` / `GHOST_TXN` $\rightarrow$ Capital leaks; action: `ESCALATE`.

### `src/export_audit_sheet.py`
Synthesizes inputs into `output/reconciliation_audit_sheet.csv`, providing human-readable explanations, detected discrepancies, and actionable recovery tags.

### `tests/eval_harness.py`
Compares agent decisions against hidden ground-truth labels (`ochicken_ground_truth.csv`) to compute objective metrics:
* Precision, Recall, and F1 Score.
* Total Capital at Risk vs Actual Capital Recovered.

---

## 4. Failure Modes & Engineering Resolutions

| Failure Encountered | Root Cause | Engineering Resolution |
| :--- | :--- | :--- |
| **HTTP 404 / Deprecated Model** | Legacy endpoints sunset in environment updates. | Migrated to the modern `google-genai` SDK targeting current model endpoints. |
| **API Latency & Rate Limits** | Sequential row-by-row API querying caused long delays and rate-limit drops. | Re-architected ingestion to execute as a single batched JSON array request. |
| **Schema Inconsistency** | Unstructured text output complicates programmatic reconciliation. | Enforced native JSON schema validation (`response_mime_type="application/json"`). |