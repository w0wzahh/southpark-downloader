from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.downloader import has_mp4_signature, looks_like_html, ffprobe_media

parser = argparse.ArgumentParser(description="Diagnose a downloaded media file")
parser.add_argument("file")
args = parser.parse_args()
path = Path(args.file)

if not path.exists():
    print(f"File not found: {path}")
    raise SystemExit(1)

print(f"File: {path}")
print(f"Size: {path.stat().st_size:,} bytes")
print(f"Extension: {path.suffix or '(none)'}")

with path.open("rb") as f:
    head = f.read(8192)

print(f"Looks like HTML: {looks_like_html(head)}")
if path.suffix.lower() == ".mp4":
    print(f"MP4 ftyp signature: {has_mp4_signature(path)}")

probe = ffprobe_media(path)
if not probe.get("available"):
    print("ffprobe: not installed / not on PATH")
else:
    print(json.dumps(probe, indent=2))
