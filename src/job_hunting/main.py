from dotenv import load_dotenv

load_dotenv()


def run_discovery() -> None:
    """Cron entry point — discover and score new vacancies, send Telegram approval requests."""
    from job_hunting.flows.discovery_flow import DiscoveryFlow
    DiscoveryFlow().kickoff()


def run_bot() -> None:
    """Long-running entry point — start the Telegram bot."""
    from job_hunting.bot.telegram_bot import run
    run()


def run_advisor() -> None:
    """Long-running entry point — start the Chainlit Career Advisor."""
    import subprocess
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    advisor_path = os.path.join(os.path.dirname(__file__), "advisor", "app.py")
    subprocess.run(
        [sys.executable, "-m", "chainlit", "run", advisor_path],
        check=True,
        cwd=project_root,
    )
