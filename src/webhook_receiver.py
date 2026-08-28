from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import json
from pathlib import Path
from google import genai
from google.genai import types

app = FastAPI(
    title="O'Chicken AI Finance Controller - Real-Time Webhook Gateway",
    version="1.0.0"
)

ROOT = Path(__file__).resolve().parent.parent

try:
    client = genai.Client()
except Exception as e:
    client = None

# Pydantic schema mirroring Razorpay settlement / bank payloads
class SettlementEvent(BaseModel):
    transaction_id: str
    date: str
    gross_amt: float
    fee_deducted: float
    tax_deducted: float
    net_credited: float
    payment_method: str

def load_contract():
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        return json.load(f)

@app.get("/")
def health_check():
    return {"status": "active", "service": "O'Chicken Real-Time Reconciliation Daemon"}

@app.post("/api/v1/reconcile-webhook")
def process_incoming_settlement(event: SettlementEvent):
    contract = load_contract()
    
    # Tier 1: Deterministic Algebraic Check
    # Expected Net = Gross - (Gross * MDR) - (MDR * GST)
    method_rules = contract.get("rules", {}).get(event.payment_method, {"mdr": 0.02, "gst": 0.18})
    expected_mdr = event.gross_amt * method_rules["mdr"]
    expected_gst = expected_mdr * method_rules["gst"]
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
    
    # Tier 2: If an exception is found, trigger Gemini 3.6-flash live analysis
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