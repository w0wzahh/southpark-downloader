from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from app.services.downloader import MediaValidationError, has_mp4_signature, ffprobe_media


def ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if exe:
            return exe
        raise RuntimeError("FFmpeg is not available. Reinstall requirements.txt or install FFmpeg.")


def _temp_output(destination: Path) -> Path:
    # IMPORTANT: FFmpeg chooses the output muxer from the final extension.
    # '.mp4.part' is not recognized as an MP4 filename, so use '.part.mp4'.
    return destination.with_name(f"{destination.stem}.part{destination.suffix}")


def _verify_output(path: Path, destination: Path, checksum: str | None) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise MediaValidationError("FFmpeg produced an empty media file.")

    if destination.suffix.lower() == ".mp4" and not has_mp4_signature(path):
        raise MediaValidationError("FFmpeg output does not have a valid MP4 container signature.")

    probe = ffprobe_media(path)
    if probe.get("available") and not probe.get("valid"):
        raise MediaValidationError(
            "FFmpeg output contains no valid media stream: "
            + str(probe.get("error", "unknown media error"))
        )

    if checksum:
        import hashlib
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        actual = h.hexdigest().lower()
        if actual != checksum.lower():
            raise MediaValidationError(
                f"SHA-256 verification failed. Expected {checksum.lower()}, got {actual}."
            )


def download_hls(
    url: str,
    destination: Path,
    progress: Callable | None = None,
    should_pause: Callable | None = None,
    should_cancel: Callable | None = None,
    checksum: str | None = None,
) -> None:
    """Download a non-DRM HLS manifest through FFmpeg and remux to MP4.

    The temporary output deliberately ends in '.mp4' so FFmpeg can infer the MP4
    muxer. The final file is only renamed after validation succeeds.
    """
    if not url:
        raise ValueError("No HLS manifest URL was configured.")

    exe = ffmpeg_path()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = _temp_output(destination)

    # A previous failed HLS job can leave a partial container. Starting the HLS
    # mux from the manifest is safer than pretending it is resumable.
    part.unlink(missing_ok=True)

    cmd = [
        exe,
        "-hide_banner",
        "-loglevel", "error",
        "-nostdin",
        "-progress", "pipe:1",
        "-i", url,
        "-map", "0:v:0?",
        "-map", "0:a:0?",
        "-sn",
        "-dn",
        "-c", "copy",
        "-movflags", "+faststart",
        "-f", "mp4",
        "-y", str(part),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    try:
        while proc.poll() is None:
            if should_cancel and should_cancel():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise RuntimeError("Download cancelled.")

            # Pause is deliberately a queue-level pause for HLS. FFmpeg's process
            # is allowed to finish the current job instead of being suspended in a
            # platform-specific way.
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                continue
            line = line.strip()
            if line.startswith("out_time_us=") and progress:
                try:
                    done_us = max(0, int(line.split("=", 1)[1]))
                    progress(done_us, 0, 0.0)
                except ValueError:
                    pass

        _, stderr = proc.communicate(timeout=10)
    except Exception:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        raise

    if proc.returncode != 0:
        err = (stderr or "").strip()[-3000:]
        raise MediaValidationError(
            "FFmpeg could not download the HLS stream. "
            + (err or "Unknown FFmpeg error.")
        )

    _verify_output(part, destination, checksum)
    part.replace(destination)

    if progress:
        final = destination.stat().st_size
        progress(final, final, 0.0)
