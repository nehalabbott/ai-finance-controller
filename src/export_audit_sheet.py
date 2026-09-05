import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate_audit_spreadsheet():
    # 1. Load data sources
    ledger = pd.read_csv(ROOT / "data" / "ochicken_ledger.csv")
    truth = pd.read_csv(ROOT / "data" / "ochicken_ground_truth.csv")
    exceptions = pd.read_csv(ROOT / "output" / "tier1_exceptions.csv")
    resolutions = pd.read_csv(ROOT / "output" / "agent_resolutions.csv")

    # 2. Merge Tier 1 exception metadata with Tier 2 agent diagnoses
    combined = pd.merge(
        exceptions,
        resolutions,
        on="transaction_id",
        how="left"
    )

    # 3. Merge ledger details
    merged = pd.merge(
        ledger[["txn_id", "value_date", "narration", "deposit_amt"]],
        combined,
        left_on="txn_id",
        right_on="transaction_id",
        how="inner"
    )

    # 4. Merge ground truth validation data
    merged = pd.merge(
        merged,
        truth[["txn_id", "gross_amount", "correct_net", "discrepancy_amount", "injected_error_type"]],
        on="txn_id",
        how="left"
    )

    # 5. Select and format audit sheet columns based on the strict agent schema
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
        "Agent Confidence": merged["confidence"],
        "Human Approval Needed": merged["human_approval_required"],
        # Check confidence score rather than legacy 'reasoning' strings to detect fallbacks
        "Used LLM": merged["confidence"] > 0.0, 
        "Actual Planted Error": merged["injected_error_type"].fillna("None (Valid Variance)")
    })

    # 6. Sort by items requiring human approval and highest monetary discrepancy
    audit_df.sort_values(
        by=["Human Approval Needed", "Discrepancy (₹)"],
        ascending=[False, False],
        inplace=True
    )

    output_path = ROOT / "output" / "reconciliation_audit_sheet.csv"
    audit_df.to_csv(output_path, index=False)

    print(f"Spreadsheet generated: {output_path}")
    print(f"Total flagged transactions: {len(audit_df)}")
    
    # Safely sum escalation actions using the new schema naming
    escalations = audit_df['Agent Recommended Action'].astype(str).str.contains('ESCALATE', case=False).sum()
    ignores = audit_df['Agent Recommended Action'].astype(str).str.contains('IGNORE', case=False).sum()
    
    print(f"Items flagged for recovery (ESCALATE): {escalations}")
    print(f"Legitimate variances cleared (IGNORE): {ignores}")

if __name__ == "__main__":
    generate_audit_spreadsheet()