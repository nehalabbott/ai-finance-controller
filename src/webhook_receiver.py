import hmac
import hashlib
import os
import json
from datetime import date, datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel
from groq import Groq

app = FastAPI(
    title="O'Chicken AI Finance Controller - Real-Time Webhook Gateway",
    version="1.0.1"
)

ROOT = Path(__file__).resolve().parent.parent

PROMO_START = date(2026, 7, 15)
PROMO_END = date(2026, 7, 31)
PROMO_MDR_RATE = 1.50 / 100

# Replaced Gemini with the unified Groq client architecture
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

# In-memory idempotency store (replace with Redis/Postgres in production)
PROCESSED_EVENTS = set()

class SettlementEvent(BaseModel):
    transaction_id: str
    date: str  
    gross_amt: float
    fee_deducted: float
    tax_deducted: float
    net_credited: float
    payment_method: str  
    is_upi_routed: bool = False  

def load_contract():
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        return json.load(f)

async def verify_razorpay_signature(body: bytes, signature: str):
    """Validates the webhook originated from Razorpay."""
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").encode()
    if not secret:
        print("⚠️ Warning: RAZORPAY_WEBHOOK_SECRET not set. Skipping validation.")
        return
        
    expected_sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

def adapt_razorpay_payload(raw_payload: dict) -> SettlementEvent:
    """Transforms a genuine Razorpay payload into the internal schema."""
    entity = raw_payload.get("payload", {}).get("settlement", {}).get("entity", {})
    
    # Razorpay uses paise; convert to INR
    return SettlementEvent(
        transaction_id=entity.get("id", "UNKNOWN"),
        # Timestamp conversion omitted for brevity; assuming date format YYYY-MM-DD
        date=datetime.now().strftime("%Y-%m-%d"), 
        gross_amt=entity.get("amount", 0) / 100.0,
        fee_deducted=entity.get("fees", 0) / 100.0,
        tax_deducted=entity.get("tax", 0) / 100.0,
        net_credited=entity.get("amount_settled", 0) / 100.0,
        payment_method="RAZORPAY_PAYOUT_BATCH",
        is_upi_routed=False 
    )

def compute_expected_fee(contract, event: SettlementEvent):
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
    return {"status": "active", "service": "O'Chicken Real-Time Webhook Gateway"}

@app.post("/api/v1/reconcile-webhook")
async def process_incoming_settlement(
    request: Request,
    x_razorpay_signature: str = Header(None),
    x_razorpay_event_id: str = Header(None)
):
    # 1. Security & Idempotency Checks
    if not x_razorpay_signature or not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay headers")
        
    if x_razorpay_event_id in PROCESSED_EVENTS:
        return {"status": "ignored", "reason": "Duplicate event ID"}

    raw_body = await request.body()
    await verify_razorpay_signature(raw_body, x_razorpay_signature)
    PROCESSED_EVENTS.add(x_razorpay_event_id)

    # 2. Payload Parsing & Transformation
    payload_dict = json.loads(raw_body.decode("utf-8"))
    
    if payload_dict.get("event") != "settlement.processed":
        return {"status": "ignored", "reason": "Unhandled event type"}
        
    event = adapt_razorpay_payload(payload_dict)
    contract = load_contract()

    # 3. Deterministic Algebraic Check
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
    
    # 4. Tier 2: Agentic Diagnostic Layer (Groq Integration)
    if not is_clean and client:
        prompt = f"""
        Analyze this financial reconciliation exception based on contract rules.
        
        Transaction Data: {event.dict()}
        Calculated Variance: ₹{variance}
        Contract Rules: {json.dumps(contract)}
        
        Return a valid JSON object with the following exact keys:
        - "root_cause": precise string explaining the discrepancy
        - "confidence": float between 0.0 and 1.0
        - "recommended_action": clear operational instruction
        - "human_approval_required": boolean
        """
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a financial AI controller. Always output strictly valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            result["ai_diagnosis"] = json.loads(response.choices[0].message.content)
        except Exception as e:
            result["ai_diagnosis"] = {"error": f"Agent Failed: {str(e)}"}

    return result