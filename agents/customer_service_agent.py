"""
Customer service agent — handles complaints and incidents via RAG over the
bank's knowledge base.
"""
from crewai import Agent, Task, Crew
from tools.rag_search import RAGSearchTool
from config.settings import CUSTOMER_SERVICE_MODEL


_BACKSTORY = """
You are a customer service agent for a Spanish bank.
You help customers with incidents, complaints, card issues, fraud, and transfers.
Always search the knowledge base before answering and respond in Spanish.
""".strip()


def answer_incident_query(user_message: str) -> str:
    rag_tool = RAGSearchTool()
    agent = Agent(
        role="Customer Service Agent",
        goal="Resolve customer incidents using the knowledge base.",
        backstory=_BACKSTORY,
        tools=[rag_tool],
        llm=CUSTOMER_SERVICE_MODEL,
        verbose=True,
    )
    task = Task(
        description=user_message,
        agent=agent,
        expected_output="A helpful response in Spanish that resolves or escalates the incident.",
    )
    result = Crew(agents=[agent], tasks=[task], verbose=True).kickoff()
    return str(result)
