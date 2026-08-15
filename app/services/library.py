from __future__ import annotations
import csv
from pathlib import Path
from app.providers.tvmaze import TVMazeProvider
from app.services.filesystem import path_for
from app.services.manager import DownloadManager
from app.services.url_validation import classify_source_url
from app.services.downloader import probe_http_source

class LibraryService:
    def __init__(self, repo, settings):
        self.repo=repo; self.settings=settings
        self.progress_callback=None; self.state_callback=None
        self.manager=DownloadManager(repo,settings.download_dir,settings.concurrency,self._progress,self._state)
    def _progress(self,*args):
        if self.progress_callback:self.progress_callback(*args)
    def _state(self,*args):
        if self.state_callback:self.state_callback(*args)

    def sync_tvmaze(self):
        p=TVMazeProvider()
        try:
            show,seasons,episodes=p.fetch()
            for s in seasons:self.repo.upsert_season(s)
            for e in episodes:
                old=self.repo.get_episode(e.season,e.number)
                if old:
                    e.source_url=old.source_url; e.page_url=old.page_url; e.source_kind=old.source_kind
                    e.extension=old.extension; e.sha256=old.sha256; e.downloaded=old.downloaded; e.filename=old.filename
                self.repo.upsert_episode(e)
            return len(episodes)
        finally:p.close()

    def queue_episode(self,season,number):
        e=self.repo.get_episode(season,number)
        if not e: raise ValueError("Episode not found.")
        if not e.source_url: raise ValueError("Episode has no media source. Save a direct media or HLS manifest URL first.")
        self.manager.add(e); return f"S{season:02d}E{number:02d}"

    def queue_season(self,season):
        n=0
        for e in self.repo.list_episodes(season):
            if not e.downloaded and e.source_url:self.manager.add(e);n+=1
        return n
    def queue_all(self): return sum(self.queue_season(s.number) for s in self.repo.list_seasons())

    def save_source(self,season,number,url,extension,sha256,page_url="",source_kind="unknown"):
        check=classify_source_url(url)
        if not check.valid: raise ValueError(check.message)
        kind=source_kind or check.kind
        self.repo.set_source(season,number,url,extension.lstrip(".") or "mp4",sha256 or None,page_url.strip(),kind)

    def probe_source(self,url):
        check=classify_source_url(url)
        if not check.valid: return {"valid":False,"kind":check.kind,"message":check.message}
        try:
            info=probe_http_source(url)
            return {"valid":True,**{k:v for k,v in info.items() if k!="prefix"},
                    "message":f"Detected {info['kind']} source ({info['content_type'] or 'no Content-Type'})."}
        except Exception as exc:
            return {"valid":False,"kind":check.kind,"message":f"Probe failed: {exc}"}

    def import_sources(self,path):
        count=0
        with open(path,newline="",encoding="utf-8-sig") as f:
            rows=csv.reader(f)
            for row in rows:
                if not row or row[0].strip().lower()=="season":continue
                if len(row)<3:continue
                season,episode=int(row[0]),int(row[1])
                ext=row[3].strip() if len(row)>3 and row[3].strip() else "mp4"
                sha=row[4].strip() if len(row)>4 else ""
                page=row[5].strip() if len(row)>5 else ""
                kind=row[6].strip() if len(row)>6 else "unknown"
                self.save_source(season,episode,row[2].strip(),ext,sha,page,kind);count+=1
        return count

    def scan_library(self):
        count=0
        for s in self.repo.list_seasons():
            for e in self.repo.list_episodes(s.number):
                p=path_for(self.settings.download_dir,e)
                if p.exists():
                    self.repo.set_downloaded(e.season,e.number,True,str(p));count+=1
        return count
    def shutdown(self):self.manager.shutdown()
