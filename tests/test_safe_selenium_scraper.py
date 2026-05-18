from job_hunting.tools import safe_selenium_scraper as scraper
from selenium.common.exceptions import SessionNotCreatedException


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


def test_find_chromedriver_prefers_snap_driver_for_snap_chromium(monkeypatch):
    monkeypatch.delenv("CHROMEDRIVER_PATH", raising=False)
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: "/snap/bin/chromium")
    monkeypatch.setattr(
        scraper,
        "which",
        lambda executable: {
            "chromedriver": "/usr/bin/chromedriver",
            "chromium.chromedriver": "/snap/bin/chromium.chromedriver",
        }.get(executable),
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
    assert any(argument.startswith("--user-agent=") for argument in options.arguments)


def test_run_retries_with_legacy_headless_when_chrome_exits(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(scraper, "_find_chromedriver", lambda: "/usr/bin/chromedriver")
    monkeypatch.setattr(
        scraper,
        "_find_chromedriver_candidates",
        lambda: ["/usr/bin/chromedriver"],
    )
    monkeypatch.setattr(scraper.time, "sleep", lambda seconds: None)

    created_options = []

    class _Element:
        text = "Vacancy"

        def get_attribute(self, name):
            return "https://example.com/jobs/1" if name == "href" else None

    class _Driver:
        def get(self, website_url):
            self.website_url = website_url

        def execute_script(self, script):
            self.script = script

        def find_element(self, by, value):
            return _Element()

        def find_elements(self, by, value):
            return [_Element()]

        def quit(self):
            self.closed = True

    def fake_chrome(service, options):
        created_options.append(options.arguments)
        if len(created_options) == 1:
            raise SessionNotCreatedException("Chrome instance exited")
        return _Driver()

    monkeypatch.setattr(scraper.webdriver, "Chrome", fake_chrome)
    monkeypatch.setattr(
        scraper.WebDriverWait,
        "until",
        lambda self, condition: True,
    )

    result = scraper.SafeSeleniumScrapingTool()._run("https://example.com/jobs")

    assert "Vacancy" in result
    assert "--headless=new" in created_options[0]
    assert "--headless" in created_options[1]
    assert "--headless=new" not in created_options[1]


def test_run_retries_with_alternate_driver_when_first_driver_exits(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(
        scraper,
        "_find_chromedriver_candidates",
        lambda: ["/usr/bin/chromedriver", "/snap/bin/chromium.chromedriver"],
    )
    monkeypatch.setattr(scraper.time, "sleep", lambda seconds: None)

    created_driver_paths = []

    class _Element:
        text = "Vacancy"

        def get_attribute(self, name):
            return "https://example.com/jobs/1" if name == "href" else None

    class _Driver:
        def get(self, website_url):
            self.website_url = website_url

        def execute_script(self, script):
            self.script = script

        def find_element(self, by, value):
            return _Element()

        def find_elements(self, by, value):
            return [_Element()]

        def quit(self):
            self.closed = True

    def fake_chrome(service, options):
        created_driver_paths.append(service.path)
        if service.path == "/usr/bin/chromedriver":
            raise SessionNotCreatedException(
                "Service /usr/bin/chromedriver unexpectedly exited. Status code was: 1"
            )
        return _Driver()

    monkeypatch.setattr(scraper.webdriver, "Chrome", fake_chrome)
    monkeypatch.setattr(
        scraper.WebDriverWait,
        "until",
        lambda self, condition: True,
    )

    result = scraper.SafeSeleniumScrapingTool()._run("https://example.com/jobs")

    assert "Vacancy" in result
    assert "/usr/bin/chromedriver" in created_driver_paths
    assert "/snap/bin/chromium.chromedriver" in created_driver_paths


def test_run_returns_startup_diagnostics_when_chrome_cannot_start(monkeypatch):
    monkeypatch.setattr(scraper, "_find_chrome_binary", lambda: "/usr/bin/chromium")
    monkeypatch.setattr(scraper, "_find_chromedriver", lambda: "/usr/bin/chromedriver")
    monkeypatch.setattr(
        scraper,
        "_find_chromedriver_candidates",
        lambda: ["/usr/bin/chromedriver"],
    )

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "driver failed"

    monkeypatch.setattr(scraper.subprocess, "run", lambda *args, **kwargs: _Result())

    def fake_chrome(service, options):
        raise SessionNotCreatedException("Chrome instance exited")

    monkeypatch.setattr(scraper.webdriver, "Chrome", fake_chrome)

    result = scraper.SafeSeleniumScrapingTool()._run("https://example.com/jobs")

    assert "Error starting Selenium Chrome session" in result
    assert "Chrome instance exited" in result
    assert "Browser binary: /usr/bin/chromium" in result
    assert "ChromeDriver: /usr/bin/chromedriver" in result
    assert "Tried ChromeDrivers: /usr/bin/chromedriver" in result
    assert "Executable diagnostics:" in result
    assert "/usr/bin/chromium --version exited 1: driver failed" in result
    assert "/usr/bin/chromedriver --version exited 1: driver failed" in result
    assert "Retried with legacy --headless" in result
