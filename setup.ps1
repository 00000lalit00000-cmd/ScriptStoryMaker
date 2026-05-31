# Setup Script for ScriptStoryMaker

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

Write-Host "Setup complete. Activate the virtual environment with:`n.\.venv\Scripts\Activate.ps1"