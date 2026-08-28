import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate_audit_spreadsheet():
    # 1. Load data sources
    ledger = pd.read_csv(ROOT / "data" / "ochicken_ledger.csv")
    truth = pd.read_csv(ROOT / "data" / "ochicken_ground_truth.csv")
    resolutions = pd.read_csv(ROOT / "output" / "agent_resolutions.csv")

    # 2. Merge ledger details with agent diagnoses
    merged = pd.merge(
        ledger[["txn_id", "value_date", "narration", "deposit_amt"]],
        resolutions,
        left_on="txn_id",
        right_on="transaction_id",
        how="inner"
    )

    # 3. Merge ground truth validation data
    merged = pd.merge(
        merged,
        truth[["txn_id", "gross_amount", "correct_net", "discrepancy_amount", "injected_error_type"]],
        on="txn_id",
        how="left"
    )

    # 4. Select and format audit sheet columns
    audit_df = pd.DataFrame({
        "Transaction ID": merged["txn_id"],
        "Date": merged["value_date"],
        "Narration": merged["narration"],
        "Gross Amount (₹)": merged["gross_amount"],
        "Stated Bank Net (₹)": merged["deposit_amt"],
        "Correct Expected Net (₹)": merged["correct_net"],
        "Discrepancy (₹)": merged["discrepancy_amount"],
        "Detection Rule": merged["exception_type"],
        "Agent Diagnosis": merged["root_cause"],
        "Agent Recommended Action": merged["recommended_action"],
        "Agent Reasoning / Cause": merged["reasoning"],
        "Actual Planted Error": merged["injected_error_type"].fillna("None (Valid Variance)")
    })

    # 5. Sort by discrepancies requiring escalation first
    audit_df.sort_values(
        by=["Agent Recommended Action", "Discrepancy (₹)"],
        ascending=[True, False],
        inplace=True
    )

    output_path = ROOT / "output" / "reconciliation_audit_sheet.csv"
    audit_df.to_csv(output_path, index=False)

    print(f"Spreadsheet generated: {output_path}")
    print(f"Total flagged transactions: {len(audit_df)}")
    print(f"Items flagged for recovery (ESCALATE): {(audit_df['Agent Recommended Action'] == 'ESCALATE').sum()}")
    print(f"Legitimate variances cleared (IGNORE): {(audit_df['Agent Recommended Action'] == 'IGNORE').sum()}")

if __name__ == "__main__":
    generate_audit_spreadsheet()