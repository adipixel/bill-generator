Param(
  [string]$VenvFolder = ".venv"
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python is required. Please install Python 3.8+ and retry."
  exit 1
}

python -m venv $VenvFolder
& "$VenvFolder\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .\bills.csv)) { New-Item -Path .\bills.csv -ItemType File | Out-Null }
if (-not (Test-Path .\bill_counter.txt)) { "0" | Out-File -Encoding utf8 .\bill_counter.txt }
if (-not (Test-Path .\companies.csv)) { New-Item -Path .\companies.csv -ItemType File | Out-Null }
if (-not (Test-Path .\consultancies.csv)) { New-Item -Path .\consultancies.csv -ItemType File | Out-Null }

"Installation complete. To run:"
"  & $VenvFolder\Scripts\Activate.ps1"
"  set FLASK_APP=app.py; flask run --host=127.0.0.1 --port=5000"
