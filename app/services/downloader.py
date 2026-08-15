from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
import httpx

class DownloadCancelled(Exception):
    pass

class MediaValidationError(Exception):
    pass

def looks_like_html(data: bytes) -> bool:
    sample = data[:8192].lstrip().lower()
    return (sample.startswith(b"<!doctype html") or sample.startswith(b"<html")
            or b"<html" in sample[:2048] or b"<head" in sample[:2048])

def has_mp4_signature(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(64 * 1024)
    except OSError:
        return False
    return len(head) >= 12 and b"ftyp" in head[:4096]

def find_ffprobe() -> str | None:
    return shutil.which("ffprobe") or shutil.which("ffprobe.exe")

def ffprobe_media(path: Path) -> dict:
    exe = find_ffprobe()
    if not exe:
        return {"available": False}
    proc = subprocess.run(
        [exe, "-v", "error",
         "-show_entries", "format=format_name,format_long_name,duration,size",
         "-show_entries", "stream=index,codec_type,codec_name,width,height,sample_rate,channels",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return {"available": True, "valid": False,
                "error": proc.stderr.strip() or "ffprobe failed"}
    try:
        result = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"available": True, "valid": False, "error": "Invalid ffprobe output"}
    streams = result.get("streams") or []
    return {"available": True, "valid": bool(streams),
            "format": result.get("format") or {}, "streams": streams}

class HttpDownloader:
    def download(self, url, destination, progress=None, should_pause=None,
                 should_cancel=None, checksum=None):
        if not url:
            raise ValueError("No direct media URL is configured.")

        destination = Path(destination)
        part = destination.with_suffix(destination.suffix + ".part")
        existing = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        mode = "ab" if existing else "wb"
        last_time = time.monotonic()
        last_bytes = existing

        with httpx.Client(timeout=60, follow_redirects=True) as client:
            with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                if existing and response.status_code == 200:
                    existing = 0
                    mode = "wb"

                content_type = (response.headers.get("Content-Type") or "").lower()
                if "text/html" in content_type or "text/plain" in content_type:
                    raise MediaValidationError(
                        f"Source returned {content_type}, not media. "
                        "The URL may be a webpage, login page, or error page."
                    )

                length = response.headers.get("Content-Length")
                total = (int(length) + existing if length and response.status_code == 206
                         else int(length) if length else 0)
                current = existing

                with part.open(mode) as out:
                    first_chunk = True
                    for chunk in response.iter_bytes(1024 * 1024):
                        if should_cancel and should_cancel():
                            raise DownloadCancelled()
                        while should_pause and should_pause():
                            if should_cancel and should_cancel():
                                raise DownloadCancelled()
                            time.sleep(.15)
                        if not chunk:
                            continue
                        if first_chunk:
                            first_chunk = False
                            if looks_like_html(chunk):
                                raise MediaValidationError(
                                    "The URL returned HTML instead of media. "
                                    "Use a direct authorized media URL."
                                )
                        out.write(chunk)
                        current += len(chunk)
                        now = time.monotonic()
                        if now - last_time >= .25:
                            speed = (current-last_bytes)/(now-last_time)
                            if progress:
                                progress(current, total, speed)
                            last_time, last_bytes = now, current

                if progress:
                    elapsed = max(.001, time.monotonic()-last_time)
                    progress(current, total, (current-last_bytes)/elapsed)

        if not part.exists() or part.stat().st_size == 0:
            raise MediaValidationError("The server returned an empty file.")

        if destination.suffix.lower() == ".mp4" and not has_mp4_signature(part):
            with part.open("rb") as f:
                head = f.read(8192)
            reason = ("the response is HTML, not an MP4"
                      if looks_like_html(head)
                      else "the file has no MP4/ISO-BMFF ftyp signature")
            raise MediaValidationError(
                f"MP4 validation failed: {reason}. "
                "The source URL probably does not point to the actual MP4."
            )

        probe = ffprobe_media(part)
        if probe.get("available") and not probe.get("valid"):
            raise MediaValidationError(
                "ffprobe found no valid media stream: "
                + str(probe.get("error", "unknown media error"))
            )

        if checksum:
            h = hashlib.sha256()
            with part.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            actual = h.hexdigest().lower()
            if actual != checksum.lower():
                raise MediaValidationError(
                    f"SHA-256 verification failed. Expected {checksum.lower()}, got {actual}."
                )

        part.replace(destination)


def probe_http_source(url: str) -> dict:
    """Inspect a source without saving media. Only fetches a small prefix when needed."""
    from app.services.url_validation import classify_content_type
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "SP-Downloader/3.3"}) as client:
        with client.stream("GET", url, headers={"Range": "bytes=0-8191"}) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            prefix = b""
            for chunk in response.iter_bytes(8192):
                prefix += chunk
                if len(prefix) >= 8192:
                    break
    kind = classify_content_type(content_type, prefix)
    return {"kind": kind, "status": response.status_code, "content_type": content_type,
            "final_url": str(response.url), "prefix": prefix}
