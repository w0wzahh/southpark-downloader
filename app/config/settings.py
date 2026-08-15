from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    root: Path
    data_dir: Path
    download_dir: Path
    database_path: Path
    concurrency: int = 2

    @classmethod
    def from_root(cls, root: Path):
        return cls(root, root/"data", root/"downloads", root/"data"/"library.db")

    def ensure(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
