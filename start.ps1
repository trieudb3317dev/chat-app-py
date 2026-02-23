# start.ps1 — create venv if missing, activate, install deps, run app with reload
if (-not (Test-Path -Path ".venv")) {
    Write-Host "Creating virtual environment .venv..."
    py -3 -m venv .venv
}

Write-Host "Activating .venv"
. .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing requirements"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Starting uvicorn (reload enabled)"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
