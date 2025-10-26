#!/usr/bin/env bash
set -euo pipefail

# Usage: ./install.sh [venv_dir]
VENV_DIR="${1:-.venv}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Please install Python 3.8+ and retry." >&2
  exit 1
fi

python3 -m venv "$VENV_DIR"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Creating data files if missing..."
[ -f bills.csv ] || touch bills.csv
[ -f bill_counter.txt ] || echo "0" > bill_counter.txt
[ -f companies.csv ] || touch companies.csv
[ -f consultancies.csv ] || touch consultancies.csv

cat > run.sh <<'RUN'
#!/usr/bin/env bash
# Helper to run the app inside the venv
source "$VENV_DIR/bin/activate"
export FLASK_APP=app.py
flask run --host=127.0.0.1 --port=5000
RUN

chmod +x run.sh

cat <<EOF
Installation complete.
Activate the virtualenv and run the app:
  source $VENV_DIR/bin/activate
  ./run.sh

Or run directly:
  FLASK_APP=app.py flask run --host=127.0.0.1 --port=5000
EOF
