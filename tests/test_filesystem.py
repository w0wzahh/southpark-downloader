from app.models.entities import Episode
from app.services.filesystem import path_for,safe_name

def test_safe_name():
    assert safe_name("a:/b?")=="a__b_"

def test_path(tmp_path):
    p=path_for(tmp_path,Episode(None,1,2,"Test"))
    assert p.name=="S01E02 - Test.mp4"
    assert p.parent.name=="Season 01"
