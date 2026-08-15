from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass(frozen=True)
class URLCheck:
    valid: bool
    kind: str
    message: str

WEBPAGE_HOSTS = {"southparkstudios.com", "www.southparkstudios.com"}
WEBPAGE_PATH_MARKERS = ("/episodes/", "/shows/", "/videos/")


def classify_source_url(value: str) -> URLCheck:
    value = (value or "").strip()
    if not value:
        return URLCheck(False, "empty", "No source URL was provided.")
    p = urlparse(value)
    if p.scheme not in {"http", "https"} or not p.netloc:
        return URLCheck(False, "invalid", "URL must be a complete http:// or https:// URL.")
    host = p.netloc.lower().split(":", 1)[0]
    path = p.path.lower()
    if host in WEBPAGE_HOSTS and any(marker in path for marker in WEBPAGE_PATH_MARKERS):
        return URLCheck(False, "episode_page",
            "This is an episode webpage, not a direct media source. Store it as the episode page URL.")
    if path.endswith(".m3u8") or ".m3u8" in path or "m3u8" in p.query.lower():
        return URLCheck(True, "hls", "HLS manifest URL. It will be probed and downloaded through FFmpeg if supported.")
    if path.endswith(".mpd") or ".mpd" in path:
        return URLCheck(True, "dash", "DASH manifest URL. v3.3 identifies it but does not download DASH yet.")
    if path.endswith((".mp4", ".m4v", ".webm", ".mkv", ".mov", ".ts")):
        return URLCheck(True, "direct", "Direct media-looking URL. The response will still be validated.")
    return URLCheck(True, "unknown", "Source type is unknown. Use Probe Source before downloading.")


def classify_content_type(content_type: str, body: bytes = b"") -> str:
    ct = (content_type or "").lower()
    sample = body[:8192].lstrip().lower()
    if "text/html" in ct or sample.startswith(b"<!doctype html") or sample.startswith(b"<html"):
        return "webpage"
    if "mpegurl" in ct or "vnd.apple.mpegurl" in ct or b"#extm3u" in sample[:4096]:
        return "hls"
    if "dash+xml" in ct or b"<mpd" in sample[:4096]:
        return "dash"
    if ct.startswith("video/"):
        return "direct"
    return "unknown"
