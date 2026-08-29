import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def evaluate():
    ground_truth = pd.read_csv(ROOT / "data" / "ochicken_ground_truth.csv")
    exceptions = pd.read_csv(ROOT / "output" / "tier1_exceptions.csv")
    resolutions = pd.read_csv(ROOT / "output" / "agent_resolutions.csv")

    # IMPORTANT: We evaluate against the FULL ground truth, not just the subset
    # that Tier 1 happened to flag. A previous version of this harness only
    # merged ground_truth with resolutions (which only contains Tier-1-flagged
    # rows), which meant any transaction Tier 1 silently cleared - even if it
    # had a real injected error - was invisible to the eval and could never
    # count as a false negative. That structurally inflated recall.
    #
    # Full pipeline stages for every ground-truth row:
    #   1. Was it flagged as an exception by Tier 1?      (tier1_exceptions.csv)
    #   2. If flagged, what did Tier 2 recommend?          (agent_resolutions.csv)
    #   3. If never flagged, it was implicitly cleared -> treated as NOT escalated.
    merged = pd.merge(
        ground_truth,
        exceptions[["transaction_id", "exception_type"]],
        left_on="txn_id",
        right_on="transaction_id",
        how="left"
    )
    merged = pd.merge(
        merged,
        resolutions[["transaction_id", "action", "reasoning"]],
        on="transaction_id",
        how="left"
    )

    tp, fp, tn, fn = 0, 0, 0, 0
    total_at_risk = abs(ground_truth["discrepancy_amount"]).sum()
    recovered_amount = 0.0
    fallback_used_count = 0
    tier1_miss_count = 0  # real errors that Tier 1 never even flagged

    for _, row in merged.iterrows():
        has_real_error = pd.notna(row["injected_error_type"]) and str(row["injected_error_type"]).strip() != ""
        was_flagged = pd.notna(row["exception_type"])
        agent_escalated = was_flagged and row["action"] == "ESCALATE"
        disc_amt = abs(row["discrepancy_amount"])

        if pd.notna(row.get("reasoning")) and "Fallback rule applied" in str(row["reasoning"]):
            fallback_used_count += 1

        if has_real_error and not was_flagged:
            tier1_miss_count += 1

        if has_real_error and agent_escalated:
            tp += 1
            recovered_amount += disc_amt
        elif not has_real_error and agent_escalated:
            fp += 1
        elif not has_real_error and not agent_escalated:
            tn += 1
        elif has_real_error and not agent_escalated:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    recovery_rate = (recovered_amount / total_at_risk) * 100 if total_at_risk > 0 else 0.0

    print("=" * 55)
    print("        RAZORPAY RECONCILIATION EVAL HARNESS         ")
    print("=" * 55)
    print(f"Total Ground-Truth Transactions Evaluated: {len(merged)}")
    print(f"True Positives (TP):         {tp}")
    print(f"False Positives (FP):        {fp}")
    print(f"True Negatives (TN):         {tn}")
    print(f"False Negatives (FN):        {fn}")
    print(f"  of which missed by Tier 1 entirely: {tier1_miss_count}")
    print("-" * 55)
    print(f"Precision:                   {precision:.2%}")
    print(f"Recall:                      {recall:.2%}")
    print(f"F1 Score:                    {f1:.2%}")
    print("-" * 55)
    print(f"Total Capital at Risk:       ₹{total_at_risk:,.2f}")
    print(f"Capital Recovered / Flagged: ₹{recovered_amount:,.2f}")
    print(f"Capital Recovery Rate:       {recovery_rate:.2f}%")
    print("-" * 55)
    if fallback_used_count > 0:
        print(f"⚠️  WARNING: {fallback_used_count} record(s) used the deterministic")
        print(f"    fallback instead of a live LLM call. The precision/recall")
        print(f"    numbers above reflect fallback behavior, not the LLM agent.")
    print("=" * 55)

if __name__ == "__main__":
    evaluate()
