import subprocess
import sys
from pathlib import Path

def run_pipeline():
    print("="*60)
    print("🚀 BOOTING O'CHICKEN AI FINANCE CONTROLLER PIPELINE 🚀")
    print("="*60)

    # List of all your pipeline scripts in execution order
    scripts = [
        ("1. Generating Synthetic Data...", "src/generate_data.py"),
        ("2. Running Deterministic Reconciler (Tier 1)...", "src/reconciler.py"),
        ("3. Running AI Diagnostic Agent (Tier 2)...", "src/agent.py"),
        ("4. Exporting Enterprise Audit Sheet...", "src/export_audit_sheet.py"),
        ("5. Evaluating Accuracy Metrics...", "tests/eval_harness.py"),
    ]

    for step_name, script_path in scripts:
        print(f"\n>> {step_name}")
        try:
            # Executes the script exactly as if you typed it in the terminal
            subprocess.run([sys.executable, script_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Pipeline halted at {script_path}. Error code: {e.returncode}")
            sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE! All reports saved to the /output folder.")
    print("💡 To interact with the audit sheet, run: python src/qna_agent.py")
    print("="*60)

if __name__ == "__main__":
    run_pipeline()