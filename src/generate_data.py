import json
import random
import csv
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # reproducible runs

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONTRACT_PATH = ROOT / "contracts" / "ochicken_contract.json"

with open(CONTRACT_PATH) as f:
    CONTRACT = json.load(f)

START_DATE = date(2026, 7, 1)
NUM_DAYS = 30
STARTING_BALANCE = 1_200_000.00

ERROR_INJECTION_RATE = 0.15  # ~15% of fee-bearing settlements get a planted error

ERROR_TYPES = [
    "wrong_mdr_rate",       # used standard rate instead of promo rate (or vice versa)
    "gst_on_gross",         # GST computed on gross amount instead of on the fee
    "fee_double_charged",   # MDR/commission subtracted twice
    "fee_omitted",          # fee not deducted at all
    "commission_on_upi",    # commission wrongly charged on a fee-exempt UPI settlement
]

def round2(x):
    return round(x + 1e-9, 2)

def is_promo_window(txn_date):
    return date(2026, 7, 15) <= txn_date <= date(2026, 7, 31)

def compute_correct_card_settlement(gross, txn_date):
    """Ground-truth fee computation for a card terminal settlement."""
    rate = (CONTRACT["card_terminal_settlement"]["mdr_rate_percent"] / 100
            if not is_promo_window(txn_date)
            else 1.50 / 100)  # promo rate per special_clause
    mdr = round2(gross * rate)
    gst = round2(mdr * CONTRACT["card_terminal_settlement"]["gst_on_mdr_percent"] / 100)
    net = round2(gross - mdr - gst)
    return {"gross": gross, "fee": mdr, "gst": gst, "net": net, "rate_used": rate}

def compute_correct_razorpay_payout(gross, is_upi_routed):
    """Ground-truth fee computation for a Razorpay batch payout."""
    if is_upi_routed:
        # UPI-routed settlements are commission-free per contract clause
        return {"gross": gross, "fee": 0.0, "gst": 0.0, "net": gross, "rate_used": 0.0}
    if gross < CONTRACT["razorpay_payout_batch"]["commission_waived_below_amount"]:
        return {"gross": gross, "fee": 0.0, "gst": 0.0, "net": gross, "rate_used": 0.0}
    rate = CONTRACT["razorpay_payout_batch"]["commission_rate_percent"] / 100
    commission = round2(gross * rate)
    gst = round2(commission * CONTRACT["razorpay_payout_batch"]["gst_on_commission_percent"] / 100)
    net = round2(gross - commission - gst)
    return {"gross": gross, "fee": commission, "gst": gst, "net": net, "rate_used": rate}

def maybe_inject_error(correct, txn_type, is_upi_routed=False):
    """
    With probability ERROR_INJECTION_RATE, returns a (stated_net, error_type)
    tuple where stated_net deviates from correct['net']. Otherwise returns
    (correct['net'], None) i.e. no error, ledger matches ground truth exactly.
    """
    if random.random() > ERROR_INJECTION_RATE:
        return correct["net"], None

    # pick an error type sensible for this transaction type
    if txn_type == "RAZORPAY_PAYOUT_BATCH" and is_upi_routed:
        candidates = ["commission_on_upi"]
    else:
        candidates = ["wrong_mdr_rate", "gst_on_gross", "fee_double_charged", "fee_omitted"]

    err = random.choice(candidates)
    gross, fee, gst = correct["gross"], correct["fee"], correct["gst"]

    if err == "wrong_mdr_rate":
        wrong_rate = 0.020 if correct["rate_used"] != 0.020 else 0.015
        wrong_fee = round2(gross * wrong_rate)
        wrong_gst = round2(wrong_fee * 0.18)
        stated_net = round2(gross - wrong_fee - wrong_gst)
    elif err == "gst_on_gross":
        wrong_gst = round2(gross * 0.18 / 100 * 10)  # deliberately wrong base
        stated_net = round2(gross - fee - wrong_gst)
    elif err == "fee_double_charged":
        stated_net = round2(gross - (2 * fee) - gst)
    elif err == "fee_omitted":
        stated_net = gross
    elif err == "commission_on_upi":
        wrong_fee = round2(gross * 0.02)
        wrong_gst = round2(wrong_fee * 0.18)
        stated_net = round2(gross - wrong_fee - wrong_gst)
    else:
        stated_net = correct["net"]

    return stated_net, err

def generate_rzp_settlement_report(truth_rows):
    """Generates the payment gateway's own settlement report with isolated errors."""
    rzp_rows = []
    for row in truth_rows:
        txn_id, txn_type, gross, fee, gst, net, stated_net, diff, err = row
        
        # Razorpay only reports on its own settlements, not direct UPI or NEFT
        if txn_type in ["CARD_TERMINAL_SETTLEMENT", "RAZORPAY_PAYOUT_BATCH"]:
            rzp_fee = fee
            rzp_gst = gst
            rzp_net = net
            
            rand_val = random.random()
            if rand_val < 0.02:
                # 2% of transactions dropped/missing from settlement report
                continue 
            elif rand_val < 0.07:
                # 5% of transactions get a gateway overcharge error
                rzp_fee = round2(fee * 1.5) 
                rzp_gst = round2(rzp_fee * 0.18)
                rzp_net = round2(gross - rzp_fee - rzp_gst)
                
            rzp_rows.append([txn_id, gross, rzp_fee, rzp_gst, rzp_net])
            
    with open(DATA_DIR / "razorpay_settlement_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id", "amount", "rzp_fee", "rzp_tax", "rzp_net"])
        w.writerows(rzp_rows)
    return len(rzp_rows)

