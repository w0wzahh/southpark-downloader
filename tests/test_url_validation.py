from app.services.url_validation import classify_source_url, classify_content_type

def test_southpark_episode_page_is_not_source():
    result=classify_source_url("https://www.southparkstudios.com/episodes/8gq1cu/south-park-butters-very-own-episode-season-5-ep-14")
    assert not result.valid and result.kind=="episode_page"

def test_non_http_url_rejected():
    assert not classify_source_url("not-a-url").valid

def test_hls_manifest_detected():
    result=classify_source_url("https://cdn.example.test/master.m3u8?token=x")
    assert result.valid and result.kind=="hls"

def test_m3u8_content_detected():
    assert classify_content_type("application/vnd.apple.mpegurl", b"#EXTM3U\n#EXT-X-VERSION:3")=="hls"

def test_html_content_detected():
    assert classify_content_type("text/html", b"<!doctype html>")=="webpage"
