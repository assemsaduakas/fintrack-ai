import os
import requests
from dotenv import load_dotenv
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI

from crewai.agent import Agent
from crewai.task import Task
from crewai.tools.agent_tools import AgentTools

from database import DatabaseManager
from rag import FinancialRAG

import logging
import time
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("fintrack_ai.log"),
        logging.StreamHandler()
    ]
)


def load_environment() -> None:
    load_dotenv()
    required = ["OPENAI_API_KEY"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")


def create_bookkeeper_tools(database: DatabaseManager):
    def log_expense(amount: float, category: str, description: str, date: str = None) -> str:
        return database.add_expense(amount, category, description, date)

    def summarize_expenses(period: str = "this month", category: str = "") -> str:
        return database.get_summary(period=period, category=category or None)

    def recent_expenses(limit: int = 10) -> str:
        return database.get_recent_expenses(limit=limit)

    return [
        StructuredTool.from_function(
            func=log_expense,
            name="Log expense",
            description="Record an expense in the personal finance ledger."
        ),
        StructuredTool.from_function(
            func=summarize_expenses,
            name="Summarize expenses",
            description="Provide a summary of expenses for a specified period and optional category."
        ),
        StructuredTool.from_function(
            func=recent_expenses,
            name="List recent expenses",
            description="Return the most recent expense entries from the ledger."
        ),
    ]


def create_rag_tools(rag: FinancialRAG):
    def query_finance_documents(query: str) -> str:
        return rag.query(query)

    return [
        StructuredTool.from_function(
            func=query_finance_documents,
            name="Query financial knowledge base",
            description="Search the personal financial knowledge base of goals and statements."
        )
    ]


def create_market_tools(rag: FinancialRAG = None):
    def market_search(query: str, region: str = "global") -> str:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Market search is not configured. Set SERPER_API_KEY in your .env file."

        base_url = os.getenv("MARKET_API_URL", "https://api.serper.dev")
        url = base_url.rstrip("/") + "/search"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        payload = {"q": query, "gl": region}

        # Retries with exponential backoff for transient errors
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            except requests.RequestException as e:
                logging.warning("Market search network error (attempt %d): %s", attempt + 1, e)
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    return "Market search returned invalid JSON."
                snippets = []
                for item in data.get("organic", [])[:5]:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    snippets.append(f"- {title}: {snippet}")
                return "\n".join(snippets) if snippets else "No market results returned."

            # If 404, likely wrong endpoint — log and fallback to RAG if available
            if response.status_code == 404:
                logging.error("Market search 404 — endpoint may be incorrect: %s", url)
                if rag is not None:
                    logging.info("Falling back to local RAG for market info.")
                    return rag.query(query)
                return f"Market search failed: {response.status_code} {response.text}"

            # Retry on 5xx
            if 500 <= response.status_code < 600:
                logging.warning("Market search server error %s, retrying...", response.status_code)
                time.sleep(2 ** attempt)
                continue

            # Other client errors — do not retry
            logging.error("Market search failed %s: %s", response.status_code, response.text)
            return f"Market search failed: {response.status_code} {response.text}"

        logging.error("Market search failed after retries.")
        if rag is not None:
            logging.info("Using RAG fallback after market search retries exhausted.")
            return rag.query(query)
        return "Market search failed after retries."

    return [
        StructuredTool.from_function(
            func=market_search,
            name="Market search",
            description="Look up current market information for a given financial query."
        )
    ]


def create_agents(tools, openai_api_key: str = None):
    # Create a ChatOpenAI instance with explicit API key to avoid pydantic default_factory validation
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(openai_api_key=api_key) if api_key else ChatOpenAI(openai_api_key="")

    return [
        Agent(
            role="Bookkeeper",
            goal="Capture and categorize every personal expense accurately.",
            backstory="I am responsible for tracking spending, keeping the ledger accurate, and summarizing budget performance.",
            tools=tools,
            memory=True,
            verbose=False,
            max_iter=6,
            llm=llm,
        ),
        Agent(
            role="Market Analyst",
            goal="Research market and pricing details relevant to user financial decisions.",
            backstory="I analyze market conditions, pricing trends, and compare products to keep recommendations grounded in current data.",
            tools=tools,
            memory=True,
            verbose=False,
            max_iter=6,
            llm=llm,
        ),
        Agent(
            role="Financial Advisor",
            goal="Recommend a budget plan and actionable saving strategies based on expenses and financial goals.",
            backstory="I turn spending data and goals into practical advice, help the user stay on track, and suggest tradeoffs.",
            tools=tools,
            memory=True,
            verbose=False,
            max_iter=6,
            llm=llm,
        ),
    ]


class StateManager:
    def __init__(self):
        self.state = {}

    def update_state(self, agent_role, task_description, status):
        self.state[agent_role] = {
            "task": task_description,
            "status": status,
        }

    def get_state(self):
        return self.state


class PromptSanitizer:
    FORBIDDEN = [
        r"launder",
        r"terror",
        r"hack",
        r"illegal",
        r"kill",
        r"exploit",
        r"money laundering",
    ]

    @staticmethod
    def sanitize(prompt: str, max_length: int = 2000) -> (bool, str):
        if not prompt or not prompt.strip():
            return False, "Empty prompt provided."

        low = prompt.lower()
        for pat in PromptSanitizer.FORBIDDEN:
            if re.search(pat, low):
                return False, "Sorry, I can't assist with that."

        # Basic prompt-injection detection
        if "ignore previous" in low or "disregard previous" in low or "follow only" in low:
            return False, "Prompt appears to contain instruction injection; please rephrase."

        if len(prompt) > max_length:
            return True, prompt[:max_length]

        return True, prompt


class RateLimiter:
    def __init__(self, max_per_minute: int = 10):
        self.max_per_minute = max_per_minute
        self.calls = {}  # agent_id -> list of timestamps

    def allow(self, agent_id: str) -> bool:
        now = time.time()
        window_start = now - 60
        timestamps = [t for t in self.calls.get(agent_id, []) if t >= window_start]
        if len(timestamps) >= self.max_per_minute:
            return False
        timestamps.append(now)
        self.calls[agent_id] = timestamps
        return True


# single shared limiter
rate_limiter = RateLimiter(max_per_minute=10)


# Update DelegationTask to include logging
class DelegationTask(Task):
    def execute(self):
        try:
            # Sanitize prompt first
            ok, out = PromptSanitizer.sanitize(self.description)
            if not ok:
                logging.warning(f"Prompt rejected: {out}")
                return out

            logging.info(f"{self.agent.role} is processing the task: {self.description}")

            # rate limit per agent
            agent_id = getattr(self.agent, "id", getattr(self.agent, "role", "unknown"))
            if not rate_limiter.allow(str(agent_id)):
                logging.warning("Rate limit exceeded for agent %s", agent_id)
                return "Rate limit exceeded. Please try again later."

            # Use the standard Task execution which delegates to Agent.execute_task
            result = super().execute()

            # Simple delegation heuristic: if agent suggests delegation in text, forward to another agent
            if isinstance(result, str) and "delegate" in result.lower():
                logging.info("Delegation suggested by agent response. Searching for a coworker to delegate to...")
                agents_list = getattr(self, "agents", None)
                if agents_list:
                    for candidate in agents_list:
                        if candidate.role != self.agent.role:
                            logging.info(f"Delegating task to {candidate.role}.")
                            new_task = DelegationTask(description=self.description, agent=candidate)
                            # propagate agents list for further delegation
                            object.__setattr__(new_task, "agents", agents_list)
                            return new_task.execute()
                else:
                    logging.warning("No agents list available for delegation; skipping delegation.")

            logging.info(f"Task completed by {self.agent.role}: {result}")
            return result
        except Exception as e:
            logging.error(f"Error occurred while executing task: {e}")
            return f"Task failed due to error: {e}"


# Add iterative testing and refinement logic

def test_system(agents):
    logging.info("Starting iterative testing and refinement.")

    test_queries = [
        "Log an expense of $20 for groceries.",
        "Summarize my expenses for this month.",
        "What are the recent expenses?",
        "Find market trends for electric vehicles.",
        "Suggest a budget plan based on my expenses."
    ]

    for query in test_queries:
        logging.info(f"Testing system with query: {query}")
        print(f"\n> {query}")

        starter_agent = next(agent for agent in agents if agent.role == "Financial Advisor")
        task = DelegationTask(description=query, agent=starter_agent)
        # attach agents list so DelegationTask can delegate if needed
        object.__setattr__(task, "agents", agents)
        result = task.execute()

        logging.info(f"Result for query '{query}': {result}")
        print("\n--- Agent response ---")
        print(result)

    logging.info("Iterative testing completed. Refinement suggestions can be implemented based on logs.")


def main():
    load_environment()
    database = DatabaseManager()
    rag = FinancialRAG()

    if rag.vectorstore is None:
        print("Initializing the financial knowledge base...")
        rag.ingest_documents(FinancialRAG.default_documents())

    agents = create_agents([])
    crew_tools = AgentTools(agents=agents).tools()
    shared_tools = (
        create_bookkeeper_tools(database)
        + create_rag_tools(rag)
        + create_market_tools(rag)
        + crew_tools
    )

    for agent in agents:
        agent.tools = shared_tools

    logging.info("FinTrack AI is ready. Waiting for user input.")
    print("FinTrack AI is ready. Enter a financial request in plain English.")
    user_query = input("> ").strip()
    if not user_query:
        logging.warning("No request provided. Exiting.")
        print("No request provided. Exiting.")
        return

    state_manager = StateManager()

    starter_agent = next(agent for agent in agents if agent.role == "Financial Advisor")
    logging.info(f"Starting task with Financial Advisor for query: {user_query}")

    task = DelegationTask(description=user_query, agent=starter_agent)
    object.__setattr__(task, "agents", agents)
    result = task.execute()

    logging.info("Task execution completed. Displaying result.")
    print("\n--- Agent response ---")
    print(result)

    # Call test_system in main function for refinement
    logging.info("Initiating system testing and refinement.")
    test_system(agents)


if __name__ == "__main__":
    main()
