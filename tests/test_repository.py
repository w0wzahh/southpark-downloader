from app.db.repository import LibraryRepository
from app.models.entities import Episode

def test_job(tmp_path):
    r=LibraryRepository(tmp_path/"db.sqlite");r.upsert_episode(Episode(None,1,1,"Test"));r.create_job(1,1)
    assert r.get_job(1,1)["status"]=="queued";r.update_job(1,1,status="failed",error="x");assert r.get_job(1,1)["error"]=="x"

def test_source_kind_migration(tmp_path):
    r=LibraryRepository(tmp_path/"db.sqlite");r.upsert_episode(Episode(None,1,2,"Test",source_url="https://x.test/a.m3u8",source_kind="hls"))
    e=r.get_episode(1,2);assert e.source_kind=="hls"
