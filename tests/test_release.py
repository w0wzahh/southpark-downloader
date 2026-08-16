from pathlib import Path

from app.version import __version__


def test_release_version():
    assert __version__ == "3.7.3"


def test_readme_has_current_release():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Current release: 3.7.3" in text