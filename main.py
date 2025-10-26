import subprocess
import sys

PYTHON = sys.executable  # use the same Python interpreter as PyCharm/venv

print("🔹 Running ETL (clean + load data)...")
subprocess.run([PYTHON, "etl/clean_load.py"], check=True)

print("🔹 Starting Flask API...")
api_process = subprocess.Popen([PYTHON, "api/app.py"])

print("🔹 Launching Streamlit dashboard...")
subprocess.run(["streamlit", "run", "client/streamlit_app.py"])

api_process.terminate()
