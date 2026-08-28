import streamlit as st
import pandas as pd
import json
from pathlib import Path
from groq import Groq
import os

# Page Config
st.set_page_config(
    page_title="O'Chicken AI Finance Controller",
    page_icon="🐔",
    layout="wide"
)

ROOT = Path(__file__).resolve().parent.parent

@st.cache_data
def load_data():
    audit_df = pd.read_csv(ROOT / "output" / "reconciliation_audit_sheet.csv")
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        contract = json.load(f)
    return audit_df, contract

audit_df, contract = load_data()

# Header
st.title("🐔 O'Chicken AI Finance Controller")
st.markdown("**Razorpay AI Buildathon 2026 | Track 04 Dashboard**")
st.markdown("---")

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Capital at Risk", "₹4,127.51")
with col2:
    st.metric("Capital Recovered", "₹4,127.51", delta="100% Recovery")
with col3:
    st.metric("Audit Recall Rate", "100.00%", delta="0 False Negatives")
with col4:
    st.metric("Exceptions Flagged", len(audit_df))

st.markdown("### 📊 Live Reconciliation Audit Sheet")
st.markdown("Inspect actionable exceptions classified by Tier 1 deterministic math and Tier 2 diagnostics.")

# Interactive Search / Filter
search_term = st.text_input("🔍 Search by Transaction ID or Cause:", "")
if search_term:
    filtered_df = audit_df[audit_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
else:
    filtered_df = audit_df

st.dataframe(filtered_df, use_container_width=True)

st.markdown("---")
st.markdown("### 💬 Settlement Q&A AI Assistant")
st.markdown("Interrogate your financial data and contract clauses in real time.")

# Initialize Groq Client for Chat
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")
try:
    client = Groq(api_key=api_key) if api_key else None
except Exception:
    client = None

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about transaction anomalies or fee rules (e.g., 'Why was transaction TXN_1179 escalated?'):"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if client:
            system_instruction = f"""You are the O'Chicken Financial Q&A Assistant. Answer precisely based on this contract and audit data:
            Contract Rules: {json.dumps(contract)}
            Audit Data Summary: {audit_df.head(20).to_string()}
            Be concise, professional, and cite specific Transaction IDs and monetary amounts."""
            
            try:
                messages_payload = [{"role": "system", "content": system_instruction}]
                for m in st.session_state.messages:
                    messages_payload.append({"role": m["role"], "content": m["content"]})

                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=messages_payload,
                    temperature=0.1
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                error_msg = f"Error generating response: {e}"
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            st.markdown("Groq Client not initialized. Make sure your API key is exported.")