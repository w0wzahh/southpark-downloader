from __future__ import annotations
import re
from pathlib import Path
from app.models.entities import Episode
BAD=re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def safe_name(value):
    return BAD.sub("_",value).strip().rstrip(".") or "Untitled"

def path_for(root,episode):
    folder=root/f"Season {episode.season:02d}"
    folder.mkdir(parents=True,exist_ok=True)
    ext=safe_name(episode.extension.lstrip(".")) or "mp4"
    return folder/f"S{episode.season:02d}E{episode.number:02d} - {safe_name(episode.title)}.{ext}"
