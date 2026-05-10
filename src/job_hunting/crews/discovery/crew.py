from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import SeleniumScrapingTool, FileReadTool, FileWriterTool
from typing import List
from job_hunting.config import get_llm
from job_hunting.tools import DedupTool


@CrewBase
class DiscoveryCrew:
    """Discovers and scores new job vacancies."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def vacancy_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["vacancy_scout"],
            llm=get_llm(),
            tools=[SeleniumScrapingTool(), FileWriterTool(), DedupTool()],
            verbose=True,
        )

    @agent
    def fit_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fit_analyst"],
            llm=get_llm(),
            tools=[FileReadTool(), FileWriterTool()],
            verbose=True,
        )

    @task
    def scrape_vacancies_task(self) -> Task:
        return Task(config=self.tasks_config["scrape_vacancies_task"])

    @task
    def score_vacancies_task(self) -> Task:
        return Task(config=self.tasks_config["score_vacancies_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
