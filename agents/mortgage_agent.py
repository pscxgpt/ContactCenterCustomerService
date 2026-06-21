"""
Mortgage agent — answers mortgage questions using the financial calculator tool.
The LLM reasons; the Python tool does every numeric computation.
"""
from crewai import Agent, Task, Crew
from tools.financial_calculator import (
    MortgageCalculatorTool,
    LTVCalculatorTool,
    CreditRatingTool,
    BonificationCalculatorTool,
    MortgageSimulatorTool,
)
from config.settings import MORTGAGE_MODEL


_BACKSTORY = """
You are a specialist mortgage advisor at a Spanish bank.
You NEVER compute numbers yourself — you ALWAYS delegate calculations to the
appropriate tool. You have five tools available:

1. MortgageCalculatorTool — basic monthly payment, total repayment, interest.
2. LTVCalculatorTool — Loan-To-Value ratio and risk assessment.
3. CreditRatingTool — internal credit-risk scoring of the client profile.
4. BonificationCalculatorTool — final rate/TAE after linked-product discounts.
5. MortgageSimulatorTool — stress tests, early repayment, and affordability scenarios.

Choose the right tool(s) for each query. Present results clearly to the customer in Spanish.
""".strip()


def answer_mortgage_query(user_message: str) -> str:
    tools = [
        MortgageCalculatorTool(),
        LTVCalculatorTool(),
        CreditRatingTool(),
        BonificationCalculatorTool(),
        MortgageSimulatorTool(),
    ]
    agent = Agent(
        role="Mortgage Advisor",
        goal="Answer mortgage questions accurately using the calculator tools.",
        backstory=_BACKSTORY,
        tools=tools,
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
