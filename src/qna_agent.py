import pandas as pd
import json
from google import genai
from google.genai import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    client = genai.Client()
except Exception as e:
    raise ValueError(f"Failed to initialize Gemini Client. Error: {e}")

def load_knowledge_base():
    # Load the actionable exceptions report and the contract
    audit_df = pd.read_csv(ROOT / "output" / "reconciliation_audit_sheet.csv")
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        contract = json.load(f)
    return audit_df, contract

def run_finance_chat():
    audit_df, contract = load_knowledge_base()
    
    # Injecting the data directly into the system instruction
    system_instruction = f"""You are the O'Chicken Financial Q&A Assistant.
You answer user questions based EXCLUSIVELY on this merchant contract and the subsequent reconciliation audit data.

Contract Terms:
{json.dumps(contract, indent=2)}

Audit Exceptions Data (CSV):
{audit_df.to_csv(index=False)}

Rules:
1. Trace all answers back to specific Transaction IDs.
2. Clearly explain the math or contract clause that justifies your answer.
3. Be concise and professional.
"""

    print("Booting Settlement Q&A Agent... \n")
    
    # Initialize an interactive chat session
    chat = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(system_instruction=system_instruction)
    )
    
    print("Agent ready! Ask about your financial data (type 'exit' to quit).")
    print("Example: 'Why was transaction 1179 escalated?' or 'How much money are we losing to gateway overcharges?'\n")
    
    while True:
        user_query = input("Finance Team: ")
        if user_query.lower() in ['exit', 'quit']:
            print("Shutting down Q&A agent.")
            break
            
        try:
            # Use the streaming endpoint instead of the standard one
            response = chat.send_message_stream(user_query)
            
            print(f"\nAI Controller: ", end="", flush=True)
            
            # Print each chunk instantly as it arrives from the API
            for chunk in response:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
            
            print("\n\n" + "-" * 50)
            
        except Exception as e:
            print(f"\nError processing query: {e}\n")
if __name__ == "__main__":
    run_finance_chat()

def load_knowledge_base():
    audit_df = pd.read_csv(ROOT / "output" / "reconciliation_audit_sheet.csv")
    
    # 1. Strip out bulky text columns that the LLM doesn't need for logical reasoning
    slim_df = audit_df.drop(columns=['Date', 'Narration', 'Agent Reasoning / Cause'])
    
    # 2. Convert to a token-efficient JSON format instead of a raw CSV string
    optimized_audit_data = slim_df.to_dict(orient='records')
    
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        contract = json.load(f)
        
    return optimized_audit_data, contract

def run_finance_chat():
    optimized_audit_data, contract = load_knowledge_base()
    
    system_instruction = f"""You are the O'Chicken Financial Q&A Assistant.
You answer user questions based EXCLUSIVELY on this merchant contract and the audit data.

Contract Terms:
{json.dumps(contract)}

Audit Exceptions Data:
{json.dumps(optimized_audit_data)}

Rules:
1. Trace all answers back to specific Transaction IDs.
2. Clearly explain the math or contract clause.
3. Be concise and professional.
"""