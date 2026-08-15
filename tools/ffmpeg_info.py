from app.services.hls import ffmpeg_path
import subprocess

try:
    exe=ffmpeg_path()
    print(exe)
    p=subprocess.run([exe,"-version"],capture_output=True,text=True,timeout=10)
    print(p.stdout.splitlines()[0] if p.stdout else p.stderr.splitlines()[0])
except Exception as e:
    print(f"FFmpeg unavailable: {e}")
    raise SystemExit(1)
