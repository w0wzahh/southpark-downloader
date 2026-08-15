from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class Season:
    number: int
    title: str = ""
    episode_count: int = 0
    downloaded_count: int = 0


@dataclass(slots=True)
class Episode:
    id: int | None
    season: int
    number: int
    title: str
    source_url: str = ""
    extension: str = "mp4"
    sha256: str | None = None
    downloaded: bool = False
    filename: str = ""
    airdate: str = ""
    runtime: int | None = None
    summary: str = ""
    image_url: str = ""
    page_url: str = ""
    source_kind: str = "unknown"
