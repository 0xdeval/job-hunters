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


def test_find_chromedriver_uses_explicit_environment_path(monkeypatch):
    monkeypatch.setenv("CHROMEDRIVER_PATH", "/opt/chromedriver")
    monkeypatch.setattr(scraper, "which", lambda executable: None)

    assert scraper._find_chromedriver() == "/opt/chromedriver"


def test_find_chromedriver_detects_snap_chromium_driver(monkeypatch):
    monkeypatch.delenv("CHROMEDRIVER_PATH", raising=False)
    monkeypatch.setattr(
        scraper,
        "which",
        lambda executable: "/snap/bin/chromium.chromedriver"
        if executable == "chromium.chromedriver"
        else None,
    )

    assert scraper._find_chromedriver() == "/snap/bin/chromium.chromedriver"


def test_require_chromedriver_raises_clear_install_message(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chromedriver", lambda: None)

    try:
        scraper.require_chromedriver()
    except RuntimeError as exc:
        message = str(exc)
        assert "ChromeDriver is required" in message
        assert "matches the installed Chrome/Chromium major version" in message
        assert "CHROMEDRIVER_PATH=/snap/bin/chromium.chromedriver" in message
    else:
        raise AssertionError("Expected missing driver to fail before launch")


def test_build_chrome_options_uses_linux_server_startup_flags(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: "/snap/bin/chromium")

    options = scraper._build_chrome_options("/tmp/job-hunting-chrome-profile")

    assert options.binary_location == "/snap/bin/chromium"
    assert "--headless=new" in options.arguments
    assert "--no-sandbox" in options.arguments
    assert "--disable-dev-shm-usage" in options.arguments
    assert "--remote-debugging-port=0" in options.arguments
    assert "--user-data-dir=/tmp/job-hunting-chrome-profile" in options.arguments
