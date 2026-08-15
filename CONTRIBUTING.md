# Contributing

Thanks for taking the time to improve South Park Downloader.

## Development setup

Python 3.11 or newer is supported. A normal development setup is:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest
```

Then run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py
```

## Pull requests

Keep pull requests focused. Explain the user-visible change, include tests for behavior that can be tested automatically, and avoid committing local databases or downloaded media.

## Source handling

Do not add code intended to bypass DRM, authentication, paywalls, geo restrictions, or other access controls. The project is designed to work with media sources the user is authorized to access.

## Reporting bugs

Use the bug report template and include the application version, operating system, reproduction steps, and the relevant error. Remove cookies, access tokens, signed URLs, and other private data before posting logs.
