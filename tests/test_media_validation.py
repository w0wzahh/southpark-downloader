from app.services.downloader import has_mp4_signature, looks_like_html

def test_html_detection():
    assert looks_like_html(b"<!doctype html><html><body>Error</body></html>")

def test_mp4_signature(tmp_path):
    p = tmp_path / "x.mp4"
    p.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2")
    assert has_mp4_signature(p)

def test_invalid_mp4(tmp_path):
    p = tmp_path / "x.mp4"
    p.write_bytes(b"not a real mp4")
    assert not has_mp4_signature(p)
