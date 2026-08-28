import pandas as pd
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_contract():
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        return json.load(f)

def run_tier1_reconciliation():
    contract = load_contract()
    
    # 1. Load Data
    ledger = pd.read_csv(ROOT / 'data' / 'ochicken_ledger.csv')
    rzp_report = pd.read_csv(ROOT / 'data' / 'razorpay_settlement_report.csv')
    
    # Filter ledger for actual settlements (ignoring direct UPI/NEFT for now)
    settlements = ledger[ledger['txn_type'].isin(['CARD_TERMINAL_SETTLEMENT', 'RAZORPAY_PAYOUT_BATCH'])].copy()
    settlements = settlements.rename(columns={'txn_id': 'transaction_id', 'deposit_amt': 'bank_net'})
    
    # 2. Outer Merge to find missing and matched records
    recon = pd.merge(settlements, rzp_report, on='transaction_id', how='outer')
    
    # 3. Categorize Exceptions
    exceptions = []
    
    for _, row in recon.iterrows():
        tx_id = row['transaction_id']
        
        # Missing in Gateway (Bank received money, but gateway has no record)
        if pd.isna(row['amount']):
            exceptions.append({'transaction_id': tx_id, 'exception_type': 'MISSING_IN_GATEWAY', 'details': f"Bank net: {row['bank_net']}"})
            continue
            
        # Missing in Bank (Gateway says settled, but bank didn't receive it)
        if pd.isna(row['bank_net']):
            exceptions.append({'transaction_id': tx_id, 'exception_type': 'MISSING_IN_BANK', 'details': f"Gateway net: {row['rzp_net']}"})
            continue

        gross = row['amount']
        txn_type = row['txn_type']
        bank_net = float(row['bank_net'])
        rzp_net = float(row['rzp_net'])
        rzp_fee = float(row['rzp_fee'])
        
        # Compute expected standard fees (ignoring promo windows/UPI waivers - the AI agent will figure those out later)
        if txn_type == 'CARD_TERMINAL_SETTLEMENT':
            expected_rate = contract['card_terminal_settlement']['mdr_rate_percent'] / 100
        else:
            expected_rate = contract['razorpay_payout_batch']['commission_rate_percent'] / 100
            
        expected_fee = round(gross * expected_rate, 2)
        
        # Flag discrepancies
        if abs(bank_net - rzp_net) > 0.01:
            exceptions.append({'transaction_id': tx_id, 'exception_type': 'NET_MISMATCH', 'details': f"Bank received {bank_net}, Gateway reported {rzp_net}"})
        elif abs(rzp_fee - expected_fee) > 0.01:
            exceptions.append({'transaction_id': tx_id, 'exception_type': 'FEE_VARIANCE', 'details': f"Charged fee {rzp_fee} differs from expected base fee {expected_fee}"})
            
    # 4. Output Exception Report
    output_dir = ROOT / 'output'
    output_dir.mkdir(exist_ok=True)
    pd.DataFrame(exceptions).to_csv(output_dir / 'tier1_exceptions.csv', index=False)
    
    match_rate = ((len(settlements) - len(exceptions)) / len(settlements)) * 100
    print(f"Tier 1 Deterministic Engine Complete.")
    print(f"Total Settlements Analyzed: {len(settlements)}")
    print(f"Exceptions Found: {len(exceptions)}")
    print(f"Match Rate: {match_rate:.2f}%")
    print(f"Report written to output/tier1_exceptions.csv")

if __name__ == "__main__":
    run_tier1_reconciliation()