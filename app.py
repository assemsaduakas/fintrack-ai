import os
import streamlit as st
from datetime import datetime

from database import DatabaseManager
from main import create_agents, DelegationTask, create_bookkeeper_tools, create_rag_tools, create_market_tools
from crewai.tools.agent_tools import AgentTools


st.set_page_config(page_title="FinTrack AI", layout="wide")

st.sidebar.title("FinTrack AI")
st.sidebar.markdown("A polished demo UI for personal finance multi-agent system.")

@st.cache_resource
def get_env():
    return os.environ.copy()


@st.cache_resource
def init_system():
    db = DatabaseManager()
    agents = create_agents([])
    crew_tools = AgentTools(agents=agents).tools()
    shared_tools = create_bookkeeper_tools(db) + create_rag_tools(None) + create_market_tools() + crew_tools
    for agent in agents:
        agent.tools = shared_tools
    return db, agents


db, agents = init_system()

st.title("FinTrack AI — Demo UI")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Quick Actions")
    action = st.selectbox("Choose action", ["Log expense", "Summarize expenses", "Recent expenses", "Agent query"])

    if action == "Log expense":
        amount = st.number_input("Amount", min_value=0.0, value=10.0, format="%.2f")
        category = st.text_input("Category", value="Groceries")
        description = st.text_input("Description", value="Demo purchase")
        if st.button("Log"):
            res = db.add_expense(amount, category, description, datetime.utcnow().strftime("%Y-%m-%d"))
            st.success(res)

    elif action == "Summarize expenses":
        period = st.selectbox("Period", ["this month", "this year"])
        if st.button("Summarize"):
            res = db.get_summary(period=period)
            st.text(res)

    elif action == "Recent expenses":
        if st.button("Show recent"):
            res = db.get_recent_expenses()
            st.text(res)

    else:
        query = st.text_area("Ask the agents", value="Suggest a budget plan based on my expenses.")
        agent_role = st.selectbox("Start agent", [a.role for a in agents], index=2)
        if st.button("Run"):
            starter = next(a for a in agents if a.role == agent_role)
            task = DelegationTask(description=query, agent=starter)
            object.__setattr__(task, "agents", agents)
            res = task.execute()
            st.markdown("**Agent response:**")
            st.write(res)

with col2:
    st.header("Recent Activity")
    st.markdown("### Latest expenses")
    st.text(db.get_recent_expenses(limit=5))

    st.markdown("### State")
    st.text("Agents: " + ", ".join([a.role for a in agents]))

st.markdown("---")
st.caption("Polished demo UI — designed for demo/Investor walkthroughs. Use the Recording checklist in scripts/.")
