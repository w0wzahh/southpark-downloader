from urllib.parse import urlparse


def compact_url(value: str, limit: int = 72) -> str:
    if not value:
        return ""
    p = urlparse(value)
    base = f"{p.scheme}://{p.netloc}{p.path}"
    if p.query:
        base += "?…"
    if len(base) <= limit:
        return base
    return base[:limit - 1] + "…"


def test_compact_url_does_not_expose_full_signed_query():
    url = "https://example.test/path/master.m3u8?token=" + "x" * 500
    result = compact_url(url)
    assert len(result) <= 72
    assert "token=" not in result
    assert result.endswith("…")
