import re

from main import (
    create_agents,
    create_bookkeeper_tools,
    create_rag_tools,
    create_market_tools,
    DelegationTask,
)
from crewai.tools.agent_tools import AgentTools
from database import DatabaseManager

import pytest


@pytest.fixture(autouse=True)
def set_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    yield


def test_end_to_end_log_and_summary(tmp_path, monkeypatch):
    # Use a temporary sqlite db
    db_path = tmp_path / "test_expenses.db"
    database = DatabaseManager(str(db_path))

    agents = create_agents([])
    crew_tools = AgentTools(agents=agents).tools()
    shared_tools = create_bookkeeper_tools(database) + create_rag_tools(None) + create_market_tools() + crew_tools

    for agent in agents:
        agent.tools = shared_tools

    # Monkeypatch Financial Advisor to directly call DB tools for deterministic behavior
    fa = next(a for a in agents if a.role == "Financial Advisor")

    def fa_stub(self, task, context=None, tools=None):
        desc = task.description.lower()
        if "log an expense" in desc or "log an expense of" in desc:
            # extract amount
            m = re.search(r"\$?(\d+(?:\.\d{1,2})?)", desc)
            amount = float(m.group(1)) if m else 0.0
            cat_m = re.search(r"for ([\w &]+)[\.]?$", desc)
            category = cat_m.group(1).title() if cat_m else "Misc"
            return database.add_expense(amount, category, "Automated test")
        if "summarize" in desc:
            return database.get_summary(period="this month")
        if "recent" in desc:
            return database.get_recent_expenses()
        return "OK"

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)

    # Log an expense
    task1 = DelegationTask(description="Log an expense of $15 for coffee.", agent=fa)
    object.__setattr__(task1, "agents", agents)
    res1 = task1.execute()
    assert "Logged expense" in res1

    # Summarize
    task2 = DelegationTask(description="Summarize my expenses for this month.", agent=fa)
    object.__setattr__(task2, "agents", agents)
    res2 = task2.execute()
    assert "Expense summary for" in res2

    # Recent expenses
    task3 = DelegationTask(description="What are the recent expenses?", agent=fa)
    object.__setattr__(task3, "agents", agents)
    res3 = task3.execute()
    assert "$15.00" in res3


def test_delegation_flow_with_bookkeeper(tmp_path, monkeypatch):
    db_path = tmp_path / "test_expenses2.db"
    database = DatabaseManager(str(db_path))

    agents = create_agents([])
    crew_tools = AgentTools(agents=agents).tools()
    shared_tools = create_bookkeeper_tools(database) + create_rag_tools(None) + create_market_tools() + crew_tools

    for agent in agents:
        agent.tools = shared_tools

    fa = next(a for a in agents if a.role == "Financial Advisor")
    bk = next(a for a in agents if a.role == "Bookkeeper")

    # FA suggests delegation
    def fa_stub(self, task, context=None, tools=None):
        return "Please delegate to Bookkeeper"

    def bk_stub(self, task, context=None, tools=None):
        # parse and log
        return database.add_expense(42.0, "Taxi", "Delegated")

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)
    monkeypatch.setattr(type(bk), "execute_task", bk_stub)

    task = DelegationTask(description="Log an expense of $42 for taxi.", agent=fa)
    object.__setattr__(task, "agents", agents)
    res = task.execute()
    assert "Logged expense" in res
