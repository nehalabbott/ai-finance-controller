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
    audit_path = ROOT / "output" / "reconciliation_audit_sheet.csv"
    if not audit_path.exists():
        return pd.DataFrame(), {}
    audit_df = pd.read_csv(audit_path)
    with open(ROOT / 'contracts' / 'ochicken_contract.json', 'r') as f:
        contract = json.load(f)
    return audit_df, contract

audit_df, contract = load_data()

# Header
st.title("🐔 O'Chicken AI Finance Controller")
st.markdown("**Razorpay AI Buildathon 2026 | Track 04 Finance Operations Hub**")
st.markdown("---")

if audit_df.empty:
    st.warning("⚠️ No audit sheet found. Run `python main.py` first to execute reconciliation.")
    st.stop()

# 1. Standardize Schema Across New & Legacy Columns
discrepancy_col = "Discrepancy (₹)" if "Discrepancy (₹)" in audit_df.columns else "variance_inr"
if discrepancy_col not in audit_df.columns:
    audit_df[discrepancy_col] = 0.0

if "Actual Planted Error" in audit_df.columns:
    real_leak_mask = audit_df["Actual Planted Error"] != "None (Valid Variance)"
else:
    real_leak_mask = pd.Series([True] * len(audit_df))

action_col = "recommended_action" if "recommended_action" in audit_df.columns else "Agent Recommended Action"
escalated_mask = audit_df[action_col].astype(str).str.contains("ESCALATE", case=False, na=False) if action_col in audit_df.columns else pd.Series([True] * len(audit_df))

total_at_risk = float(audit_df.loc[real_leak_mask, discrepancy_col].abs().sum())
recovered = float(audit_df.loc[real_leak_mask & escalated_mask, discrepancy_col].abs().sum())
recovery_pct = (recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0
missed_leaks = int(real_leak_mask.sum() - (real_leak_mask & escalated_mask).sum())

# 2. Executive KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Capital at Risk", f"₹{total_at_risk:,.2f}")
with col2:
    st.metric("Capital Recovered", f"₹{recovered:,.2f}", delta=f"{recovery_pct:.1f}% Recovery")
with col3:
    st.metric("Real Leaks Missed", missed_leaks, delta=None if missed_leaks == 0 else "Needs attention", delta_color="inverse")
with col4:
    st.metric("Actionable Exceptions", len(audit_df))

# Fallback diagnostic indicator
fallback_used = False
if "confidence" in audit_df.columns:
    fallback_used = (audit_df["confidence"] == 0.0).any()
elif "Used LLM" in audit_df.columns:
    fallback_used = (~audit_df["Used LLM"]).any()

if fallback_used:
    st.warning("⚠️ One or more exceptions used deterministic fallback heuristics. Verify GROQ_API_KEY for live agentic diagnoses.")

st.markdown("---")

# 3. Finance Operator Action Card (Judge UX Recommendation)
st.subheader("⚡ Operator Action Queue (Highest Risk Triage)")
high_risk_subset = audit_df.sort_values(by=discrepancy_col, key=abs, ascending=False)

if not high_risk_subset.empty:
    top_txn = high_risk_subset.iloc[0]
    txn_id = top_txn.get("transaction_id", top_txn.get("Transaction ID", "TXN_UNKNOWN"))
    variance_amt = abs(float(top_txn.get(discrepancy_col, 0.0)))
    cause_desc = top_txn.get("root_cause", top_txn.get("Agent Diagnosis", "Discrepancy detected"))
    rec_action = top_txn.get("recommended_action", top_txn.get("Agent Recommended Action", "ESCALATE TO HUMAN REVIEW"))
    confidence_score = top_txn.get("confidence", 1.0)

    with st.container(border=True):
        t_col1, t_col2 = st.columns([3, 1])
        with t_col1:
            st.markdown(f"#### 🚨 Highest Risk Item: `{txn_id}` — **₹{variance_amt:,.2f} Variance**")
            st.markdown(f"**Root Cause Diagnosis:** {cause_desc}")
            st.markdown(f"**Action Plan:** `{rec_action}` (Confidence: {confidence_score:.0%})")
        with t_col2:
            st.write("")
            if st.button("✅ Approve Dispute Ticket", use_container_width=True):
                st.success(f"Dispute initiated for `{txn_id}` with Razorpay Support.")
            if st.button("⚠️ Dismiss / Mark Cleared", use_container_width=True):
                st.info(f"`{txn_id}` marked as cleared.")

st.markdown("---")

# 4. Filterable Audit Table
st.subheader("📊 Complete Audit Sheet")
search_term = st.text_input("🔍 Search by Transaction ID, Cause, or Recommendation:", "")
if search_term:
    filtered_df = audit_df[audit_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
else:
    filtered_df = audit_df

st.dataframe(filtered_df, use_container_width=True)

st.markdown("---")

# 5. Settlement Q&A AI Assistant (Groq Architecture)
st.subheader("💬 Settlement Q&A Assistant")
st.caption("Ask questions about anomalies, contract clauses, or fee structures.")

api_key = os.environ.get("GROQ_API_KEY")
try:
    client = Groq(api_key=api_key) if api_key else None
except Exception:
    client = None

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("E.g., 'Why was transaction TXN_1179 escalated?'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if client:
            # Token-optimized context payload
            slim_records = audit_df.drop(columns=["Date", "Narration"], errors="ignore").head(25).to_dict(orient="records")
            system_instruction = f"""You are the O'Chicken Financial Q&A Assistant. Answer precisely based on:
Contract: {json.dumps(contract)}
Audit Data Sample: {json.dumps(slim_records)}
Rules: Be concise, cite exact Transaction IDs, and detail the fee math clearly."""

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
                err_text = f"Error generating response: {e}"
                st.markdown(err_text)
                st.session_state.messages.append({"role": "assistant", "content": err_text})
        else:
            st.markdown("⚠️ Groq client not initialized. Ensure `GROQ_API_KEY` is exported in your environment.")