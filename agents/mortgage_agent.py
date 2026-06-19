"""
Mortgage agent — answers mortgage questions using the financial calculator tool.
The LLM reasons; the Python tool does every numeric computation.
"""
from crewai import Agent, Task, Crew
from tools.financial_calculator import MortgageCalculatorTool
from config.settings import MORTGAGE_MODEL


_BACKSTORY = """
You are a specialist mortgage advisor at a Spanish bank.
You NEVER compute numbers yourself — you ALWAYS delegate calculations to the
MortgageCalculatorTool. Present results clearly to the customer in Spanish.
""".strip()


def answer_mortgage_query(user_message: str) -> str:
    calculator = MortgageCalculatorTool()
    agent = Agent(
        role="Mortgage Advisor",
        goal="Answer mortgage questions accurately using the calculator tool.",
        backstory=_BACKSTORY,
        tools=[calculator],
        llm=MORTGAGE_MODEL,
        verbose=True,
    )
    task = Task(
        description=user_message,
        agent=agent,
        expected_output="A clear answer in Spanish with exact figures from the calculator.",
    )
    result = Crew(agents=[agent], tasks=[task], verbose=True).kickoff()
    return str(result)
