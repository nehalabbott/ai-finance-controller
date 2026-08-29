## Summary

Post-submission audit found the pipeline crashed when run fresh, the reported
87.5%/100% precision/recall numbers weren't reproducible with the checked-in
code, and a committed file exposed live API keys. This PR fixes all of it.

## 🔒 Security
- **Removed `api.env`**, which had a live Groq key and a Gemini key committed
  in plaintext. Replaced with `api.env.example` as a safe template.
- Keys have been revoked and rotated. Anyone who cloned the repo before this
  commit should not reuse the old keys.
- History was scrubbed with `git-filter-repo` and force-pushed.

## 🐛 Pipeline crashes (previously `python main.py` did not complete)
- `export_audit_sheet.py` referenced `exception_type` without ever merging
  in `tier1_exceptions.csv` → `KeyError`. Now merges Tier 1 + Tier 2 output
  before building the sheet.
- `eval_harness.py` read a `recommended_action` column that doesn't exist —
  `agent.py` outputs `action`. Fixed the column name mismatch.
- Both scripts now run cleanly end-to-end from a fresh clone.

## 📉 Tier 1 was contract-blind (25 of 34 flagged exceptions were false positives)
`reconciler.py` always applied the flat base MDR/commission rate, ignoring:
- the contract's promotional MDR window (2026-07-15 to 2026-07-31)
- the UPI fee-exemption clause
- the commission-waived-below-amount threshold

Fixed by encoding the same rules the synthetic data generator uses. Result:
Tier 1 false positives dropped from 25/34 to 1/8, and it now catches all 7
real injected errors with zero misses on its own, before Tier 2 even runs.

## 📊 Metrics are now honest and reproducible
- `eval_harness.py` previously only scored transactions that Tier 1 already
  flagged, so a real error Tier 1 silently missed could never be counted as
  a false negative — recall was inflated by construction. It now scores
  against the *full* ground truth.
- The checked-in example output showed **every single exception using the
  fallback heuristic**, not a live LLM call, meaning the reported 87.5%
  precision was never actually produced by the LLM the README described.
  Re-running the fixed pipeline reproduces 87.5% precision / 100% recall
  legitimately, driven by the corrected Tier 1 logic, with the harness now
  printing an explicit warning whenever fallback was used instead of a live
  LLM call.
- `alerts.py` and the Streamlit dashboard (`app.py`) had hardcoded metric
  strings (`"₹4,127.51"`, `"100.00%"`) instead of computing them from the
  actual run output. Both now compute live from the audit sheet.

## 🔧 Other bugs fixed
- `agent.py` / `app.py`: fell back to `GEMINI_API_KEY` when initializing the
  **Groq** client, which is an invalid credential for that provider and
  silently forced fallback mode. Now only uses the matching key per client.
- `agent.py`: added a single retry on transient API failures before
  degrading to the fallback heuristic.
- `webhook_receiver.py` (Tier 3): read `contract.get("rules", {})`, a key
  that doesn't exist anywhere in `ochicken_contract.json`, so it always used
  a generic 2%/18% rate regardless of payment method or promo window —
  disagreeing with Tier 1 on the same transaction. Now mirrors Tier 1's
  contract-aware logic.
- `qna_agent.py`: file had two full duplicate definitions of
  `load_knowledge_base()` and `run_finance_chat()` from an incomplete
  refactor; the second (better, token-efficient) version was dead code since
  it was defined after the `if __name__ == "__main__"` guard already ran.
  Consolidated into one version. Also fixed `genai.Client()` raising on
  import with no key set, instead of failing gracefully like the rest of the
  codebase.

## ✅ Verification
Ran `python main.py` from a clean `output/` directory with no API key set
(worst case): completes with exit code 0, produces
`output/reconciliation_audit_sheet.csv`, and `tests/eval_harness.py` reports
87.50% precision / 100.00% recall / 93.33% F1, reproducibly.

## Still open
- These numbers reflect the deterministic fallback (see the `Used LLM`
  column in the audit sheet). Re-running with `GROQ_API_KEY` set will
  exercise the live LLM diagnostic path and may change root-cause labels.