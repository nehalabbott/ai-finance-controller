# Architectural Design Decisions: O'Chicken AI Finance Controller

## A. Multi-Source Triangulation
Single-source matching fails in production because a bank ledger only records net credited cash—never the underlying gross transaction value or deducted gateway commissions[cite: 1].
* **Source A (Bank Statement):** Ground reality of funds received (`deposit_amt`)[cite: 1].
* **Source B (Gateway Settlement):** Intermediary ledger showing gross capture, gateway fees, and applied GST[cite: 1].
* **Source C (Merchant Contract):** Definitive business rules (e.g., base 1.75% MDR, promo windows at 1.5%, UPI fee waivers, minimum volume thresholds)[cite: 1].

## B. Compute Separation & Cost Optimization
**The Anti-Pattern:** Piping 1,400+ transaction rows directly into an LLM context window is computationally wasteful, slow, and prone to floating-point arithmetic errors[cite: 1].

**My Approach:** Tier 1 processes clean transactions in sub-20 milliseconds via deterministic algebraic validation (Expected Net = Gross - MDR - GST)[cite: 1]. Only ambiguous exceptions are dispatched to Tier 2, reducing LLM token consumption by over 95%[cite: 1]. This strictly enforces the operational rule that an LLM should not execute mathematical operations a calculator can handle deterministically[cite: 1].

## C. Single-Payload Batch Inference
**The Anti-Pattern:** Sequential for-loop API calls introduce severe network round-trip overhead and risk rate-limit exhaustion (HTTP 429)[cite: 1].

**My Approach:** Tier 2 packages all flagged exception records into a unified JSON array payload[cite: 1]. A single batched prompt processes the entire batch concurrently using a unified model provider (`openai/gpt-oss-120b`), dropping diagnostic latency from minutes to sub-5 seconds[cite: 1].

## D. Structured Operational Schema vs. Simple Escalation
**The Anti-Pattern:** Relying on the AI to output unstructured textual advice that requires manual human parsing[cite: 1].

**My Approach:** The AI diagnostic agent is constrained to a strict Pydantic JSON output schema (`root_cause`, `confidence`, `recommended_action`, `human_approval_required`)[cite: 1]. This forces the LLM to act as a structured operational copilot, allowing downstream systems to process dispute tickets or clear false positives systematically[cite: 1].

## E. Secure At-Least-Once Webhook Processing
Webhook gateways in financial operations must withstand replay attacks, duplicate deliveries, and tampered payloads[cite: 1].
* **Signature Verification:** All incoming Razorpay webhooks are cryptographically validated using HMAC-SHA256 against a secure webhook secret header[cite: 1].
* **Idempotency Execution:** To prevent duplicate escalations from Razorpay's at-least-once delivery model, the unique `x-razorpay-event-id` is logged and verified prior to processing any settlement event[cite: 1].

## F. Operator-Centric UX Triage
Finance operators face alert fatigue when presented with massive tabular data dumps[cite: 1]. The dashboard architecture surfaces the single highest-risk capital anomaly directly to the top of the interface, providing an instant operational action queue tailored for a finance operator rather than a raw engineering data view[cite: 1].