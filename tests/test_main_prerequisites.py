import sys
from unittest.mock import patch

import pytest

from job_hunting import main


def test_run_bot_checks_chromium_before_starting_bot():
    sys.modules.pop("job_hunting.bot.telegram_bot", None)

    with patch(
        "job_hunting.tools.safe_selenium_scraper.require_chrome_binary",
        side_effect=RuntimeError("Chrome or Chromium is required"),
    ):
        with pytest.raises(RuntimeError, match="Chrome or Chromium is required"):
            main.run_bot()

    assert "job_hunting.bot.telegram_bot" not in sys.modules


def test_run_discovery_checks_chromium_before_starting_flow():
    sys.modules.pop("job_hunting.flows.discovery_flow", None)

    with patch(
        "job_hunting.tools.safe_selenium_scraper.require_chrome_binary",
        side_effect=RuntimeError("Chrome or Chromium is required"),
    ):
        with pytest.raises(RuntimeError, match="Chrome or Chromium is required"):
            main.run_discovery()

    assert "job_hunting.flows.discovery_flow" not in sys.modules
