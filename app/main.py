from __future__ import annotations
import argparse
import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from app.config.settings import Settings
from app.version import __version__
from app.db.repository import LibraryRepository
from app.services.library import LibraryService
from app.gui.main_window import MainWindow


def main():
    p = argparse.ArgumentParser(description=f"South Park Downloader v{__version__}")
    p.add_argument("--cli", action="store_true")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("sync")
    sub.add_parser("list")
    sub.add_parser("queue")
    sub.add_parser("scan")
    ds = sub.add_parser("download-season")
    ds.add_argument("season", type=int)
    de = sub.add_parser("download-episode")
    de.add_argument("season", type=int)
    de.add_argument("episode", type=int)
    args = p.parse_args()

    settings = Settings.from_root(Path(__file__).resolve().parents[1])
    settings.ensure()
    repo = LibraryRepository(settings.database_path)
    service = LibraryService(repo, settings)

    if args.cli:
        if args.command == "sync":
            print(f"Synced {service.sync_tvmaze()} episodes.")
        elif args.command == "list":
            for s in repo.list_seasons():
                print(f"Season {s.number:02d}: {s.downloaded_count}/{s.episode_count}")
        elif args.command == "queue":
            for j in repo.list_jobs():
                print(f"{j['id']:>4} S{j['season']:02d}E{j['episode']:02d} {j['status']}")
        elif args.command == "scan":
            print(f"Library scan: {service.scan_library()} file(s) marked downloaded.")
        elif args.command == "download-season":
            print(f"Queued {service.queue_season(args.season)} job(s).")
        elif args.command == "download-episode":
            print(f"Queued: {service.queue_episode(args.season, args.episode)}")
        else:
            p.print_help()
        service.shutdown()
        return

    app = QApplication(sys.argv)
    app.setApplicationName("South Park Downloader")
    app.setApplicationDisplayName("South Park Downloader")
    app.setOrganizationName("South Park Downloader")
    app.setOrganizationDomain("southpark-downloader.local")
    icon_path = Path(__file__).resolve().parents[1] / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyle("Fusion")
    window = MainWindow(service)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
