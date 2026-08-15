from pathlib import Path
from app.services.hls import _temp_output


def test_hls_temp_file_keeps_media_extension(tmp_path):
    destination = tmp_path / "Season 05" / "S05E14 - Test.mp4"
    assert _temp_output(destination).name == "S05E14 - Test.part.mp4"
    assert _temp_output(destination).suffix == ".mp4"
