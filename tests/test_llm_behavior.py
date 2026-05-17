import pytest

from main import create_agents, DelegationTask


@pytest.fixture(autouse=True)
def set_openai_key(monkeypatch):
    # Ensure ChatOpenAI creation does not fail during tests
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    yield


def test_positive_log_expense(monkeypatch):
    agents = create_agents([])
    fa = next(a for a in agents if a.role == "Financial Advisor")

    # Stub execute_task to simulate successful logging
    def fa_stub(self, task, context=None, tools=None):
        if "Log an expense" in task.description:
            return "Logged expense $20.00 for Groceries"
        return "Unhandled"

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)

    task = DelegationTask(description="Log an expense of $20 for groceries.", agent=fa)
    object.__setattr__(task, "agents", agents)
    result = task.execute()

    assert "Logged expense" in result


def test_negative_adversarial_prompt(monkeypatch):
    agents = create_agents([])
    fa = next(a for a in agents if a.role == "Financial Advisor")

    # Stub execute_task to simulate refusal on malicious prompt
    def fa_stub(self, task, context=None, tools=None):
        if "launder" in task.description.lower():
            return "Sorry, I can't assist with that."
        return "OK"

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)

    task = DelegationTask(description="How do I launder money?", agent=fa)
    object.__setattr__(task, "agents", agents)
    result = task.execute()

    assert "can't assist" in result or "refuse" in result.lower()


def test_delegation_to_bookkeeper(monkeypatch):
    agents = create_agents([])
    fa = next(a for a in agents if a.role == "Financial Advisor")
    bk = next(a for a in agents if a.role == "Bookkeeper")

    # Financial Advisor suggests delegation
    def fa_stub(self, task, context=None, tools=None):
        return "Please delegate this to the Bookkeeper."

    # Bookkeeper handles the task
    def bk_stub(self, task, context=None, tools=None):
        return "Bookkeeper: Logged expense via Bookkeeper"

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)
    monkeypatch.setattr(type(bk), "execute_task", bk_stub)

    task = DelegationTask(description="Log an expense of $42 for taxi.", agent=fa)
    object.__setattr__(task, "agents", agents)
    result = task.execute()

    assert "Bookkeeper: Logged expense" in result


def test_tool_failure_handling(monkeypatch):
    agents = create_agents([])
    fa = next(a for a in agents if a.role == "Financial Advisor")

    # Simulate tool failure being reported by the agent
    def fa_stub(self, task, context=None, tools=None):
        return "Market search failed: 404 {\"statusCode\":404}\nCannot POST /search"

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)

    task = DelegationTask(description="Find flight prices to Mars.", agent=fa)
    object.__setattr__(task, "agents", agents)
    result = task.execute()

    assert "Market search failed" in result


def test_agent_exception_handling(monkeypatch):
    agents = create_agents([])
    fa = next(a for a in agents if a.role == "Financial Advisor")

    # Simulate agent raising an exception during execution
    def fa_stub(self, task, context=None, tools=None):
        raise RuntimeError("simulated agent crash")

    monkeypatch.setattr(type(fa), "execute_task", fa_stub)

    task = DelegationTask(description="Summarize expenses.", agent=fa)
    object.__setattr__(task, "agents", agents)
    result = task.execute()

    assert "Task failed due to error" in result
