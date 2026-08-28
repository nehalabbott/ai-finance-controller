# ai-finance-controller
For reconcillation

# 🐔 O'Chicken AI Finance Controller
### Razorpay AI Buildathon 2026 | Track 04: AI-Powered Autonomous Finance Operations

An enterprise-grade, multi-tiered financial reconciliation and automated capital recovery platform designed to close the finance-ops loop. By combining a deterministic algebraic filter, a batched LLM diagnostic agent, an active webhook gateway, and an interactive Streamlit dashboard, this system reconciles thousands of transactions in seconds with 100% recall on capital recovery.

---

## 🎯 Alignment with Buildathon Problem Statement

| Problem Statement Criteria | How O'Chicken AI Finance Controller Delivers |
| :--- | :--- |
| **Close one finance-ops loop across 50+ records** | Processes **1,412+ ledger transactions** and gateway settlement reports across a 30-day window, running an automated end-to-end loop from raw data ingestion to final audit resolution. |
| **Verification over generation (Why Now)** | Focuses entirely on the 2026 builder consensus—solving the verification bottleneck where manual reconciliation and settlement lead to capital leakage. |
| **Multi-source reconciliation & Settlement Q&A** | Combines cross-source matching (`ochicken_ledger.csv` vs `razorpay_settlement_report.csv`) with an interactive **Streamlit Q&A chatbot** (`src/app.py`) to query ledger data and contract rules in real time. |
| **Throughput, Accuracy & Honest Exception List** | Features an evaluation harness (`tests/eval_harness.py`) tracking 100% recall accuracy and exact capital recovery (₹4,127.51), while maintaining a transparent exception list (`output/reconciliation_audit_sheet.csv`) rather than cherry-picked matches. |

---

## 🏗️ System Architecture

Piping raw transactional CSVs into an LLM is computationally expensive and prone to hallucinations. This project utilizes a highly optimized Multi-Tier Architecture:

* **Tier 1: Deterministic Engine (`src/reconciler.py`)**
  A fast, rule-based Python engine cross-references the Bank Ledger (net cash) against the Razorpay Settlement Report (gross/fee/tax). It computes mathematical parity based on the legal contract and filters out clean matches, isolating only genuine edge cases.
* **Tier 2: Agentic Diagnostic Layer (`src/agent.py`)**
  The remaining exceptions are packaged into a single JSON array and analyzed via batched LLM payloads. The agent references the merchant contract to classify edge cases (e.g., UPI fee waivers vs. gateway overcharges) and outputs an actionable `IGNORE` or `ESCALATE` recommendation without raw LaTeX formatting bugs.
* **Tier 3: Active Webhook Gateway (`src/webhook_receiver.py`)**
  A FastAPI real-time daemon that listens to live gateway callbacks, running Tier 1 checks and triggering Tier 2 diagnostics instantly on incoming settlement events.
* **Tier 4: Interactive Dashboard & Q&A (`src/app.py`)**
  A Streamlit web interface offering visual audit inspection, metric tracking, and a natural language chat assistant to interrogate contract clauses and transaction anomalies.

---

## 📊 Evaluation Metrics

Tested on a synthetic 30-day batch of 1,412 bank transactions and 56 gateway settlements containing intentionally injected anomalies.

| Metric | Result | Note |
| --- | --- | --- |
| **Capital Recovery Rate** | 100.00% | Caught all ₹4,127.51 of injected revenue leaks. |
| **Recall (Missing Funds)** | 100.00% | Zero false negatives. No leaked capital bypassed the agent. |
| **Precision** | 87.50% | Heavy bias toward safety (1 false positive escalated for manual review). |
| **Inference Time** | < 5 seconds | Achieved via single-payload JSON batching, bypassing rate limits. |

---

## 🚀 Quick Start & Installation

**1. Clone the Repository & Install Dependencies**
```powershell
git clone [https://github.com/your-username/ai-finance-controller.git](https://github.com/your-username/ai-finance-controller.git)
cd ai-finance-controller
pip install -r requirements.txt