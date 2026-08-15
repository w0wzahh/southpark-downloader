# PyInstaller spec for South Park Downloader.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent

hiddenimports = collect_submodules("app")

# PySide6 and imageio-ffmpeg both contain runtime data that should be bundled.
datas = [
    (str(ROOT / "assets"), "assets"),
]
datas += collect_data_files("imageio_ffmpeg")

analysis = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="SouthParkDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "icon.ico"),
)
