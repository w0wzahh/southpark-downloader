# South Park Downloader

A Windows-friendly desktop application for organizing episode metadata, managing media sources, downloading authorized streams, and keeping a clean season-based local library.

South Park Downloader is an independent project. It is not affiliated with, endorsed by, or sponsored by Paramount, South Park Studios, or the creators of South Park. South Park and related names are trademarks of their respective owners.

## What it does

- Browse seasons and episode metadata in a desktop UI.
- Keep an episode's webpage separate from its actual media source.
- Accept direct media URLs and HLS (`.m3u8`) manifests.
- Probe a source before saving it.
- Use FFmpeg for HLS downloads instead of handling stream segments manually.
- Validate media before moving it into the library.
- Keep a persistent SQLite download queue.
- Queue an episode, a full season, or all missing episodes with configured sources.
- Retry failed jobs, cancel jobs, and pause/resume new queue work.
- Scan the library and reconcile files already on disk.
- Import source information from CSV.
- Organize files as `Season XX/SXXEXX - Episode Title.mp4`.
- Use the same interface in dark or light mode.
- Run from source or from the Windows installer/portable build.

## Screenshots

### Download queue

![Download queue](docs/screenshots/download-queue.png)

### Help and workflow

![Help and workflow](docs/screenshots/how-it-works.png)

## Installation

### Windows installer

Download the latest `SouthParkDownloader-Setup-*.exe` from the repository's Releases page and run it. The installer creates a normal Windows application entry and can create a desktop shortcut.

The portable release is also available as a ZIP if you do not want an installed copy.

### Run from source

Requirements:

- Python 3.11 or newer
- Windows, macOS, or Linux
- Internet access for metadata and remote media sources

FFmpeg is supplied through `imageio-ffmpeg`, so a separate system-wide FFmpeg installation is normally unnecessary.

#### Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Or use the setup script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
.\.venv\Scripts\python.exe run.py
```

#### Linux / macOS

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python run.py
```

## First run

1. Start the application.
2. Select **Sync Metadata** to populate the library.
3. Pick a season and episode.
4. Keep the episode webpage in **Episode page**. This is only a reference URL.
5. Put an authorized direct media URL or HLS manifest in **Media source**.
6. Select **Probe Source**.
7. Select **Save Source**.
8. Queue the episode, season, or all configured missing episodes.
9. Watch progress in **Download Queue**.

## Episode pages and media sources

An episode page such as:

```text
https://www.southparkstudios.com/episodes/...
```

is not an MP4 download URL. Modern players may request a separate HLS manifest such as:

```text
https://example.invalid/path/master.m3u8
```

When an authorized HLS manifest is supplied, the application passes it to FFmpeg. FFmpeg handles the playlist and segments and writes the compatible media to an MP4 file.

You do not need to download or concatenate individual `segment-*` requests yourself.

## Access boundaries

The application is intended for media sources you are authorized to access and download.

It does not attempt to:

- bypass DRM;
- extract or recover DRM keys;
- defeat authentication or access controls;
- circumvent paywalls or geo restrictions;
- turn protected playback into an unauthorized download.

If a source requires a protected playback mechanism the application cannot use, the job is reported as failed.

## Library layout

Downloads are organized automatically:

```text
downloads/
├── Season 01/
│   ├── S01E01 - Episode Title.mp4
│   └── S01E02 - Episode Title.mp4
├── Season 02/
│   └── S02E01 - Episode Title.mp4
└── ...
```

HLS downloads use a temporary `.part.mp4` file so FFmpeg can select the MP4 muxer. The temporary file is validated before it becomes the final library file.

## CSV source import

The source importer accepts:

```text
season,episode,direct_media_url,extension,sha256,episode_page_url,source_kind
```

Example:

```text
1,1,https://authorized.example/video.mp4,mp4,,https://authorized.example/episode/1,direct
1,2,https://authorized.example/master.m3u8,mp4,,https://authorized.example/episode/2,hls
```

`source_kind` may be `direct`, `hls`, `dash`, or `unknown`. HLS is supported by the downloader. DASH can be identified and stored but is not currently downloaded.

## Command line

The GUI is the main interface, but common operations are available from the command line:

```powershell
.\.venv\Scripts\python.exe run.py --cli sync
.\.venv\Scripts\python.exe run.py --cli list
.\.venv\Scripts\python.exe run.py --cli queue
.\.venv\Scripts\python.exe run.py --cli scan
.\.venv\Scripts\python.exe run.py --cli download-season 5
.\.venv\Scripts\python.exe run.py --cli download-episode 5 14
```

## Diagnostics

Inspect a media file:

```powershell
.\.venv\Scripts\python.exe tools\diagnose_media.py "downloads\Season 05\S05E14 - Episode Title.mp4"
```

Check the bundled FFmpeg:

```powershell
.\.venv\Scripts\python.exe tools\ffmpeg_info.py
```

## Building a Windows release

The repository contains a PyInstaller build and an Inno Setup installer definition.

On Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

If Inno Setup 6 is installed, the script also produces the installer. Without it, the portable PyInstaller build is still produced under `dist\SouthParkDownloader`.

Tagged releases are built automatically by GitHub Actions. Push a tag such as `v3.7.1` to create the release artifacts.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q
```

Pull requests and bug reports are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Repository layout

```text
app/                    Application code
assets/                 Application icon and branding
cache/                  Runtime cache
 data/                  Local SQLite database (ignored by Git)
downloads/              Managed media library (ignored by Git)
docs/screenshots/       Repository screenshots
packaging/              PyInstaller and Inno Setup definitions
scripts/                Setup and release scripts
tests/                  Automated tests
tools/                  Diagnostics
.github/                CI, release automation, and issue templates
run.py                  Source entry point
```

## Versioning

Releases use semantic versioning (`MAJOR.MINOR.PATCH`). GitHub Actions builds release artifacts when a `v*.*.*` tag is pushed.

## License

Released under the [MIT License](LICENSE).

## Current release

Current release: **3.7.0**

## Disclaimer

This project is an independent software project. Users are responsible for complying with the terms, laws, licenses, and access restrictions that apply to media they access or download.
