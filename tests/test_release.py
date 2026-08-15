from pathlib import Path

from app.version import __version__


def test_release_version():
    assert __version__ == "3.7.0"


def test_readme_has_current_release():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Current release: **3.7.0**" in text
    assert "v3.5" not in text


def test_help_does_not_reference_old_ui_version():
    text = Path("app/gui/main_window.py").read_text(encoding="utf-8")
    assert "Why v3.5" not in text
