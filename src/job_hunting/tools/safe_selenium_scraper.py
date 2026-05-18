import time
import subprocess
from os import environ
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


CHROME_BINARY_ENV = "CHROME_BINARY"
CHROMEDRIVER_PATH_ENV = "CHROMEDRIVER_PATH"
CHROME_BINARY_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
CHROMEDRIVER_CANDIDATES = (
    "chromedriver",
    "chromium.chromedriver",
)
SNAP_CHROMIUM_DRIVER = "/snap/bin/chromium.chromedriver"
CHROME_INSTALL_HELP = (
    "Chrome or Chromium is required for Selenium vacancy scraping, but no "
    "browser binary was found. Install Chromium or Google Chrome on the server "
    "(Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y chromium), "
    "or set CHROME_BINARY=/path/to/chrome before starting the service."
)
CHROMEDRIVER_INSTALL_HELP = (
    "ChromeDriver is required for Selenium vacancy scraping. Install a driver "
    "that matches the installed Chrome/Chromium major version, or set "
    "CHROMEDRIVER_PATH=/path/to/chromedriver. For Snap Chromium this is often "
    "CHROMEDRIVER_PATH=/snap/bin/chromium.chromedriver."
)


class SafeSeleniumScrapingSchema(BaseModel):
    website_url: str = Field(description="Mandatory website url to read. Must start with http:// or https://")
    css_element: Optional[str] = Field(description="Optional css reference for element to scrape from the website", default="")

class SafeSeleniumScrapingTool(BaseTool):
    name: str = "Scrape website with Selenium"
    description: str = "A tool that can be used to read a website content, including dynamically loaded content."
    args_schema: Type[BaseModel] = SafeSeleniumScrapingSchema

    def _run(self, website_url: str, css_element: str = "") -> str:
        with TemporaryDirectory(prefix="job-hunting-chrome-") as profile_dir:
            driver_paths = _find_chromedriver_candidates()
            if not driver_paths:
                driver_paths = [ChromeDriverManager().install()]
            driver_log_path = str(Path(profile_dir) / "chromedriver.log")
            driver = None
            startup_errors: list[str] = []

            for driver_path in driver_paths:
                for legacy_headless in (False, True):
                    chrome_options = _build_chrome_options(
                        profile_dir,
                        legacy_headless=legacy_headless,
                    )
                    service = Service(driver_path, log_output=driver_log_path)
                    try:
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                        break
                    except WebDriverException as exc:
                        headless_mode = "--headless" if legacy_headless else "--headless=new"
                        startup_errors.append(
                            f"{driver_path} with {headless_mode}: {exc}"
                        )
                if driver is not None:
                    break

            if driver is None:
                return _format_chrome_startup_error(
                    startup_errors,
                    driver_paths,
                    driver_log_path,
                )

            try:
                driver.get(website_url)
                
                # Wait for initial load
                time.sleep(3)
                
                # Scroll down multiple times to trigger lazy loading
                for _ in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5)

                # If a specific CSS element is requested, wait for it
                if css_element:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, css_element))
                        )
                    except:
                        pass # Continue anyway if wait fails

                # Specifically for job boards, wait for links to appear
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                except:
                    pass

                # Extract content
                if css_element:
                    elements = driver.find_elements(By.CSS_SELECTOR, css_element)
                    content = "\n".join([e.text for e in elements if e.text.strip()])
                    # If it's links, also get URLs
                    if css_element.startswith("a") or " a" in css_element or css_element.endswith("a"):
                        links = []
                        for e in elements:
                            href = e.get_attribute("href")
                            if href and e.text.strip():
                                links.append(f"[{e.text.strip()}]({href})")
                        if links:
                            content = "\n".join(links)
                else:
                    # Default: Get main body text but preserve links in markdown format
                    # We'll use a simple heuristic to find job links
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    # Also find all links to provide to the agent
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    formatted_links = []
                    for link in all_links:
                        href = link.get_attribute("href")
                        text = link.text.strip()
                        if href and text and len(text) > 3: # Ignore tiny links
                            # Filter for common job-like links
                            if any(k in href.lower() for k in ["job", "vacancy", "opening", "career", "apply"]):
                                 formatted_links.append(f"[{text}]({href})")
                            elif any(k in text.lower() for k in ["engineer", "manager", "lead", "developer", "product", "sales"]):
                                 formatted_links.append(f"[{text}]({href})")

                    content = page_text
                    if formatted_links:
                        content += "\n\n### Potential Job Links Found:\n" + "\n".join(set(formatted_links))

                return content
            except Exception as e:
                return f"Error scraping with Selenium: {str(e)}"
            finally:
                driver.quit()


