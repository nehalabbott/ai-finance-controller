import pandas as pd
import json
from google import genai
from google.genai import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# BUG FIX: previously this ran at import time and used `raise` on failure,
# which crashed the whole module the instant it was imported without a key -
# inconsistent with the graceful (client = None) fallback pattern used
# everywhere else in this project (agent.py, app.py, webhook_receiver.py).
try:
    client = genai.Client()
except Exception as e:
    print(f"⚠️ Could not initialize Gemini client ({e}). Set GEMINI_API_KEY and retry.")
    client = None


def load_knowledge_base():
    """
    NOTE: this file previously had TWO copies of this function (and of
    run_finance_chat below it) - a leftover from an incomplete refactor.
    Because Python executes top-to-bottom, the `if __name__ == "__main__"`
    guard ran before the second, token-efficient version was even defined,
    so that version was silently dead code and never actually used. This is
    the single, consolidated version - the token-efficient one, since it's
    materially cheaper to run against a real API.
    """
    audit_path = ROOT / "output" / "reconciliation_audit_sheet.csv"
    if not audit_path.exists():
        raise FileNotFoundError(
            "output/reconciliation_audit_sheet.csv not found. "
            "Run `python main.py` first to generate the audit sheet."
        )
    audit_df = pd.read_csv(audit_path)

    # Strip bulky text columns the LLM doesn't need for reasoning, and use a
    # compact JSON representation instead of a raw CSV string - meaningfully
    # cheaper on tokens for larger audit sheets.
    slim_df = audit_df.drop(columns=["Date", "Narration", "Agent Reasoning / Cause"], errors="ignore")
    optimized_audit_data = slim_df.to_dict(orient="records")

    with open(ROOT / "contracts" / "ochicken_contract.json", "r") as f:
        contract = json.load(f)

    return optimized_audit_data, contract


def run_finance_chat():
    if client is None:
        print("❌ Cannot start Q&A agent: Gemini client not initialized. Set GEMINI_API_KEY.")
        return

    try:
        optimized_audit_data, contract = load_knowledge_base()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    system_instruction = f"""You are the O'Chicken Financial Q&A Assistant.
You answer user questions based EXCLUSIVELY on this merchant contract and the audit data.

Contract Terms:
{json.dumps(contract)}

Audit Exceptions Data:
{json.dumps(optimized_audit_data)}

Rules:
1. Trace all answers back to specific Transaction IDs.
2. Clearly explain the math or contract clause that justifies your answer.
3. Be concise and professional.
"""

    print("Booting Settlement Q&A Agent... \n")

    chat = client.chats.create(
        model="gemini-3.6-flash",  # re-check https://ai.google.dev/gemini-api/docs/models before a demo
        config=types.GenerateContentConfig(system_instruction=system_instruction)
    )

    print("Agent ready! Ask about your financial data (type 'exit' to quit).")
    print("Example: 'Why was transaction 1179 escalated?' or 'How much money are we losing to gateway overcharges?'\n")

    while True:
        user_query = input("Finance Team: ")
        if user_query.lower() in ["exit", "quit"]:
            print("Shutting down Q&A agent.")
            break

        try:
            response = chat.send_message_stream(user_query)
            print(f"\nAI Controller: ", end="", flush=True)
            for chunk in response:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            print("\n\n" + "-" * 50)
        except Exception as e:
            print(f"\nError processing query: {e}\n")


if __name__ == "__main__":
    run_finance_chat()
