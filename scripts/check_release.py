from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN = {
    ".venv",
    "data/library.db",
    "downloads",
    "build",
    "dist",
    ".pytest_cache",
}
REQUIRED = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "assets/icon.ico",
    "assets/icon.png",
    "packaging/SouthParkDownloader.spec",
    "packaging/SouthParkDownloader.iss",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
]

missing = [p for p in REQUIRED if not (ROOT / p).exists()]
if missing:
    raise SystemExit("Missing release files:\n- " + "\n- ".join(missing))

bad = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if any(rel == item or rel.startswith(item.rstrip("/") + "/") for item in FORBIDDEN):
        if rel.endswith("/.gitkeep") or rel == ".gitkeep":
            continue
        bad.append(rel)
    if p.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm", ".part"}:
        bad.append(rel)

if bad:
    raise SystemExit("Local/runtime files would be included in the release:\n- " + "\n- ".join(sorted(set(bad))))

print("Release tree looks clean.")
