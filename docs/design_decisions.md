A. Multi-Source Triangulation
Single-source matching fails in production because a bank ledger only records net credited cash—never the underlying gross transaction value or deducted gateway commissions.

Source A (Bank Statement): Ground reality of funds received (deposit_amt).

Source B (Gateway Settlement): Intermediary ledger showing gross capture, gateway fees, and applied GST.

Source C (Merchant Contract): Definitive business rules (e.g., base 2.0% MDR, promo windows at 1.5%, UPI fee waivers, minimum volume thresholds).

B. Compute Separation & Cost Optimization
The Anti-Pattern: Piping 1,400+ transaction rows directly into an LLM context window is computationally wasteful, slow, and prone to floating-point arithmetic errors.

Our Approach: Tier 1 processes clean transactions in milliseconds via vector operations. Only the remaining ambiguous exceptions are dispatched to Tier 2, reducing LLM token consumption by over 95%.

C. Single-Payload Batch Inference
Sequential for-loop API calls introduce severe network round-trip overhead and risk rate-limit exhaustion (HTTP 429).

Tier 2 packages all flagged exception records into a unified JSON array payload. A single batched prompt processes the entire batch concurrently, dropping diagnostic latency from minutes to sub-5 seconds.
