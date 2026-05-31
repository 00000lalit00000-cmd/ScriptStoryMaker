import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    streamlit_app = root / "frontend" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(streamlit_app)])
