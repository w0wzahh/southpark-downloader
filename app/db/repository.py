from __future__ import annotations
import sqlite3
from pathlib import Path
from app.models.entities import Episode, Season


class LibraryRepository:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def initialize(self):
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS seasons(
                number INTEGER PRIMARY KEY,
                title TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS episodes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER NOT NULL,
                number INTEGER NOT NULL,
                title TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                page_url TEXT NOT NULL DEFAULT '',
                extension TEXT NOT NULL DEFAULT 'mp4',
                sha256 TEXT,
                downloaded INTEGER NOT NULL DEFAULT 0,
                filename TEXT NOT NULL DEFAULT '',
                airdate TEXT NOT NULL DEFAULT '',
                runtime INTEGER,
                summary TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                UNIQUE(season, number),
                FOREIGN KEY(season) REFERENCES seasons(number)
            );
            CREATE TABLE IF NOT EXISTS download_jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER NOT NULL,
                episode INTEGER NOT NULL,
                status TEXT NOT NULL,
                bytes_done INTEGER NOT NULL DEFAULT 0,
                bytes_total INTEGER NOT NULL DEFAULT 0,
                speed REAL NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(season, episode)
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
            # Lightweight migration for databases created by v2/v3/v3.1.
            cols = {r[1] for r in db.execute("PRAGMA table_info(episodes)").fetchall()}
            if "page_url" not in cols:
                db.execute("ALTER TABLE episodes ADD COLUMN page_url TEXT NOT NULL DEFAULT ''")
            if "source_kind" not in cols:
                db.execute("ALTER TABLE episodes ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'unknown'")

    def upsert_season(self, s):
        with self.connect() as db:
            db.execute("""INSERT INTO seasons(number,title) VALUES(?,?)
                ON CONFLICT(number) DO UPDATE SET title=excluded.title""",
                (s.number, s.title))

    def upsert_episode(self, e):
        self.upsert_season(Season(e.season))
        with self.connect() as db:
            db.execute("""INSERT INTO episodes(
                season,number,title,source_url,page_url,source_kind,extension,sha256,downloaded,
                filename,airdate,runtime,summary,image_url)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(season,number) DO UPDATE SET
                title=excluded.title,airdate=excluded.airdate,runtime=excluded.runtime,
                summary=excluded.summary,image_url=excluded.image_url""",
                (e.season,e.number,e.title,e.source_url,getattr(e, "page_url", ""),getattr(e, "source_kind", "unknown"),e.extension,e.sha256,
                 int(e.downloaded),e.filename,e.airdate,e.runtime,e.summary,e.image_url))

    def set_source(self, season, number, url, extension, sha256, page_url=None, source_kind="unknown"):
        with self.connect() as db:
            if page_url is None:
                db.execute("""UPDATE episodes SET source_url=?,extension=?,sha256=?,source_kind=?
                             WHERE season=? AND number=?""",
                           (url,extension,sha256,source_kind,season,number))
            else:
                db.execute("""UPDATE episodes SET source_url=?,page_url=?,extension=?,sha256=?,source_kind=?
                             WHERE season=? AND number=?""",
                           (url,page_url,extension,sha256,source_kind,season,number))

    def set_downloaded(self, season, number, value, filename=""):
        with self.connect() as db:
            db.execute("""UPDATE episodes SET downloaded=?,filename=?
                         WHERE season=? AND number=?""",
                       (int(value),filename,season,number))

    def get_episode(self, season, number):
        with self.connect() as db:
            r = db.execute("SELECT * FROM episodes WHERE season=? AND number=?",
                           (season,number)).fetchone()
        return self._episode(r) if r else None

    def list_episodes(self, season):
        with self.connect() as db:
            rows=db.execute("SELECT * FROM episodes WHERE season=? ORDER BY number",
                            (season,)).fetchall()
        return [self._episode(r) for r in rows]

    def list_seasons(self):
        with self.connect() as db:
            rows=db.execute("""SELECT s.number,s.title,COUNT(e.id) episode_count,
                COALESCE(SUM(e.downloaded),0) downloaded_count
                FROM seasons s LEFT JOIN episodes e ON e.season=s.number
                GROUP BY s.number ORDER BY s.number""").fetchall()
        return [Season(r["number"],r["title"],r["episode_count"],r["downloaded_count"])
                for r in rows]

    def create_job(self, season, episode):
        with self.connect() as db:
            db.execute("""INSERT INTO download_jobs(season,episode,status)
                VALUES(?,?, 'queued')
                ON CONFLICT(season,episode) DO UPDATE SET
                status=CASE WHEN download_jobs.status='completed'
                THEN 'completed' ELSE 'queued' END,
                error='',updated_at=CURRENT_TIMESTAMP""",(season,episode))

    def update_job(self, season, episode, **fields):
        allowed={"status","bytes_done","bytes_total","speed","error"}
        fields={k:v for k,v in fields.items() if k in allowed}
        if not fields:return
        fields["updated_at"]="CURRENT_TIMESTAMP"
        assignments=[]
        values=[]
        for k,v in fields.items():
            if v == "CURRENT_TIMESTAMP": assignments.append(f"{k}=CURRENT_TIMESTAMP")
            else:
                assignments.append(f"{k}=?"); values.append(v)
        values += [season,episode]
        with self.connect() as db:
            db.execute(f"""UPDATE download_jobs SET {','.join(assignments)}
                         WHERE season=? AND episode=?""",values)

    def list_jobs(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM download_jobs ORDER BY id DESC").fetchall()]

    def get_job(self, season, episode):
        with self.connect() as db:
            r=db.execute("SELECT * FROM download_jobs WHERE season=? AND episode=?",
                         (season,episode)).fetchone()
        return dict(r) if r else None

    def clear_completed_jobs(self):
        with self.connect() as db:
            db.execute("DELETE FROM download_jobs WHERE status='completed'")

    def reset_stale_jobs(self):
        with self.connect() as db:
            db.execute("""UPDATE download_jobs SET status='queued',error=''
                         WHERE status='downloading'""")

    def set_setting(self,key,value):
        with self.connect() as db:
            db.execute("""INSERT INTO settings(key,value) VALUES(?,?)
                         ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                       (key,str(value)))

    def get_setting(self,key,default=None):
        with self.connect() as db:
            r=db.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return r["value"] if r else default

    @staticmethod
    def _episode(r):
        return Episode(r["id"],r["season"],r["number"],r["title"],r["source_url"],
            r["extension"],r["sha256"],bool(r["downloaded"]),r["filename"],
            r["airdate"],r["runtime"],r["summary"],r["image_url"],
            r["page_url"] if "page_url" in r.keys() else "",
            r["source_kind"] if "source_kind" in r.keys() else "unknown")
