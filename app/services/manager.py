from __future__ import annotations
from dataclasses import dataclass
from queue import Queue, Empty
from threading import Event, Lock, Thread
import time
from app.services.downloader import HttpDownloader, DownloadCancelled
from app.services.hls import download_hls
from app.services.filesystem import path_for

@dataclass
class Job:
    season:int
    episode:int

class DownloadManager:
    def __init__(self,repo,root,concurrency=2,on_progress=None,on_state=None):
        self.repo=repo; self.root=root; self.concurrency=max(1,int(concurrency))
        self.on_progress=on_progress; self.on_state=on_state
        self.queue=Queue(); self.stop=Event(); self.pause_event=Event(); self.cancelled=set(); self.lock=Lock(); self.threads=[]
        self.repo.reset_stale_jobs()
        for i in range(self.concurrency):
            t=Thread(target=self.worker,daemon=True,name=f"download-{i+1}"); t.start(); self.threads.append(t)

    def add(self,e):
        job=self.repo.get_job(e.season,e.number)
        if job and job["status"] in {"queued","downloading"}:
            return False
        self.repo.create_job(e.season,e.number); self.queue.put(Job(e.season,e.number)); return True

    def worker(self):
        while not self.stop.is_set():
            try: job=self.queue.get(timeout=.2)
            except Empty: continue
            if job is None:
                self.queue.task_done(); return
            e=self.repo.get_episode(job.season,job.episode); key=(job.season,job.episode)
            with self.lock:
                was_cancelled = key in self.cancelled
                if was_cancelled:
                    self.cancelled.discard(key)
            if was_cancelled:
                self.repo.update_job(*key,status="cancelled",speed=0)
                self.queue.task_done(); continue
            if self.pause_event.is_set():
                self.queue.put(job)
                self.queue.task_done()
                time.sleep(0.15)
                continue
            if not e or e.downloaded:
                self.queue.task_done(); continue
            if not e.source_url:
                self._fail(e,"No media source configured."); self.queue.task_done(); continue
            self.repo.update_job(*key,status="downloading",error="")
            if self.on_state:self.on_state(e,"downloading","")
            try:
                dest=path_for(self.root,e)
                def progress(done,total,speed):
                    self.repo.update_job(*key,bytes_done=int(done),bytes_total=int(total or 0),speed=float(speed))
                    if self.on_progress:self.on_progress(e,int(done),int(total or 0),float(speed))
                def cancelled(): return key in self.cancelled or self.stop.is_set()
                if e.source_kind == "hls" or e.source_url.lower().split("?",1)[0].endswith(".m3u8"):
                    download_hls(e.source_url,dest,progress,should_cancel=cancelled,checksum=e.sha256)
                elif e.source_kind == "dash" or e.source_url.lower().split("?",1)[0].endswith(".mpd"):
                    raise RuntimeError("DASH manifest detected. v3.3 does not download DASH yet. Use an authorized direct/HLS source.")
                else:
                    HttpDownloader().download(e.source_url,dest,progress,
                        should_pause=lambda:self.pause_event.is_set(),should_cancel=cancelled,checksum=e.sha256)
                self.repo.set_downloaded(*key,True,str(dest))
                size=dest.stat().st_size
                self.repo.update_job(*key,status="completed",bytes_done=size,bytes_total=size,speed=0,error="")
                if self.on_state:self.on_state(e,"completed","")
            except DownloadCancelled:
                self.repo.update_job(*key,status="cancelled",speed=0)
                if self.on_state:self.on_state(e,"cancelled","")
            except Exception as exc:
                self.repo.update_job(*key,status="failed",error=str(exc),speed=0)
                if self.on_state:self.on_state(e,"failed",str(exc))
            finally:
                with self.lock:self.cancelled.discard(key)
                self.queue.task_done()

    def _fail(self,e,error):
        self.repo.update_job(e.season,e.number,status="failed",error=error)
        if self.on_state:self.on_state(e,"failed",error)
    def pause(self):self.pause_event.set()
    def resume(self):self.pause_event.clear()
    def cancel(self,e):
        key=(e.season,e.number)
        with self.lock:self.cancelled.add(key)
        self.repo.update_job(e.season,e.number,status="cancelled")
    def retry(self,e):
        with self.lock:self.cancelled.discard((e.season,e.number))
        self.add(e)
    def shutdown(self):
        self.stop.set()
        for _ in self.threads:self.queue.put(None)
        for t in self.threads:t.join(timeout=2)
