
# AI Finance Controller (🐔 O'Chicken brand specific)
### Razorpay AI Buildathon 2026 | Track 04: AI-Powered Autonomous Finance Operations

An enterprise-grade, multi-tiered financial reconciliation and automated capital recovery platform designed to close the finance-ops loop. By combining a deterministic algebraic filter, a batched LLM diagnostic agent, a secure active webhook gateway, and an operator-focused Streamlit dashboard, this system reconciles thousands of transactions in seconds with 100% recall on capital recovery.

---

## 🎯 Alignment with Buildathon Problem Statement

| Problem Statement Criteria | How O'Chicken AI Finance Controller Delivers |
| :--- | :--- |
| **Close one finance-ops loop across 50+ records** | Processes **1,412+ ledger transactions** and gateway settlement reports across a 30-day window, running an automated end-to-end loop from raw data ingestion to final audit resolution. |
| **Verification over generation (Why Now)** | Focuses entirely on the 2026 builder consensus—solving the verification bottleneck where manual reconciliation and settlement lead to capital leakage. |
| **Multi-source reconciliation & Settlement Q&A** | Combines cross-source matching (`ochicken_ledger.csv` vs `razorpay_settlement_report.csv`) with a token-optimized **Streamlit Q&A chatbot** to query ledger data and contract rules in real time. |
| **Throughput, Accuracy & Honest Exception List** | Features an evaluation harness tracking 100% recall accuracy and exact capital recovery across independent boundary edge cases, maintaining a transparent exception list rather than cherry-picked matches. |

---

## 🏗️ System Architecture

Piping raw transactional CSVs into an LLM is computationally expensive and prone to hallucinations. This project utilizes a highly optimized Multi-Tier Architecture:

* **Tier 1: Deterministic Engine (`src/reconciler.py`)**
  A fast (sub-20ms), rule-based Python engine cross-references the Bank Ledger (net cash) against the Razorpay Settlement Report (gross/fee/tax). It computes mathematical parity based on the legal contract—including the promotional MDR window, 5-paise rounding tolerances, and the UPI/below-threshold commission exemption—filtering out clean matches and isolating genuine edge cases.
* **Tier 2: Agentic Diagnostic Layer (`src/agent.py`)**
  The remaining exceptions are packaged into a single JSON array and analyzed via batched LLM payloads using the unified **Groq (openai/gpt-oss-120b)** architecture. The agent references the merchant contract to output a strict JSON operational schema (root cause, confidence score, recommended action, and human approval flag).
* **Tier 3: Active Webhook Gateway (`src/webhook_receiver.py`)**
  A FastAPI real-time daemon that listens to live gateway callbacks. It features HMAC-SHA256 signature verification, Razorpay payload adapters, and event-ID idempotency to ensure secure, at-least-once processing for enterprise finance ops.
* **Tier 4: Interactive Dashboard & Q&A (`src/app.py`)**
  A Streamlit web interface centered on a Finance Operator Action Queue for highest-risk anomaly triage, metric tracking, and a natural language chat assistant to interrogate contract clauses.

---

## 📊 Evaluation Metrics

Tested on a synthetic batch of bank transactions and gateway settlements containing intentionally injected anomalies. The ground-truth generation pipeline explicitly targets edge cases (₹999.99 boundaries, exact ₹1,000 thresholds, and strict promo start/end dates) to ensure independent evaluation rigor.

| Metric | Result | Note |
| --- | --- | --- |
| **Capital Recovery Rate** | 100.00% | Successfully flagged all injected revenue leaks across the synthetic batch. |
| **Recall (Missing Funds)** | 100.00% | Zero false negatives, verified against the full ground-truth set to ensure no dropped gateway records were silently cleared. |

**Note on the LLM tier:** without a `GROQ_API_KEY` set, Tier 2 uses a deterministic fallback (confidence = 0.0, human approval required = True) rather than a live LLM diagnosis. The evaluation harness safely prints an explicit warning when the deterministic fallback is used to prevent misrepresenting deterministic logic as AI performance.

---

## 🚀 Quick Start & Installation

**1. Clone the Repository & Install Dependencies**
```powershell
git clone [https://github.com/your-username/ai-finance-controller.git](https://github.com/your-username/ai-finance-controller.git)
cd ai-finance-controller
pip install -r requirements.txt
--
## 2. Set Your API Credentials

The project requires a **Groq API key** for the unified AI diagnostic agent and a **Webhook Secret** for secure Razorpay event processing.

### PowerShell

```powershell
$env:GROQ_API_KEY="your_groq_api_key_here"
$env:RAZORPAY_WEBHOOK_SECRET="your_webhook_secret_here"
--

## 3. Run the Full Automated Pipeline

Execute the deterministic reconciliation engine, AI diagnostic agent, audit generator, and evaluation harness in one command:

```powershell
python main.py
```

The pipeline performs the following steps:

1. Processes the input bank and gateway data.
2. Runs the deterministic reconciliation engine.
3. Uses the AI diagnostic agent for unresolved discrepancies.
4. Generates the reconciliation audit.
5. Runs the evaluation harness against the ground-truth data.
6. Produces the final audit output in `/output`.

The generated audit file is:

```text
output/reconciliation_audit_sheet.csv
```

---

## 4. Launch the Interactive Streamlit Dashboard

Launch the visual dashboard to inspect reconciliation results, audit tables, and interact with the Q&A assistant:

```powershell
python -m streamlit run src/app.py
```

Once started, Streamlit will provide a local URL, typically:

```text
http://localhost:8501
```

Open the URL in your browser to access the dashboard.

---

## 5. Start the Real-Time FastAPI Webhook Daemon

Start the FastAPI webhook gateway locally on port `8000`:

```powershell
python -m uvicorn src.webhook_receiver:app --reload --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI's interactive API documentation can be accessed at:

```text
http://localhost:8000/docs
```

The `--reload` flag automatically restarts the server whenever source files are modified.

---

## 6. Run Using Docker Compose

To build and start the containerized services in a single command:

```powershell
docker-compose up --build
```

To stop the services:

```powershell
docker-compose down
```

Make sure **Docker Desktop** is installed and running before executing the command.

---

## 📁 Repository Structure

```text
.
├── contracts/
│   └── ochicken_contract.json
│       └── Machine-readable legal fee rules
│
├── data/
│   ├── Synthetic bank ledgers
│   ├── Gateway reports
│   └── Ground-truth validation data
│
├── src/
│   ├── Core reconciliation engine
│   ├── Tier 2 LLM batch agents
│   ├── FastAPI webhook daemon
│   ├── Automated alerts
│   └── Streamlit frontend
│
├── tests/
│   └── eval_harness.py
│       └── Automated evaluation harness
│
├── output/
│   └── reconciliation_audit_sheet.csv
│       └── Final audit output for finance operators
│
├── main.py
├── Dockerfile
└── docker-compose.yml
```

## 🚀 Quick Start

For a complete local setup, run the following commands in order:

```powershell
# 1. Set your API key
$env:GROQ_API_KEY="your_api_key_here"

# 2. Run the complete automated pipeline
python main.py

# 3. Launch the Streamlit dashboard
python -m streamlit run src/app.py

# 4. In a separate terminal, start the webhook daemon
python -m uvicorn src.webhook_receiver:app --reload --port 8000
```

Alternatively, run the entire containerized application using:

```powershell
docker-compose up --build
```
