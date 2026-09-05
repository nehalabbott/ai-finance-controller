import pandas as pd
import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMO_START = date(2026, 7, 15)
PROMO_END = date(2026, 7, 31)
PROMO_MDR_RATE = 1.50 / 100

def load_contract():
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        return json.load(f)

def parse_txn_date(date_str):
    """Robustly parses date strings across multiple common formats."""
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    for fmt in ('%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None

def is_upi_routed(narration):
    """Broadened matching for UPI batch narrations."""
    narration_clean = str(narration).upper().replace("_", "-").replace(" ", "")
    return 'UPI-BATCH' in narration_clean or 'UPIBATCH' in narration_clean

def run_tier1_reconciliation():
    contract = load_contract()
    
    # 1. Load Data
    ledger = pd.read_csv(ROOT / 'data' / 'ochicken_ledger.csv')
    rzp_report = pd.read_csv(ROOT / 'data' / 'razorpay_settlement_report.csv')
    
    # Filter ledger for settlement records
    settlements = ledger[ledger['txn_type'].isin(['CARD_TERMINAL_SETTLEMENT', 'RAZORPAY_PAYOUT_BATCH'])].copy()
    settlements = settlements.rename(columns={'txn_id': 'transaction_id', 'deposit_amt': 'bank_net', 'narration': 'bank_narration'})
    
    exceptions = []
    
    # 2. Duplicate Detection (Independent Edge Case Handling)
    duplicate_ledger = settlements[settlements.duplicated(subset=['transaction_id'], keep=False)]
    for tx_id in duplicate_ledger['transaction_id'].unique():
        exceptions.append({
            'transaction_id': tx_id,
            'exception_type': 'DUPLICATE_IN_LEDGER',
            'details': 'Transaction ID appears multiple times in bank ledger'
        })
        
    duplicate_rzp = rzp_report[rzp_report.duplicated(subset=['transaction_id'], keep=False)]
    for tx_id in duplicate_rzp['transaction_id'].unique():
        exceptions.append({
            'transaction_id': tx_id,
            'exception_type': 'DUPLICATE_IN_GATEWAY',
            'details': 'Transaction ID appears multiple times in gateway settlement report'
        })

    # Deduplicate for outer join processing
    clean_settlements = settlements.drop_duplicates(subset=['transaction_id'], keep='first')
    clean_rzp = rzp_report.drop_duplicates(subset=['transaction_id'], keep='first')
    
    # 3. Outer Merge
    recon = pd.merge(clean_settlements, clean_rzp, on='transaction_id', how='outer')
    
    card_rules = contract.get('card_terminal_settlement', {})
    payout_rules = contract.get('razorpay_payout_batch', {})
    
    # 4. Categorize Discrepancies
    for _, row in recon.iterrows():
        tx_id = row['transaction_id']
        
        # Missing in Gateway
        if pd.isna(row.get('amount')):
            exceptions.append({
                'transaction_id': tx_id,
                'exception_type': 'MISSING_IN_GATEWAY',
                'details': f"Bank net: {row.get('bank_net', 0.0)}"
            })
            continue
            
        # Missing in Bank
        if pd.isna(row.get('bank_net')):
            exceptions.append({
                'transaction_id': tx_id,
                'exception_type': 'MISSING_IN_BANK',
                'details': f"Gateway net: {row.get('rzp_net', 0.0)}"
            })
            continue

        gross = float(row['amount'])
        txn_type = row.get('txn_type')
        bank_net = float(row['bank_net'])
        rzp_net = float(row.get('rzp_net', 0.0))
        rzp_fee = float(row.get('rzp_fee', 0.0))
        rzp_tax = float(row.get('rzp_tax', 0.0))

        # Expected fee and GST computations
        if txn_type == 'CARD_TERMINAL_SETTLEMENT':
            txn_date = parse_txn_date(row.get('value_date'))
            if txn_date and PROMO_START <= txn_date <= PROMO_END:
                expected_rate = PROMO_MDR_RATE
            else:
                expected_rate = card_rules.get('mdr_rate_percent', 1.75) / 100.0
                
            expected_fee = round(gross * expected_rate, 2)
            expected_tax = round(expected_fee * (card_rules.get('gst_on_mdr_percent', 18.0) / 100.0), 2)
        else:
            waived_below = payout_rules.get('commission_waived_below_amount', 1000.0)
            if is_upi_routed(row.get('bank_narration', '')) or gross < waived_below:
                expected_fee = 0.0
                expected_tax = 0.0
            else:
                expected_rate = payout_rules.get('commission_rate_percent', 2.0) / 100.0
                expected_fee = round(gross * expected_rate, 2)
                expected_tax = round(expected_fee * (payout_rules.get('gst_on_commission_percent', 18.0) / 100.0), 2)

        expected_net = round(gross - expected_fee - expected_tax, 2)

        # 5. Variance Checks with 5-paise tolerance for rounding
        if abs(bank_net - rzp_net) > 0.05:
            exceptions.append({
                'transaction_id': tx_id,
                'exception_type': 'NET_MISMATCH',
                'details': f"Bank received {bank_net}, Gateway reported {rzp_net}"
            })
        elif abs(bank_net - expected_net) > 0.05:
            exceptions.append({
                'transaction_id': tx_id,
                'exception_type': 'CONTRACT_VARIANCE',
                'details': f"Bank received {bank_net}, but contract terms dictate {expected_net}"
            })
        elif abs(rzp_fee - expected_fee) > 0.05:
            exceptions.append({
                'transaction_id': tx_id,
                'exception_type': 'FEE_VARIANCE',
                'details': f"Charged fee {rzp_fee} differs from expected fee {expected_fee}"
            })
        elif abs(rzp_tax - expected_tax) > 0.05:
            exceptions.append({
                'transaction_id': tx_id,
                'exception_type': 'TAX_VARIANCE',
                'details': f"Deducted tax {rzp_tax} differs from expected GST {expected_tax}"
            })
            
    # 6. Save Audit File
    output_dir = ROOT / 'output'
    output_dir.mkdir(exist_ok=True)
    pd.DataFrame(exceptions).to_csv(output_dir / 'tier1_exceptions.csv', index=False)
    
    match_rate = ((len(settlements) - len(exceptions)) / len(settlements)) * 100 if len(settlements) else 0
    print(f"Tier 1 Deterministic Engine Complete.")
    print(f"Total Settlements Analyzed: {len(settlements)}")
    print(f"Exceptions Found: {len(exceptions)}")
    print(f"Match Rate: {match_rate:.2f}%")
    print(f"Report written to output/tier1_exceptions.csv")

if __name__ == "__main__":
    run_tier1_reconciliation()