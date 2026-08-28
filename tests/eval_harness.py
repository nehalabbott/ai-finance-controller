import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def evaluate():
    ground_truth = pd.read_csv(ROOT / "data" / "ochicken_ground_truth.csv")
    resolutions = pd.read_csv(ROOT / "output" / "agent_resolutions.csv")

    # Merge on transaction ID
    merged = pd.merge(
        ground_truth,
        resolutions,
        left_on="txn_id",
        right_on="transaction_id",
        how="inner"
    )

    tp, fp, tn, fn = 0, 0, 0, 0
    total_at_risk = abs(ground_truth["discrepancy_amount"]).sum()
    recovered_amount = 0.0

    for _, row in merged.iterrows():
        has_real_error = pd.notna(row["injected_error_type"]) and str(row["injected_error_type"]).strip() != ""
        agent_escalated = row["recommended_action"] == "ESCALATE"
        disc_amt = abs(row["discrepancy_amount"])

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
    print(f"Total Exceptions Evaluated:  {len(merged)}")
    print(f"True Positives (TP):         {tp}")
    print(f"False Positives (FP):        {fp}")
    print(f"True Negatives (TN):         {tn}")
    print(f"False Negatives (FN):        {fn}")
    print("-" * 55)
    print(f"Precision:                   {precision:.2%}")
    print(f"Recall:                      {recall:.2%}")
    print(f"F1 Score:                    {f1:.2%}")
    print("-" * 55)
    print(f"Total Capital at Risk:       ₹{total_at_risk:,.2f}")
    print(f"Capital Recovered / Flagged: ₹{recovered_amount:,.2f}")
    print(f"Capital Recovery Rate:       {recovery_rate:.2f}%")
    print("=" * 55)

if __name__ == "__main__":
    evaluate()