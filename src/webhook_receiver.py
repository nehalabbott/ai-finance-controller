from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import json
from datetime import date, datetime
from pathlib import Path
from google import genai
from google.genai import types

app = FastAPI(
    title="O'Chicken AI Finance Controller - Real-Time Webhook Gateway",
    version="1.0.0"
)

ROOT = Path(__file__).resolve().parent.parent

# Keep this in sync with src/reconciler.py - both tiers must agree on the
# promo window or they will disagree on what counts as an exception.
PROMO_START = date(2026, 7, 15)
PROMO_END = date(2026, 7, 31)
PROMO_MDR_RATE = 1.50 / 100

try:
    client = genai.Client()
except Exception as e:
    client = None

# Pydantic schema mirroring Razorpay settlement / bank payloads
class SettlementEvent(BaseModel):
    transaction_id: str
    date: str  # expected format YYYY-MM-DD
    gross_amt: float
    fee_deducted: float
    tax_deducted: float
    net_credited: float
    payment_method: str  # "CARD_TERMINAL_SETTLEMENT" | "RAZORPAY_PAYOUT_BATCH"
    is_upi_routed: bool = False  # caller must tell us this; it isn't derivable from the schema otherwise

def load_contract():
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        return json.load(f)

def compute_expected_fee(contract, event: "SettlementEvent"):
    """
    Mirrors the contract-aware logic in src/reconciler.py. Previously this
    read contract.get("rules", {}) - a key that doesn't exist anywhere in
    ochicken_contract.json - so it silently always fell back to a generic
    2% MDR / 18% GST regardless of payment method, promo window, or UPI
    exemption. That meant Tier 3 (this webhook) could disagree with Tier 1
    (the batch reconciler) on the exact same transaction.
    """
    txn_date = datetime.strptime(event.date, "%Y-%m-%d").date()

    if event.payment_method == "CARD_TERMINAL_SETTLEMENT":
        rules = contract["card_terminal_settlement"]
        rate = PROMO_MDR_RATE if PROMO_START <= txn_date <= PROMO_END else rules["mdr_rate_percent"] / 100
        expected_mdr = event.gross_amt * rate
        expected_gst = expected_mdr * rules["gst_on_mdr_percent"] / 100
        return expected_mdr, expected_gst

    rules = contract["razorpay_payout_batch"]
    if event.is_upi_routed or event.gross_amt < rules["commission_waived_below_amount"]:
        return 0.0, 0.0
    expected_commission = event.gross_amt * rules["commission_rate_percent"] / 100
    expected_gst = expected_commission * rules["gst_on_commission_percent"] / 100
    return expected_commission, expected_gst

@app.get("/")
def health_check():
    return {"status": "active", "service": "O'Chicken Real-Time Reconciliation Daemon"}

@app.post("/api/v1/reconcile-webhook")
def process_incoming_settlement(event: SettlementEvent):
    contract = load_contract()

    # Tier 1: Deterministic Algebraic Check
    # Expected Net = Gross - (Gross * MDR) - (MDR * GST)
    expected_mdr, expected_gst = compute_expected_fee(contract, event)
    expected_net = event.gross_amt - expected_mdr - expected_gst
    
    variance = round(event.net_credited - expected_net, 2)
    is_clean = abs(variance) < 0.05
    
    result = {
        "transaction_id": event.transaction_id,
        "status": "RECONCILED_CLEAN" if is_clean else "EXCEPTION_FLAGGED",
        "variance_inr": variance,
        "action": "IGNORE" if is_clean else "ESCALATE",
        "diagnostic": "Deterministic check passed cleanly." if is_clean else "Variance detected. Dispatched to Tier 2 AI Agent."
    }
    
    # Tier 2: If an exception is found, trigger a live LLM analysis.
    # Model families move fast - re-check https://ai.google.dev/gemini-api/docs/models
    # before a demo in case gemini-3.6-flash has been superseded/deprecated by then.
    if not is_clean and client:
        prompt = f"""
        Analyze this financial reconciliation exception based on contract rules:
        Transaction Data: {event.dict()}
        Calculated Variance: ₹{variance}
        Contract Rules: {json.dumps(contract)}
        
        Determine root cause (e.g., GATEWAY_OVERCHARGE, UPI_WAIVER, PROMO_RATE) and provide brief JSON response with keys: 'root_cause' and 'reasoning'.
        """
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            ai_insights = json.loads(response.text)
            result["ai_diagnosis"] = ai_insights
        except Exception as e:
            result["ai_diagnosis"] = {"error": str(e)}

    return result