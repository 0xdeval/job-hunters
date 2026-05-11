from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileReadTool, FileWriterTool

from job_hunting.config import get_llm


@CrewBase
class CompanySourcingCrew:
    """Sources and scores target companies for vacancy discovery."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def source_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["source_planner"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def company_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["company_researcher"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def fit_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fit_analyst"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def candidate_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["candidate_writer"],
            llm=get_llm(),
            tools=[FileReadTool(), FileWriterTool()],
            verbose=True,
        )

    @task
    def plan_company_sources_task(self) -> Task:
        return Task(config=self.tasks_config["plan_company_sources_task"])

    @task
    def research_companies_task(self) -> Task:
        return Task(config=self.tasks_config["research_companies_task"])

    @task
    def score_company_fit_task(self) -> Task:
        return Task(config=self.tasks_config["score_company_fit_task"])

    @task
    def write_company_candidates_task(self) -> Task:
        return Task(config=self.tasks_config["write_company_candidates_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
