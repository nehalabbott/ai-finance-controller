import json
import pandas as pd
from pathlib import Path
from groq import Groq
import os

ROOT = Path(__file__).resolve().parent.parent

def run_tier2_agent():
    print("------------------------------------------------------------")
    print("🤖 BOOTING TIER 2: AGENTIC DIAGNOSTIC LAYER 🤖")
    print("------------------------------------------------------------")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key) if api_key else None

    exceptions_path = ROOT / "output" / "tier1_exceptions.csv"
    contract_path = ROOT / "contracts" / "ochicken_contract.json"
    output_path = ROOT / "output" / "agent_resolutions.csv"

    if not exceptions_path.exists():
        print("❌ Error: tier1_exceptions.csv not found. Run reconciler.py first.")
        return

    exceptions_df = pd.read_csv(exceptions_path)
    with open(contract_path, "r") as f:
        contract_data = json.load(f)

    print(f"Loaded {len(exceptions_df)} exceptions for batch analysis.")

    if client and len(exceptions_df) > 0:
        payload = exceptions_df.to_dict(orient="records")
        prompt = f"""
        You are an elite Enterprise AI Finance Controller. Analyze the following batch of financial reconciliation exceptions against the legal contract rules provided.
        
        Contract Rules:
        {json.dumps(contract_data, indent=2)}

        Exceptions Batch:
        {json.dumps(payload, indent=2)}

        For each record, determine the precise root cause (e.g., GATEWAY_OVERCHARGE, UPI_WAIVER, PROMO_RATE, GHOST_TXN) and choose an action: 'IGNORE' or 'ESCALATE'.
        Return your response strictly as a valid JSON array of objects with keys: 'transaction_id', 'root_cause', 'action', and 'reasoning'.
        Constraint: Do not include any LaTeX syntax, equations, or raw block formatting in your text descriptions; use plain text or standard formatting only.
        """

        print("Dispatching batched request to active Groq model...")
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a financial auditing assistant that outputs strictly valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            parsed_json = json.loads(raw_content)
            if isinstance(parsed_json, dict):
                resolutions = next((v for v in parsed_json.values() if isinstance(v, list)), [])
            else:
                resolutions = parsed_json
            
            res_df = pd.DataFrame(resolutions)
        except Exception as e:
            print(f"⚠️ API batch processing failed ({e}). Falling back to deterministic heuristics.")
            res_df = fallback_heuristics(exceptions_df)
    else:
        res_df = fallback_heuristics(exceptions_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(output_path, index=False)
    print(f"✅ Tier 2 Agent complete. Resolutions saved to {output_path}")

def fallback_heuristics(df):
    results = []
    for _, row in df.iterrows():
        results.append({
            "transaction_id": row["transaction_id"],
            "root_cause": "GATEWAY_OVERCHARGE",
            "action": "ESCALATE",
            "reasoning": "Fallback rule applied due to missing or rate-limited LLM connection."
        })
    return pd.DataFrame(results)

if __name__ == "__main__":
    run_tier2_agent()