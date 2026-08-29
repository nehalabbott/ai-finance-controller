import json
import time
import pandas as pd
from pathlib import Path
from groq import Groq
import os

ROOT = Path(__file__).resolve().parent.parent

def run_tier2_agent():
    print("------------------------------------------------------------")
    print("🤖 BOOTING TIER 2: AGENTIC DIAGNOSTIC LAYER 🤖")
    print("------------------------------------------------------------")

    # BUG FIX: previously this fell back to GEMINI_API_KEY and handed it to
    # the Groq() client, which would just fail auth silently and drop straight
    # to the fallback heuristic. Only use the key that actually belongs to
    # this client.
    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key) if api_key else None
    if not api_key:
        print("⚠️  No GROQ_API_KEY set in environment. Tier 2 will use the")
        print("    deterministic fallback heuristic for every exception.")

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
        res_df = None
        last_error = None
        # Retry once on transient failures (rate limit / brief network blip)
        # before giving up and falling back - a single flaky call shouldn't
        # silently degrade the whole batch.
        for attempt in range(2):
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
                break
            except Exception as e:
                last_error = e
                if attempt == 0:
                    print(f"⚠️ Attempt 1 failed ({e}). Retrying once...")
                    time.sleep(2)

        if res_df is None:
            print(f"❌ API batch processing failed after retry ({last_error}).")
            print("   Falling back to deterministic heuristics for this batch.")
            res_df = fallback_heuristics(exceptions_df)
    else:
        res_df = fallback_heuristics(exceptions_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    res_df.to_csv(output_path, index=False)

    fallback_count = res_df["reasoning"].str.contains("Fallback rule applied", na=False).sum()
    if fallback_count > 0:
        print(f"⚠️  {fallback_count}/{len(res_df)} record(s) used the fallback heuristic,")
        print(f"    not a live LLM diagnosis. See 'Used LLM' column in the audit sheet.")
    print(f"✅ Tier 2 Agent complete. Resolutions saved to {output_path}")

def fallback_heuristics(df):
    """
    Deterministic backstop for when the LLM is unavailable. Rather than
    guessing a single generic root cause for every record (which is
    misleading - it implies false confidence), this derives the most likely
    cause directly from the Tier 1 exception_type, and always escalates for
    manual review since we have no diagnostic reasoning to justify clearing it.
    """
    cause_map = {
        "FEE_VARIANCE": "FEE_VARIANCE_UNRESOLVED",
        "NET_MISMATCH": "GATEWAY_OVERCHARGE",
        "MISSING_IN_GATEWAY": "GHOST_TXN_BANK_SIDE",
        "MISSING_IN_BANK": "GHOST_TXN_GATEWAY_SIDE",
    }
    results = []
    for _, row in df.iterrows():
        root_cause = cause_map.get(row.get("exception_type"), "UNCLASSIFIED")
        results.append({
            "transaction_id": row["transaction_id"],
            "root_cause": root_cause,
            "action": "ESCALATE",
            "reasoning": (
                f"Fallback rule applied due to missing or rate-limited LLM connection. "
                f"Escalated by default based on Tier 1 exception_type='{row.get('exception_type')}'; "
                f"requires manual review since no contract-aware diagnosis was performed."
            )
        })
    return pd.DataFrame(results)

if __name__ == "__main__":
    run_tier2_agent()