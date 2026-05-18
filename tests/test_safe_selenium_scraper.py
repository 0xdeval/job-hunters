from job_hunting.tools import safe_selenium_scraper as scraper


def test_find_chrome_binary_uses_explicit_environment_path(monkeypatch):
    monkeypatch.setenv("CHROME_BINARY", "/opt/chrome/chrome")
    monkeypatch.setattr(scraper, "which", lambda executable: None)

    assert scraper._find_chrome_binary() == "/opt/chrome/chrome"


def test_find_chrome_binary_detects_linux_chromium(monkeypatch):
    monkeypatch.delenv("CHROME_BINARY", raising=False)
    monkeypatch.setattr(
        scraper,
        "which",
        lambda executable: "/usr/bin/chromium"
        if executable == "chromium"
        else None,
    )

    assert scraper._find_chrome_binary() == "/usr/bin/chromium"


def test_find_chrome_binary_falls_back_to_common_file_paths(monkeypatch):
    monkeypatch.delenv("CHROME_BINARY", raising=False)
    monkeypatch.setattr(scraper, "which", lambda executable: None)

    class _Path:
        def __init__(self, value: str):
            self.value = value

        def exists(self) -> bool:
            return self.value == "/usr/bin/chromium-browser"

        def __str__(self) -> str:
            return self.value

    monkeypatch.setattr(scraper, "Path", _Path)

    assert scraper._find_chrome_binary() == "/usr/bin/chromium-browser"


def test_require_chrome_binary_returns_detected_path(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: "/usr/bin/chromium")

    assert scraper.require_chrome_binary() == "/usr/bin/chromium"


def test_require_chrome_binary_raises_clear_install_message(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: None)

    try:
        scraper.require_chrome_binary()
    except RuntimeError as exc:
        message = str(exc)
        assert "Chrome or Chromium is required" in message
        assert "sudo apt-get install -y chromium" in message
        assert "CHROME_BINARY=/path/to/chrome" in message
    else:
        raise AssertionError("Expected missing browser to fail before launch")
