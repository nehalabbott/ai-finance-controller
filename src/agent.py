import pandas as pd
import json
from google import genai
from google.genai import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The SDK automatically detects the GEMINI_API_KEY environment variable
try:
    client = genai.Client()
except Exception as e:
    raise ValueError(f"Failed to initialize Gemini Client. Make sure GEMINI_API_KEY is set. Error: {e}")

def load_contract():
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        return json.load(f)

def run_ai_diagnostics():
    contract = load_contract()
    exceptions_df = pd.read_csv(ROOT / 'output' / 'tier1_exceptions.csv')
    
    print(f"Booting AI Agent... Processing all {len(exceptions_df)} exceptions in ONE batch request!\n")
    
    # 1. Package all transactions into a single JSON array
    exceptions_list = exceptions_df.to_dict(orient='records')
    payload_str = json.dumps(exceptions_list, indent=2)
    
    system_prompt = f"""You are an AI Finance Controller for O'Chicken.
Your job is to diagnose a batch of reconciliation exceptions by referencing this contract:
{json.dumps(contract, indent=2)}

Determine if each exception is a valid contractual variance (like a UPI waiver or Promo rate) or a genuine anomaly requiring human escalation.
Respond strictly with a JSON array of objects. Each object MUST contain:
- "transaction_id": The exact ID of the transaction.
- "root_cause": A short string classifying the issue (e.g., "UPI_WAIVER", "PROMO_RATE", "GATEWAY_OVERCHARGE", "GHOST_TXN", "UNKNOWN").
- "reasoning": A brief explanation of your logic based on the contract.
- "recommended_action": "IGNORE" if it's a valid variance, or "ESCALATE" if it's an anomaly."""

    try:
        # 2. Fire one single API call (Takes ~3-5 seconds total)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=payload_str,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
        )
        
        # 3. Parse the batch response
        diagnoses = json.loads(response.text)
        diag_map = {d["transaction_id"]: d for d in diagnoses}
        resolutions = []
        
        # 4. Map the AI's diagnoses back to the original rows
        for _, row in exceptions_df.iterrows():
            tx_id = row["transaction_id"]
            diag = diag_map.get(tx_id, {
                "root_cause": "API_ERROR", 
                "reasoning": "Model missed this row in the batch output.", 
                "recommended_action": "ESCALATE"
            })
            
            print(f"[{tx_id}] -> {diag.get('root_cause')} ({diag.get('recommended_action')})")
            resolutions.append({**row.to_dict(), **diag})
            
        output_df = pd.DataFrame(resolutions)
        output_df.to_csv(ROOT / 'output' / 'agent_resolutions.csv', index=False)
        print(f"\nDiagnostic run complete! Report saved to output/agent_resolutions.csv")

    except Exception as e:
        print(f"Batch Processing Failed: {e}")

if __name__ == "__main__":
    run_ai_diagnostics()