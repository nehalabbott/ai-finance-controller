import json
import os
import urllib.request
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def compute_live_metrics():
    """
    Pulls real numbers from this run's actual output files instead of using
    hardcoded constants, so the alert always reflects what actually happened -
    including when the LLM tier fell back to heuristics, or when a future
    dataset run produces different figures.
    """
    audit_path = ROOT / "output" / "reconciliation_audit_sheet.csv"
    audit_df = pd.read_csv(audit_path)

    total_leaks_caught = (audit_df["Actual Planted Error"] != "None (Valid Variance)").sum()
    capital_recovered_inr = audit_df.loc[
        audit_df["Actual Planted Error"] != "None (Valid Variance)", "Discrepancy (₹)"
    ].abs().sum()
    fallback_used = audit_df["Used LLM"].eq(False).any() if "Used LLM" in audit_df.columns else False

    return {
        "total_leaks_caught": int(total_leaks_caught),
        "capital_recovered_inr": round(float(capital_recovered_inr), 2),
        "fallback_used": bool(fallback_used),
        "total_flagged": len(audit_df),
    }

def dispatch_finance_alert(webhook_url: str = None):
    metrics = compute_live_metrics()
    total_leaks_caught = metrics["total_leaks_caught"]
    capital_recovered_inr = metrics["capital_recovered_inr"]
    engine_note = (
        "⚠️ Deterministic fallback used for one or more exceptions - not a live LLM diagnosis."
        if metrics["fallback_used"]
        else "Tier 2 diagnoses were produced by a live LLM call."
    )
    
    # Constructing a rich Markdown card payload (compatible with Slack, Discord, or MS Teams)
    slack_payload = {
        "text": "🚨 *O'Chicken AI Finance Controller: Reconciliation Report Complete* 🚨",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Autonomous Audit Execution Summary*\nTier 1 deterministic engine and Tier 2 Gemini agent have finalized the 30-day settlement cycle."
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Capital Recovered:*\n₹{capital_recovered_inr}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Anomalies Flagged:*\n{total_leaks_caught} Leaks Caught"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Records Reviewed:*\n{metrics['total_flagged']}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📁 *Output Status:* Actionable audit sheet successfully saved to `/output/reconciliation_audit_sheet.csv`.\n{engine_note}\nRun `tests/eval_harness.py` for precision/recall against ground truth."
                }
            }
        ]
    }

    print("------------------------------------------------------------")
    print("📢 DISPATCHING FINANCE OPERATIONS ALERT...")
    print("------------------------------------------------------------")
    print(json.dumps(slack_payload, indent=2))
    print("------------------------------------------------------------")
    print("✅ Alert simulation successfully compiled and routed!")

    # If a real webhook URL is provided, push it live
    if webhook_url:
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(slack_payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                print(f"Webhook delivered successfully. Status: {response.status}")
        except Exception as e:
            print(f"Failed to deliver webhook live: {e}")

if __name__ == "__main__":
    dispatch_finance_alert()