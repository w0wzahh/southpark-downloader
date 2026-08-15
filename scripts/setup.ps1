$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path data,downloads,cache | Out-Null
Write-Host "Setup complete. Run: .\.venv\Scripts\python.exe run.py"
