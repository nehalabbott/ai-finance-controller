## Component Pipeline

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