def generate():
    ledger_rows = []
    truth_rows = []
    balance = STARTING_BALANCE
    txn_id_counter = 1000

    for day_offset in range(NUM_DAYS):
        txn_date = START_DATE + timedelta(days=day_offset)
        date_str = txn_date.strftime("%d/%m/%y")

        # 1. Daily card terminal settlement
        gross_card = round2(random.uniform(12000, 32000))
        correct = compute_correct_card_settlement(gross_card, txn_date)
        stated_net, err = maybe_inject_error(correct, "CARD_TERMINAL_SETTLEMENT")
        balance = round2(balance + stated_net)
        txn_id_counter += 1
        narration = f"TERMINAL 1 CARDS SETTL. {date_str}"
        ledger_rows.append([txn_id_counter, date_str, "CARD_TERMINAL_SETTLEMENT", narration, "", stated_net, balance])
        truth_rows.append([txn_id_counter, "CARD_TERMINAL_SETTLEMENT", correct["gross"], correct["fee"], correct["gst"], correct["net"], stated_net, round2(stated_net - correct["net"]), err])

        # 2. Razorpay batch payouts
        for _ in range(random.choice([0, 1, 1, 2])):
            gross_rzp = round2(random.uniform(5000, 90000))
            is_upi = random.random() < 0.35
            correct = compute_correct_razorpay_payout(gross_rzp, is_upi)
            stated_net, err = maybe_inject_error(correct, "RAZORPAY_PAYOUT_BATCH", is_upi)
            balance = round2(balance + stated_net)
            txn_id_counter += 1
            tag = "UPI-BATCH" if is_upi else "CARD-ONLINE-BATCH"
            narration = f"RAZORPAY PAYOUT {tag} {date_str}"
            ledger_rows.append([txn_id_counter, date_str, "RAZORPAY_PAYOUT_BATCH", narration, "", stated_net, balance])
            truth_rows.append([txn_id_counter, "RAZORPAY_PAYOUT_BATCH", correct["gross"], correct["fee"], correct["gst"], correct["net"], stated_net, round2(stated_net - correct["net"]), err])

        # 3. Direct UPI credits
        for _ in range(random.randint(25, 50)):
            amt = round2(random.choice([random.uniform(9, 300), random.uniform(300, 900), random.uniform(900, 2600)]))
            balance = round2(balance + amt)
            txn_id_counter += 1
            narration = f"UPI-{random.randint(10**10,10**11)}-CUSTOMER@OKBANK"
            ledger_rows.append([txn_id_counter, date_str, "UPI_DIRECT_CREDIT", narration, "", amt, balance])

        # 4. NEFT vendor debits
        for _ in range(random.randint(1, 4)):
            amt = round2(random.uniform(300, 20000))
            balance = round2(balance - amt)
            txn_id_counter += 1
            narration = f"NEFT DR-VENDOR{random.randint(100,999)}-NETBANK"
            ledger_rows.append([txn_id_counter, date_str, "NEFT_VENDOR_DEBIT", narration, amt, "", balance])

        if random.random() < 0.55:  
            for _ in range(random.randint(3, 7)):
                amt = round2(random.choice([10000, 12000, 15000, 20000, 25000, 50000]))
                balance = round2(balance - amt)
                txn_id_counter += 1
                narration = f"NEFT DR-SUPPLIER{random.randint(100,999)}-NETBANK"
                ledger_rows.append([txn_id_counter, date_str, "NEFT_VENDOR_DEBIT", narration, amt, "", balance])

        # 5. MDR recovery charge
        if random.random() < 0.85:
            amt = round2(random.uniform(8, 320))
            balance = round2(balance - amt)
            txn_id_counter += 1
            narration = f"MDR RCVRY-{date_str}"
            ledger_rows.append([txn_id_counter, date_str, "MDR_RECOVERY_CHARGE", narration, amt, "", balance])

    DATA_DIR.mkdir(exist_ok=True)
    
    with open(DATA_DIR / "ochicken_ledger.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "value_date", "txn_type", "narration", "withdrawal_amt", "deposit_amt", "closing_balance"])
        w.writerows(ledger_rows)

    with open(DATA_DIR / "ochicken_ground_truth.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txn_id", "txn_type", "gross_amount", "correct_fee", "correct_gst", "correct_net", "stated_net", "discrepancy_amount", "injected_error_type"])
        w.writerows(truth_rows)

    n_rzp = generate_rzp_settlement_report(truth_rows)

    print(f"Generated {len(ledger_rows)} ledger transactions across {NUM_DAYS} days.")
    print(f"  Files written to {DATA_DIR}/")
    print(f"  - ochicken_ledger.csv (Bank Statement: {len(ledger_rows)} txns)")
    print(f"  - razorpay_settlement_report.csv (Gateway Statement: {n_rzp} txns)")
    print(f"  - ochicken_ground_truth.csv (Eval Hidden Truth)")

if __name__ == "__main__":
    generate()