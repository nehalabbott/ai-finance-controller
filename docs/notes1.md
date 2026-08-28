# Step 1 — Synthetic Data Generation

## What this does
Generates one month (July 2026) of O'Chicken's bank settlement ledger —
statistically shaped to match the real statement pattern the merchant shared
(transaction-type mix, daily volume, rough amount ranges), but every
individual number is freshly randomized. No real, identifiable data is used
anywhere in this repo.

## Files produced
- `data/ochicken_ledger.csv` — **the input.** This is what a human reconciler
  (or our system) actually sees: date, transaction type, narration,
  withdrawal/deposit amount, running closing balance. 1,412 transactions
  across 30 days.
- `data/ochicken_ground_truth.csv` — **hidden answer key**, used only by the
  evaluation harness later, never by the reconciliation engine itself. Contains
  the correct fee/GST/net for every fee-bearing settlement, the amount actually
  stated in the ledger, the discrepancy, and (if one was planted) which error
  type was injected.

## Transaction types modeled
| Type | Frequency | Fee-bearing? |
|---|---|---|
| `CARD_TERMINAL_SETTLEMENT` | 1/day | Yes — MDR + GST per contract |
| `RAZORPAY_PAYOUT_BATCH` | 0-2/day | Yes, unless UPI-routed (fee-exempt) or under ₹100 |
| `UPI_DIRECT_CREDIT` | 25-50/day | No — direct UPI collections, zero-MDR mandate |
| `NEFT_VENDOR_DEBIT` | 1-4/day + bulk supplier days | No — balance-only |
| `MDR_RECOVERY_CHARGE` | ~0.85/day | No fee logic, flat periodic charge |

## Ground truth / ambiguity built in (this is what makes evaluation honest)
The fee contract (`contracts/ochicken_contract.json`) is deliberately not a
single flat rule:
- A **promotional MDR rate** (1.50% instead of 1.80%) applies only between
  2026-07-15 and 2026-07-31 — tests whether the reconciliation logic actually
  reads the contract's date-bound clause rather than applying one fixed rate.
- **UPI-routed Razorpay settlements are commission-free**, but card/wallet-routed
  ones aren't — same underlying transaction type, different correct answer,
  depending on a narration-level detail.
- Payouts under ₹100 have commission waived entirely.

## Errors injected (~15% of fee-bearing settlements)
Each has a known, labeled ground truth so precision/recall is measurable, not
asserted:
- `wrong_mdr_rate` — promo vs. standard rate mixed up
- `gst_on_gross` — GST computed on the wrong base
- `fee_double_charged` — MDR/commission subtracted twice
- `fee_omitted` — fee not deducted at all
- `commission_on_upi` — commission wrongly charged on a fee-exempt UPI settlement

## Sanity checks run
- Closing balance stays positive and realistic throughout the month
  (₹1.2M → ~₹830K, never dips below ~₹679K) — mirrors the real statement's
  behavior of a business with steady cash movement, not an exploding or
  negative balance.
- Transaction-type mix matches the real statement's shape (dominated by many
  small UPI credits, one card settlement per day, occasional larger batch
  payouts, periodic vendor debits).

## Next (Step 2)
Build the Tier 1 deterministic reconciliation engine: for every fee-bearing
transaction in `ochicken_ledger.csv`, recompute the correct fee from the
contract (respecting the promo window and UPI-exemption clauses), diff
against the stated amount, and flag discrepancies — **without ever looking at
`ochicken_ground_truth.csv`**, which stays reserved for the eval harness only.