## Summary

This PR addresses the Razorpay Buildathon judge evaluation, hardening the AI Finance Controller from a strong prototype into a production-grade operational system[cite: 1]. It resolves critical security vulnerabilities, standardizes the AI architecture, and completely decouples the evaluation harness for honest metric reporting[cite: 1].

## 🔒 Security & Webhook Hardening
- **Purged Credentials:** Completely removed plaintext API keys from `api.env.example` and scrubbed history to resolve the submission hygiene deduction[cite: 1].
- **Webhook Authentication:** Implemented `X-Razorpay-Signature` validation via HMAC-SHA256 in `webhook_receiver.py`[cite: 1].
- **Idempotency:** Added an in-memory event store checking `x-razorpay-event-id` to prevent duplicate processing of Razorpay's at-least-once delivery webhooks[cite: 1].
- **Payload Adapter:** Added a dedicated transformation layer to convert genuine Razorpay webhook payloads into the internal normalized schema[cite: 1].

## 🤖 AI Architecture Consolidation
- **Unified Provider:** Purged all Gemini SDK remnants from `qna_agent.py`, `webhook_receiver.py`, and `alerts.py` to eliminate mixed-architecture configuration[cite: 1]. The entire repository now strictly uses Groq (`openai/gpt-oss-120b`)[cite: 1].
- **Operational JSON Schema:** Upgraded Tier 2 (`agent.py`) from generating unstructured text to enforcing a strict JSON operational schema: `root_cause`, `confidence`, `recommended_action`, and `human_approval_required`[cite: 1].
- **Contract Grounding:** Tier 2 now explicitly reads and injects the merchant contract clauses into the LLM context to ground its diagnostics[cite: 1].

## 📉 Tier 1 & Evaluation Decoupling
- **GST & Duplicate Checks:** `reconciler.py` now verifies gateway tax deductions (`rzp_tax`) and actively flags duplicate transaction IDs before merging[cite: 1].
- **Rounding Tolerances:** Added a 5-paise rounding tolerance to eliminate false positives caused by floating-point discrepancies[cite: 1].
- **Independent Evaluation:** `generate_data.py` was decoupled to natively track gateway-side errors (preventing the false positive penalty on transaction 2136)[cite: 1].
- **Stress Testing:** Injected explicit boundary edge cases (₹1,000 threshold, ₹999.99, and exact promo start/end dates) directly into the synthetic data to stress-test Tier 1 logic[cite: 1].

## 📊 UX & Operator Dashboard
- **Operator Triage Card:** Updated the Streamlit dashboard (`app.py`) to move away from a raw engineering view by surfacing the single highest-risk anomaly in an actionable Operator Queue[cite: 1].
- **Live Metric Alerts:** `alerts.py` now dynamically queries the audit sheet for the highest-risk transaction and formats a rich Slack/Teams card[cite: 1].

## ✅ Verification
Running `python main.py` followed by `python tests/eval_harness.py` executes cleanly on the newly generated synthetic batch. The webhook daemon (`uvicorn src.webhook_receiver:app`) now rejects unsigned payloads and duplicate event IDs.