def _build_chrome_options(profile_dir: str, legacy_headless: bool = False) -> Options:
    chrome_options = Options()
    chrome_binary = _find_chrome_binary()
    if chrome_binary:
        chrome_options.binary_location = chrome_binary
    chrome_options.add_argument("--headless" if legacy_headless else "--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return chrome_options


def _format_chrome_startup_error(
    startup_errors: list[str],
    driver_paths: list[str],
    driver_log_path: str,
) -> str:
    browser_path = _find_chrome_binary() or "not found"
    latest_error = startup_errors[-1] if startup_errors else "unknown startup error"
    driver_path = driver_paths[0] if driver_paths else "not found"
    tried_paths = ", ".join(driver_paths) if driver_paths else "none"
    message = (
        "Error starting Selenium Chrome session. Chromium exited before a "
        "WebDriver session was created.\n"
        f"Browser binary: {browser_path}\n"
        f"ChromeDriver: {driver_path}\n"
        f"Tried ChromeDrivers: {tried_paths}\n"
        "Retried with legacy --headless after --headless=new failed.\n"
        f"Selenium error: {latest_error}"
    )
    command_diagnostics = _format_command_diagnostics(browser_path, driver_paths)
    if command_diagnostics:
        message += f"\nExecutable diagnostics:\n{command_diagnostics}"
    driver_log = _read_text_tail(driver_log_path)
    if driver_log:
        message += f"\nChromeDriver log tail:\n{driver_log}"
    return message


def _format_command_diagnostics(browser_path: str, driver_paths: list[str]) -> str:
    commands = []
    if browser_path != "not found":
        commands.append(browser_path)
    commands.extend(driver_paths)
    diagnostics = [_command_version_diagnostic(path) for path in _unique_paths(commands)]
    return "\n".join(diagnostic for diagnostic in diagnostics if diagnostic)


def _command_version_diagnostic(path: str) -> str:
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError as exc:
        return f"{path} --version failed to start: {exc}"
    except subprocess.TimeoutExpired:
        return f"{path} --version timed out"

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    details = stdout or stderr or "no output"
    return f"{path} --version exited {result.returncode}: {details}"


def _read_text_tail(path: str, max_chars: int = 4000) -> str:
    try:
        content = Path(path).read_text(errors="replace")
    except OSError:
        return ""
    return content[-max_chars:].strip()


def _find_chrome_binary() -> str | None:
    configured = environ.get(CHROME_BINARY_ENV, "").strip()
    if configured:
        return configured

    for executable in CHROME_BINARY_CANDIDATES:
        path = which(executable)
        if path:
            return path

    for path in (
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/google-chrome-stable"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/chromium-browser"),
    ):
        if path.exists():
            return str(path)

    return None


def require_chrome_binary() -> str:
    chrome_binary = _find_chrome_binary()
    if not chrome_binary:
        raise RuntimeError(CHROME_INSTALL_HELP)
    return chrome_binary


def _find_chromedriver() -> str | None:
    candidates = _find_chromedriver_candidates()
    return candidates[0] if candidates else None


def _find_chromedriver_candidates() -> list[str]:
    configured = environ.get(CHROMEDRIVER_PATH_ENV, "").strip()
    if configured:
        return [configured]

    candidates: list[str] = []

    if _is_snap_chromium(_find_chrome_binary()):
        snap_driver = which("chromium.chromedriver")
        if snap_driver:
            candidates.append(snap_driver)
        if Path(SNAP_CHROMIUM_DRIVER).exists():
            candidates.append(SNAP_CHROMIUM_DRIVER)

    for executable in CHROMEDRIVER_CANDIDATES:
        path = which(executable)
        if path:
            candidates.append(path)

    for path in (
        Path("/usr/bin/chromedriver"),
        Path("/snap/bin/chromium.chromedriver"),
    ):
        if path.exists():
            candidates.append(str(path))

    return _unique_paths(candidates)


def _unique_paths(paths: list[str]) -> list[str]:
    seen = set()
    unique = []
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _is_snap_chromium(chrome_binary: str | None) -> bool:
    return chrome_binary == "/snap/bin/chromium"


def require_chromedriver() -> str:
    chromedriver = _find_chromedriver()
    if not chromedriver:
        raise RuntimeError(CHROMEDRIVER_INSTALL_HELP)
    return chromedriver
