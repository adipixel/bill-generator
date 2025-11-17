Installer instructions

This project includes two installer scripts to set up a local environment and run the Flask app:

1) install.sh (macOS / Linux)

  ./install.sh

This creates a virtual environment (default: .venv), installs dependencies from requirements.txt, creates any missing CSV files, and writes a small run.sh helper.

2) install.ps1 (Windows PowerShell)

  .\install.ps1

This creates a venv folder (default: .venv), installs dependencies, and creates missing CSV files. Run the app with PowerShell as described after installation.

Building standalone binaries (optional)

Use PyInstaller to build single-file executables. Recommended approach: configure GitHub Actions to build on each platform and upload artifacts. See .github/workflows/build.yml for an example.

Notes
- Python 3.8+ is recommended.
- If you add new Python dependencies, update requirements.txt and re-run the installer.
